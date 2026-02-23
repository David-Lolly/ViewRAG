"""文档处理通用API路由"""

import hashlib
import json
import logging
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from io import BytesIO
from urllib.parse import quote

from crud.database import SessionLocal
from crud.document_crud import DocumentCRUD
from schemas.document_schemas import DocumentStatusResponse
from models.models import DocumentStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["文档"])


# 状态到进度的映射
STATUS_PROGRESS_MAP = {
    DocumentStatus.QUEUED: {"progress": 5, "step": "排队中"},
    DocumentStatus.PARSING: {"progress": 25, "step": "解析中"},
    DocumentStatus.CHUNKING: {"progress": 50, "step": "分块中"},
    DocumentStatus.ENRICHING: {"progress": 65, "step": "内容增强"},
    DocumentStatus.VECTORIZING: {"progress": 80, "step": "向量化"},
    DocumentStatus.COMPLETED: {"progress": 100, "step": "完成"},
    DocumentStatus.FAILED: {"progress": 0, "step": "失败"},
}


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(doc_id: str, db: Session = Depends(get_db)):
    """
    查询单个文档的处理状态（用于前端轮询）

    - 200: 返回文档状态
    - 404: 文档不存在
    """
    document = DocumentCRUD.get_document_by_id(db, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    return DocumentStatusResponse(
        id=document.id,
        file_name=document.file_name,
        status=document.status,
        error_message=document.error_message
    )


@router.get("/{doc_id}/pdf")
async def get_document_pdf(doc_id: str, request: Request, db: Session = Depends(get_db)):
    """
    通过 doc_id 从 MinIO 获取 PDF 文件流，支持 Range 请求（分片传输）

    - 200: 返回完整 PDF 文件流
    - 206: 返回 Range 分片内容（PDF.js URL 模式按需加载）
    - 304: 浏览器缓存命中
    - 404: 文档不存在
    - 503: MinIO 连接失败
    """
    # 1. 查询文档记录
    document = DocumentCRUD.get_document_by_id(db, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 2. 基于 doc_id + file_path 生成 ETag，支持浏览器缓存
    etag = hashlib.md5(f"{doc_id}:{document.file_path}".encode()).hexdigest()
    etag_header = f'"{etag}"'

    # 3. 如果浏览器缓存命中，直接返回 304
    if_none_match = request.headers.get("if-none-match")
    if if_none_match == etag_header:
        return Response(status_code=304)

    # 4. 从 MinIO 获取文件流
    try:
        from services.storage import minio_storage

        if minio_storage is None:
            logger.error(f"MinIO 存储服务不可用，无法获取文档: {doc_id}")
            raise HTTPException(status_code=503, detail="文件存储服务不可用")

        # 先获取文件大小（用 stat_object，不下载内容）
        try:
            stat = minio_storage.client.stat_object(minio_storage.doc_bucket, document.file_path)
            file_size: int = stat.size or 0
            if file_size == 0:
                raise ValueError("文件大小为 0，元信息异常")
        except Exception as e:
            logger.error(f"获取 MinIO 文件元信息失败: {document.file_path}, 错误: {e}")
            raise HTTPException(status_code=503, detail="文件存储服务连接失败")

        # 公共响应头
        common_headers = {
            "Content-Disposition": f"inline; filename*=utf-8''{quote(document.file_name)}",
            "Cache-Control": "private, max-age=3600",
            "ETag": etag_header,
            "Accept-Ranges": "bytes",
        }

        # 5. 解析 Range 请求头
        range_header = request.headers.get("range")
        if range_header:
            # 解析格式：bytes=start-end
            try:
                range_str = range_header.replace("bytes=", "").strip()
                range_parts = range_str.split("-")
                range_start = int(range_parts[0]) if range_parts[0] else 0
                range_end = int(range_parts[1]) if len(range_parts) > 1 and range_parts[1] else file_size - 1
            except (ValueError, IndexError):
                raise HTTPException(status_code=416, detail="Range 格式非法")

            # 边界校验
            if range_start < 0 or range_end >= file_size or range_start > range_end:
                raise HTTPException(
                    status_code=416,
                    detail="Range 超出文件范围",
                    headers={"Content-Range": f"bytes */{file_size}"},
                )

            chunk_length = range_end - range_start + 1

            # 从 MinIO 按 Range 读取
            minio_response = minio_storage.client.get_object(
                minio_storage.doc_bucket,
                document.file_path,
                offset=range_start,
                length=chunk_length,
            )

            async def range_stream():
                try:
                    for chunk in minio_response.stream(amt=65536):
                        yield chunk
                finally:
                    minio_response.close()
                    minio_response.release_conn()

            return StreamingResponse(
                range_stream(),
                status_code=206,
                media_type="application/pdf",
                headers={
                    **common_headers,
                    "Content-Range": f"bytes {range_start}-{range_end}/{file_size}",
                    "Content-Length": str(chunk_length),
                },
            )

        # 6. 无 Range 头：流式传输完整文件，不先全量加载到内存
        minio_response = minio_storage.client.get_object(
            minio_storage.doc_bucket,
            document.file_path,
        )

        async def full_stream():
            try:
                for chunk in minio_response.stream(amt=65536):
                    yield chunk
            finally:
                minio_response.close()
                minio_response.release_conn()

        return StreamingResponse(
            full_stream(),
            media_type="application/pdf",
            headers={
                **common_headers,
                "Content-Length": str(file_size),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从 MinIO 获取 PDF 失败: doc_id={doc_id}, 错误: {e}")
        raise HTTPException(status_code=503, detail="文件存储服务连接失败")


@router.get("/{doc_id}/process")
async def process_document_sse(doc_id: str, track: str = "session"):
    """
    SSE 端点：处理文档并实时推送进度
    
    Args:
        doc_id: 文档ID
        track: 轨道类型，'session' 或 'kb'
    
    Returns:
        SSE 流，推送格式：
        data: {"status": "PARSING", "progress": 25, "step": "解析中"}
    """
    from crud.database import SessionLocal
    
    db = SessionLocal()
    
    try:
        # 验证文档存在
        document = DocumentCRUD.get_document_by_id(db, doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 如果文档已经处理完成或失败，直接返回当前状态
        if document.status in (DocumentStatus.COMPLETED, DocumentStatus.FAILED):
            async def completed_generator():
                status_info = STATUS_PROGRESS_MAP.get(document.status, {"progress": 0, "step": "未知"})
                data = {
                    "status": document.status.value,
                    "progress": status_info["progress"],
                    "step": status_info["step"],
                    "error_message": document.error_message
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                completed_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
    finally:
        db.close()
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE 事件生成器"""
        from services.document import VectorService, EnhancementService
        from services.document.processors import PROCESSOR_MAP
        from services.storage import minio_storage
        
        db = SessionLocal()
        
        try:
            document = DocumentCRUD.get_document_by_id(db, doc_id)
            if not document:
                yield f"data: {json.dumps({'status': 'FAILED', 'progress': 0, 'step': '文档不存在', 'error_message': '文档不存在'}, ensure_ascii=False)}\n\n"
                return
            
            # 定义状态回调函数
            async def on_status_change(status: DocumentStatus, error_message: str = None):
                """状态变化时推送给前端"""
                status_info = STATUS_PROGRESS_MAP.get(status, {"progress": 0, "step": "未知"})
                data = {
                    "status": status.value,
                    "progress": status_info["progress"],
                    "step": status_info["step"],
                    "error_message": error_message
                }
                logger.info(f"[SSE推送] doc_id={doc_id} | status={status.value} | step={status_info['step']} | progress={status_info['progress']}%")
                return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            
            # 推送初始状态
            yield await on_status_change(DocumentStatus.QUEUED)
            await asyncio.sleep(0)  # 强制刷新，确保 QUEUED 状态立即发送
            
            # 获取处理器类
            doc_type = document.document_type.value
            ProcessorClass = PROCESSOR_MAP.get((doc_type, track))
            
            if not ProcessorClass:
                error_msg = f"不支持的文档类型: {doc_type}"
                DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.FAILED, error_msg)
                yield await on_status_change(DocumentStatus.FAILED, error_msg)
                return
            
            # 初始化服务
            vector_service = VectorService()
            enhancement_service = None
            if track == 'kb':
                enhancement_service = EnhancementService(minio_service=minio_storage)
            
            # 创建处理器，传入状态回调
            processor_kwargs = {
                "doc_id": doc_id,
                "db_session": db,
                "crud_service": DocumentCRUD,
                "vector_service": vector_service,
                "minio_service": minio_storage,
                "chunk_strategy": "block",
            }
            if enhancement_service:
                processor_kwargs["enhancement_service"] = enhancement_service
            
            processor = ProcessorClass(**processor_kwargs)
            
            # 执行处理，使用生成器模式推送状态
            async for status_event in process_with_status_updates(processor, db, doc_id, on_status_change):
                yield status_event
                await asyncio.sleep(0)  # 让出控制权，确保 SSE 数据立即发送到客户端
                
        except Exception as e:
            logger.error(f"SSE 处理异常: {doc_id}, 错误: {e}", exc_info=True)
            try:
                DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.FAILED, str(e))
            except:
                pass
            yield f"data: {json.dumps({'status': 'FAILED', 'progress': 0, 'step': '处理失败', 'error_message': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            db.close()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


async def process_with_status_updates(processor, db, doc_id: str, on_status_change) -> AsyncGenerator[str, None]:
    """
    执行文档处理并在每个阶段推送状态更新
    
    这个函数包装了处理器的 process 方法，在每个阶段变化时推送状态
    """
    from crud.document_crud import ChunkCRUD
    from services.OcrAndChunk import OCRParserFactory, extract_and_upload_images
    from services.OcrAndChunk.chunk.recursive_chunker import chunk_by_recursive
    from services.OcrAndChunk.chunk.block_chunker import chunk_by_block
    import time
    import asyncio
    
    try:
        start_time = time.time()
        logger.info(f"[SSE处理] 开始处理文档 | doc_id={doc_id}")
        
        # 获取文档信息
        document = DocumentCRUD.get_document_by_id(db, doc_id)
        if not document:
            yield await on_status_change(DocumentStatus.FAILED, "文档不存在")
            return
        
        # ========== 阶段 1: PARSING ==========
        parsing_start = time.time()
        DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.PARSING)
        logger.info(f"[SSE处理] 准备推送 PARSING 状态 | doc_id={doc_id}")
        yield await on_status_change(DocumentStatus.PARSING)
        await asyncio.sleep(0)  # 强制刷新，确保 SSE 数据立即发送
        logger.info(f"[SSE处理] PARSING 状态已推送 | doc_id={doc_id}")
        
        # 从 MinIO 下载 PDF 文件
        pdf_bytes = await processor.minio.download_file_as_bytes(document.file_path)
        if not pdf_bytes:
            error_msg = "无法从 MinIO 下载文件"
            DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.FAILED, error_msg)
            yield await on_status_change(DocumentStatus.FAILED, error_msg)
            return
        
        logger.info(f"[SSE处理] 文件下载完成 | doc_id={doc_id} | 大小={len(pdf_bytes)} bytes")
        
        # OCR 解析
        parser = OCRParserFactory.create_from_config()
        blocks = await parser.parse_bytes(pdf_bytes, document.file_name)
        
        if not blocks:
            error_msg = "OCR 解析失败，未提取到任何内容"
            DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.FAILED, error_msg)
            yield await on_status_change(DocumentStatus.FAILED, error_msg)
            return
        
        logger.info(f"[SSE处理] OCR 解析完成 | doc_id={doc_id} | blocks={len(blocks)} | PARSING阶段耗时={time.time()-parsing_start:.2f}s")
        
        # 图片裁剪上传
        blocks = await extract_and_upload_images(
            pdf_bytes=pdf_bytes,
            blocks=blocks,
            kb_id=document.kb_id or "default",
            doc_id=doc_id,
            storage_service=processor.minio
        )
        
        # ========== 阶段 2: CHUNKING ==========
        DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.CHUNKING)
        yield await on_status_change(DocumentStatus.CHUNKING)
        await asyncio.sleep(0)  # 强制刷新
        
        # 分块
        partitions = [b.to_dict() for b in blocks]
        chunks = chunk_by_block(partitions=partitions, source=document.file_name)
        
        logger.info(f"[SSE处理] 分块完成 | doc_id={doc_id} | chunks={len(chunks)}")
        
        # ========== 阶段 3: ENRICHING ==========
        DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.ENRICHING)
        yield await on_status_change(DocumentStatus.ENRICHING)
        await asyncio.sleep(0)  # 强制刷新
        
        # 检查是否有增强服务（知识库轨道）
        enhancer = getattr(processor, 'enhancer', None)
        
        # 如果有增强服务，生成文档摘要
        if enhancer:
            try:
                # 注意：blocks 变量在此处必须可用
                doc_summary = await enhancer.summarize_document(blocks, document.file_name)
                document.summary = doc_summary
                db.add(document)
                db.commit()
                logger.info(f"[SSE处理] 文档摘要已保存 | doc_id={doc_id} | 摘要长度={len(doc_summary)}")
            except Exception as e:
                logger.error(f"[SSE处理] 生成文档摘要失败: {e}", exc_info=True)
        
        # 内容处理
        from models.models import ChunkType
        chunks_data = []
        
        # 如果有 enhancer，为 Image/Table 启动增强任务
        # 否则使用快速处理
        
        enhancement_tasks = []
        # 临时存储 task 和 chunk 数据的关联，方便后续聚合
        task_map = {} # task_index -> (chunk_index, chunk_type, content, metadata) 
        
        final_chunks_map = {} # chunk_index -> chunk_data
        
        for i, chunk in enumerate(chunks):
            chunk_type = chunk.chunk_type
            content = chunk.content
            metadata = {
                "bboxes": chunk.chunk_bboxes,
                "source": chunk.source
            }
            if chunk.caption:
                metadata["caption"] = chunk.caption
            if chunk.footnote:
                metadata["footnote"] = chunk.footnote
            
            caption = chunk.caption or ""
            footnote = chunk.footnote or ""
            
            if chunk_type == "Image":
                if not content:
                    continue
                
                if enhancer:
                    # 知识库轨道：启动 LLM 增强任务
                    async def enhance_image_task(idx, c_content, c_caption, c_meta):
                        import base64
                        try:
                            # 先下载图片并转换为 base64
                            # c_content 是 MinIO 中的 object path
                            image_bytes = await processor.minio.download_file_as_bytes(c_content)
                            if image_bytes:
                                base64_str = base64.b64encode(image_bytes).decode('utf-8')
                                image_input = f"data:image/jpeg;base64,{base64_str}"
                                desc = await enhancer.enhance_figure(image_input, c_caption)
                            else:
                                logger.warning(f"无法下载图片用于增强: {c_content}")
                                desc = ""

                            parts = [p for p in (c_caption, desc) if p]
                            retrieval_text = "\n".join(parts) if parts else "图片内容"
                            return idx, {
                                'chunk_type': ChunkType.IMAGE.value,
                                'content': c_content,
                                'retrieval_text': retrieval_text,
                                'metadata': c_meta
                            }
                        except Exception as e:
                            logger.error(f"Image enhancement error: {e}")
                            parts = [p for p in (c_caption, "图片内容") if p]
                            return idx, {
                                'chunk_type': ChunkType.IMAGE.value,
                                'content': c_content,
                                'retrieval_text': "\n".join(parts),
                                'metadata': c_meta
                            }

                    enhancement_tasks.append(enhance_image_task(i, content, caption, metadata))
                else:
                    # 会话轨道：快速处理
                    parts = [p for p in (caption, footnote) if p]
                    if not parts:
                        continue
                    retrieval_text = "\n".join(parts)
                    final_chunks_map[i] = {
                        'chunk_type': ChunkType.IMAGE.value,
                        'content': content,
                        'retrieval_text': retrieval_text,
                        'metadata': metadata
                    }

            elif chunk_type == "Table":
                if enhancer:
                    # 知识库轨道：启动 LLM 增强任务
                    async def enhance_table_task(idx, c_content, c_caption, c_meta):
                        try:
                            summary = await enhancer.enhance_table(c_content, c_caption)
                            parts = [p for p in (c_caption, summary) if p]
                            retrieval_text = "\n".join(parts) if parts else c_content
                            return idx, {
                                'chunk_type': ChunkType.TABLE.value,
                                'content': c_content,
                                'retrieval_text': retrieval_text,
                                'metadata': c_meta
                            }
                        except Exception as e:
                            logger.error(f"Table enhancement error: {e}")
                            return idx, {
                                'chunk_type': ChunkType.TABLE.value,
                                'content': c_content,
                                'retrieval_text': c_content,
                                'metadata': c_meta
                            }
                    
                    enhancement_tasks.append(enhance_table_task(i, content, caption, metadata))
                else:
                    # 会话轨道：快速处理
                    parts = [p for p in (caption, footnote) if p]
                    retrieval_text = "\n".join(parts) if parts else content
                    final_chunks_map[i] = {
                        'chunk_type': ChunkType.TABLE.value,
                        'content': content,
                        'retrieval_text': retrieval_text,
                        'metadata': metadata
                    }
            else:
                # Text 类型直接处理
                final_chunks_map[i] = {
                    'chunk_type': ChunkType.TEXT.value,
                    'content': content,
                    'retrieval_text': content,
                    'metadata': metadata
                }
        
        # 等待所有增强任务完成
        if enhancement_tasks:
            logger.info(f"[SSE处理] 开始 LLM 增强 | 任务数={len(enhancement_tasks)}")
            results = await asyncio.gather(*enhancement_tasks)
            for idx, data in results:
                final_chunks_map[idx] = data
            logger.info(f"[SSE处理] LLM 增强完成")

        # 按原始顺序重组 chunks_data
        sorted_indices = sorted(final_chunks_map.keys())
        chunks_data = [final_chunks_map[idx] for idx in sorted_indices]

        
        logger.info(f"[SSE处理] 内容处理完成 | doc_id={doc_id} | 有效chunks={len(chunks_data)}")
        
        # ========== 阶段 4: VECTORIZING ==========
        DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.VECTORIZING)
        yield await on_status_change(DocumentStatus.VECTORIZING)
        await asyncio.sleep(0)  # 强制刷新
        
        # 向量化（同步 HTTP 请求，放到线程池避免阻塞事件循环）
        texts_to_embed = [c['retrieval_text'] for c in chunks_data]
        vectors = await asyncio.to_thread(processor.vectorizer.get_embeddings, texts_to_embed)
        
        valid_chunks = []
        for i, chunk_data in enumerate(chunks_data):
            if vectors[i] is not None:
                chunk_data['content_vector'] = vectors[i]
                valid_chunks.append(chunk_data)
        
        logger.info(f"[SSE处理] 向量化完成 | doc_id={doc_id} | 成功={len(valid_chunks)}")
        
        # ========== 阶段 5: 入库 ==========
        success = ChunkCRUD.save_chunks(
            db,
            doc_id,
            document.kb_id,
            valid_chunks,
            session_id=document.session_id
        )
        
        if not success:
            error_msg = "数据入库失败"
            DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.FAILED, error_msg)
            yield await on_status_change(DocumentStatus.FAILED, error_msg)
            return
        
        # ========== 完成 ==========
        DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.COMPLETED)
        yield await on_status_change(DocumentStatus.COMPLETED)
        
        duration = time.time() - start_time
        logger.info(f"[SSE处理] 文档处理完成 | doc_id={doc_id} | chunks={len(valid_chunks)} | 耗时={duration:.2f}s")
        
    except Exception as e:
        logger.error(f"[SSE处理] 处理异常 | doc_id={doc_id} | 错误={e}", exc_info=True)
        try:
            DocumentCRUD.update_document_status(db, doc_id, DocumentStatus.FAILED, str(e))
        except:
            pass
        yield await on_status_change(DocumentStatus.FAILED, str(e))
