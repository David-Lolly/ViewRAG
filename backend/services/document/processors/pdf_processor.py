"""
统一的 PDF 处理器

使用新的 OCR 解析架构处理 PDF 文档，支持：
- OCR 解析（PaddleOCR 等）
- 图片裁剪和上传
- 分块处理
- LLM 内容增强（图片描述、表格摘要）
- 向量化和入库

需求: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import logging
import time
from typing import List, Dict, Any, Optional

from .base import BaseDocumentProcessor
from models.models import DocumentStatus, ChunkType

logger = logging.getLogger(__name__)


class PDFProcessor(BaseDocumentProcessor):
    """
    统一的 PDF 处理器
    
    处理流程：
    1. OCR 解析 → SimpleBlock 列表
    2. 图片裁剪上传 → 更新 Image 块的 content
    3. 分块 → Chunk 列表
    4. LLM 增强 → 图片描述、表格摘要
    5. 向量化
    6. 入库（Chunk 表）
    
    需求: 4.1, 4.2, 4.3, 4.4, 4.5
    """
    
    def __init__(
        self,
        doc_id: str,
        db_session,
        crud_service,
        vector_service,
        enhancement_service=None,
        minio_service=None,
        ocr_parser_name: str = "paddle_ocr",
        chunk_strategy: str = "block",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        **kwargs
    ):
        """
        初始化 PDF 处理器
        
        Args:
            doc_id: 文档 ID
            db_session: 数据库会话
            crud_service: DocumentCRUD 实例
            vector_service: VectorService 实例
            enhancement_service: EnhancementService 实例（可选）
            minio_service: MinIO 服务实例（可选）
            ocr_parser_name: OCR 解析器名称，默认 'paddle_ocr'
            chunk_strategy: 分块策略，'block' 或 'recursive'，默认 'block'
            chunk_size: 分块大小，默认 500
            chunk_overlap: 分块重叠，默认 50
        """
        # 调用父类初始化（传递必要参数）
        super().__init__(
            doc_id=doc_id,
            db_session=db_session,
            crud_service=crud_service,
            parsing_service=None,  # 不使用旧的解析服务
            chunking_service=None,  # 不使用旧的分块服务
            vector_service=vector_service,
            enhancement_service=enhancement_service,
            minio_service=minio_service,
            **kwargs
        )
        
        self.ocr_parser_name = ocr_parser_name
        self.chunk_strategy = chunk_strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        logger.info(
            f"PDFProcessor 初始化 | doc_id={doc_id} | "
            f"parser={ocr_parser_name} | strategy={chunk_strategy}"
        )

    async def process(self):
        """
        执行 PDF 处理的完整流程
        
        流程：
        1. OCR 解析 → SimpleBlock 列表
        2. 图片裁剪上传 → 更新 Image 块的 content
        3. 分块 → Chunk 列表
        4. LLM 增强 → 图片描述、表格摘要
        5. 向量化
        6. 入库
        """
        from crud.document_crud import ChunkCRUD
        from services.OcrAndChunk import OCRParserFactory, extract_and_upload_images
        from services.OcrAndChunk.chunk.recursive_chunker import chunk_by_recursive
        from services.OcrAndChunk.chunk.block_chunker import chunk_by_block
        from services.OcrAndChunk.image_extractor import extract_image_bytes_from_pdf
        import asyncio as _asyncio
        
        try:
            start_time = time.time()
            logger.info(f"开始处理 PDF | doc_id={self.doc_id}")
            
            # 获取文档信息
            document = self.crud.get_document_by_id(self.db, self.doc_id)
            if not document:
                logger.error(f"文档不存在: {self.doc_id}")
                return
            
            # ========== 阶段 1: OCR 解析 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | QUEUED -> PARSING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.PARSING
            )
            
            # 从 MinIO 下载 PDF 文件
            pdf_bytes = await self.minio.download_file_as_bytes(document.file_path)
            if not pdf_bytes:
                error_msg = "无法从 MinIO 下载 PDF 文件"
                self.crud.update_document_status(
                    self.db, self.doc_id, DocumentStatus.FAILED, error_msg
                )
                logger.error(f"[{self.doc_id}] {error_msg}")
                return
            
            logger.info(f"PDF 下载完成 | doc_id={self.doc_id} | 大小={len(pdf_bytes)} bytes")
            
            # 获取 OCR 解析器并解析（从配置读取 API 参数）
            parser = OCRParserFactory.create_from_config()
            blocks = await parser.parse_bytes(
                pdf_bytes,
                document.file_name
            )
            
            if not blocks:
                error_msg = "OCR 解析失败，未提取到任何内容"
                self.crud.update_document_status(
                    self.db, self.doc_id, DocumentStatus.FAILED, error_msg
                )
                logger.error(f"[{self.doc_id}] {error_msg}")
                return
            
            logger.info(f"OCR 解析完成 | doc_id={self.doc_id} | blocks={len(blocks)}")
            
            # ========== 阶段 2: 图片裁剪上传 ==========
            # 提取并上传图片，更新 Image 块的 content 为 MinIO 路径
            blocks = await extract_and_upload_images(
                pdf_bytes=pdf_bytes,
                blocks=blocks,
                kb_id=document.kb_id or "default",
                doc_id=self.doc_id,
                storage_service=self.minio
            )
            
            # 统计图片处理结果
            image_blocks = [b for b in blocks if b.type == "Image"]
            uploaded_images = [b for b in image_blocks if b.content]
            logger.info(
                f"图片处理完成 | doc_id={self.doc_id} | "
                f"总图片={len(image_blocks)} | 上传成功={len(uploaded_images)}"
            )
            
            # ========== 启动文档摘要任务（不阻塞后续流程） ==========
            summary_task = None
            if self.enhancer:
                summary_task = _asyncio.create_task(
                    self._generate_document_summary(blocks, document.file_name)
                )
            
            # ========== 阶段 3: 分块 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | PARSING -> CHUNKING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.CHUNKING
            )
            
            # 将 SimpleBlock 转换为字典格式供分块器使用
            partitions = [b.to_dict() for b in blocks]
            
            # 根据策略选择分块方法
            if self.chunk_strategy == "block":
                chunks = chunk_by_block(
                    partitions=partitions,
                    source=document.file_name
                )
            else:
                chunks = chunk_by_recursive(
                    partitions=partitions,
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    source=document.file_name
                )
            
            logger.info(f"分块完成 | doc_id={self.doc_id} | chunks={len(chunks)}")
            
            # ========== 阶段 4: 内容增强 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | CHUNKING -> ENRICHING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.ENRICHING
            )
            
            chunks_data = []
            skipped_chunks = 0
            
            if self.enhancer:
                # 知识库轨道：Image/Table 走 LLM 增强
                llm_coroutines = []
                
                for chunk in chunks:
                    if chunk.chunk_type in ("Image", "Table"):
                        llm_coroutines.append(
                            self._process_chunk(chunk=chunk, pdf_bytes=pdf_bytes, document=document)
                        )
                    else:
                        chunks_data.append(self._process_text_chunk(
                            chunk=chunk,
                            metadata=self._build_chunk_metadata(chunk)
                        ))
                
                llm_results = await _asyncio.gather(*llm_coroutines, return_exceptions=True)
                
                for result in llm_results:
                    if isinstance(result, Exception):
                        logger.warning(f"LLM 增强任务异常: {result}")
                        skipped_chunks += 1
                    elif result is None:
                        skipped_chunks += 1
                    else:
                        chunks_data.append(result)
            else:
                # 会话轨道：Image/Table 走轻量快速处理，不调 LLM
                for chunk in chunks:
                    if chunk.chunk_type == "Image":
                        result = self._process_image_chunk_fast(
                            chunk=chunk,
                            metadata=self._build_chunk_metadata(chunk)
                        )
                        if result is not None:
                            chunks_data.append(result)
                        else:
                            skipped_chunks += 1
                    elif chunk.chunk_type == "Table":
                        chunks_data.append(self._process_table_chunk_fast(
                            chunk=chunk,
                            metadata=self._build_chunk_metadata(chunk)
                        ))
                    else:
                        chunks_data.append(self._process_text_chunk(
                            chunk=chunk,
                            metadata=self._build_chunk_metadata(chunk)
                        ))
            
            logger.info(
                f"内容增强完成 | doc_id={self.doc_id} | "
                f"有效 chunks={len(chunks_data)} | 跳过={skipped_chunks}"
            )
            
            # ========== 阶段 5: 向量化 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | ENRICHING -> VECTORIZING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.VECTORIZING
            )
            
            # 提取所有 retrieval_text 进行向量化
            texts_to_embed = [c['retrieval_text'] for c in chunks_data]
            
            logger.info(f"开始向量化 | doc_id={self.doc_id} | 文本数={len(texts_to_embed)}")
            vectors = await _asyncio.to_thread(self.vectorizer.get_embeddings, texts_to_embed)
            
            # 将向量添加到 chunks_data
            valid_chunks = []
            for i, chunk_data in enumerate(chunks_data):
                if vectors[i] is not None:
                    chunk_data['content_vector'] = vectors[i]
                    valid_chunks.append(chunk_data)
                else:
                    logger.warning(f"向量化失败，跳过 chunk: index={i}")
            
            logger.info(
                f"向量化完成 | doc_id={self.doc_id} | "
                f"成功={len(valid_chunks)} | 失败={len(chunks_data) - len(valid_chunks)}"
            )
            
            # ========== 阶段 6: 入库 ==========
            success = ChunkCRUD.save_chunks(
                self.db,
                self.doc_id,
                document.kb_id,
                valid_chunks,
                session_id=document.session_id
            )
            
            if not success:
                error_msg = "数据入库失败"
                self.crud.update_document_status(
                    self.db, self.doc_id, DocumentStatus.FAILED, error_msg
                )
                logger.error(f"[{self.doc_id}] {error_msg}")
                return
            
            # ========== 完成 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | VECTORIZING -> COMPLETED")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.COMPLETED
            )
            
            # ========== 等待摘要任务完成并写入 ==========
            if summary_task is not None:
                try:
                    summary_text = await summary_task
                    if summary_text:
                        self.crud.update_document_summary(self.db, self.doc_id, summary_text)
                except Exception as e:
                    logger.warning(f"文档摘要写入失败（不影响主流程）: {e}")
            
            duration = time.time() - start_time
            logger.info(
                f"PDF 处理完成 | doc_id={self.doc_id} | "
                f"chunks={len(valid_chunks)} | 耗时={duration:.2f}s | ✓"
            )
            
        except Exception as e:
            error_msg = f"处理异常: {str(e)}"
            logger.error(f"处理失败 | doc_id={self.doc_id} | 错误={error_msg}", exc_info=True)
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.FAILED, error_msg
            )

    async def _process_chunk(
        self,
        chunk,
        pdf_bytes: bytes,
        document
    ) -> Optional[Dict[str, Any]]:
        """
        处理单个 Chunk，根据类型进行 LLM 增强
        
        Args:
            chunk: Chunk 对象
            pdf_bytes: PDF 文件字节流（用于图片裁剪）
            document: Document 对象
            
        Returns:
            处理后的 chunk 数据字典，或 None（跳过该 chunk）
        """
        from services.OcrAndChunk.image_extractor import extract_image_bytes_from_pdf
        
        chunk_type = chunk.chunk_type
        content = chunk.content
        caption = chunk.caption or ""
        
        # 构建基础元数据（包含 bbox 和页码信息）
        # 需求 4.5: 存储时在 chunk_metadata 中包含 bbox 和页码信息
        metadata = {
            "bboxes": chunk.chunk_bboxes,
            "source": chunk.source
        }
        if caption:
            metadata["caption"] = caption
        if chunk.footnote:
            metadata["footnote"] = chunk.footnote
        
        # 根据类型处理
        if chunk_type == "Image":
            return await self._process_image_chunk(
                chunk=chunk,
                pdf_bytes=pdf_bytes,
                metadata=metadata
            )
        elif chunk_type == "Table":
            return await self._process_table_chunk(
                chunk=chunk,
                metadata=metadata
            )
        else:
            # 文本类型（Title, Text, Formula 等）
            return self._process_text_chunk(
                chunk=chunk,
                metadata=metadata
            )
    
    async def _process_image_chunk(
        self,
        chunk,
        pdf_bytes: bytes,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        处理 Image 类型 Chunk
        
        需求 4.2, 6.3:
        - 获取图片字节流，调用 LLM 生成描述
        - content 存储 MinIO 相对路径
        - retrieval_text 存储 LLM 描述
        
        Args:
            chunk: Chunk 对象
            pdf_bytes: PDF 文件字节流
            metadata: 元数据字典
            
        Returns:
            处理后的 chunk 数据，或 None（跳过）
        """
        from services.OcrAndChunk.image_extractor import extract_image_bytes_from_pdf
        
        content = chunk.content  # MinIO 相对路径（由 extract_and_upload_images 填充）
        caption = chunk.caption or ""
        
        # 如果没有上传成功（content 为空），跳过
        if not content:
            logger.warning(f"Image chunk 无 content，跳过")
            return None
        
        # 获取图片字节流用于 LLM 描述
        # 从 chunk_bboxes 获取位置信息
        if chunk.chunk_bboxes and len(chunk.chunk_bboxes) > 0:
            bbox_info = chunk.chunk_bboxes[0]
            page_num = bbox_info.get("page", 0)
            bbox = bbox_info.get("bbox", [])
            
            if bbox and len(bbox) == 4:
                image_bytes = extract_image_bytes_from_pdf(
                    pdf_bytes=pdf_bytes,
                    page_num=page_num,
                    bbox=tuple(bbox)
                )
            else:
                image_bytes = None
        else:
            image_bytes = None
        
        # 调用 LLM 生成图片描述
        description = ""
        if self.enhancer and image_bytes:
            try:
                # 将图片字节转为 base64 data URL
                import base64
                base64_data = base64.b64encode(image_bytes).decode('utf-8')
                image_data_url = f"data:image/jpeg;base64,{base64_data}"
                
                description = await self.enhancer.enhance_figure(
                    image_url=image_data_url,
                    caption=caption
                )
            except Exception as e:
                logger.warning(f"图片 LLM 增强失败: {e}")
                description = ""
        
        # 如果 LLM 返回空（表示应跳过，如装饰性图片），直接过滤
        # 无意义图片不需要进行后续的向量化和入库
        if not description:
            logger.info(f"图片被 LLM 判定为无意义，跳过 | caption={caption[:50] if caption else 'N/A'}")
            return None
        
        return {
            'chunk_type': ChunkType.IMAGE.value,
            'content': content,  # MinIO 相对路径
            'retrieval_text': description,  # LLM 描述
            'metadata': metadata
        }
    
    async def _process_table_chunk(
        self,
        chunk,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        处理 Table 类型 Chunk
        
        需求 4.3:
        - content 存储 HTML 内容
        - retrieval_text 存储 LLM 摘要
        
        Args:
            chunk: Chunk 对象
            metadata: 元数据字典
            
        Returns:
            处理后的 chunk 数据
        """
        content = chunk.content  # HTML 表格内容
        caption = chunk.caption or ""
        
        # 调用 LLM 生成表格摘要
        summary = ""
        if self.enhancer and content:
            try:
                summary = await self.enhancer.enhance_table(
                    table_markdown=content,
                    caption=caption
                )
            except Exception as e:
                logger.warning(f"表格 LLM 增强失败: {e}")
                summary = ""
        
        # 如果 LLM 返回空，使用 caption 作为 fallback
        if not summary:
            summary = f"表格: {caption}" if caption else content[:200] if content else "表格内容"
        
        return {
            'chunk_type': ChunkType.TABLE.value,
            'content': content,  # HTML 内容
            'retrieval_text': summary,  # LLM 摘要
            'metadata': metadata
        }
    
    def _process_text_chunk(
        self,
        chunk,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理文本类型 Chunk（Title, Text, Formula 等）
        
        需求 4.4:
        - content 和 retrieval_text 相同
        
        Args:
            chunk: Chunk 对象
            metadata: 元数据字典
            
        Returns:
            处理后的 chunk 数据
        """
        content = chunk.content
        
        return {
            'chunk_type': ChunkType.TEXT.value,
            'content': content,
            'retrieval_text': content,  # 文本类型，检索文本与内容相同
            'metadata': metadata
        }
    
    def _process_image_chunk_fast(
        self,
        chunk,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        会话轨道专用：轻量处理 Image chunk，不调 LLM
        
        有 caption 或 footnote → 拼接作为 retrieval_text，入库
        都为空 → 跳过
        """
        content = chunk.content  # MinIO 相对路径
        if not content:
            logger.warning(f"Image chunk 无 content，跳过")
            return None
        
        caption = chunk.caption or ""
        footnote = chunk.footnote or ""
        
        parts = [p for p in (caption, footnote) if p]
        if not parts:
            logger.info(f"Image chunk 无 caption/footnote，跳过 | content={content}")
            return None
        
        retrieval_text = "\n".join(parts)
        
        return {
            'chunk_type': ChunkType.IMAGE.value,
            'content': content,
            'retrieval_text': retrieval_text,
            'metadata': metadata
        }
    
    def _process_table_chunk_fast(
        self,
        chunk,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        会话轨道专用：轻量处理 Table chunk，不调 LLM
        
        拼接 caption/footnote 中不为空的部分作为 retrieval_text，
        都为空则用表格 HTML 本体作为 retrieval_text。
        """
        content = chunk.content or ""
        caption = chunk.caption or ""
        footnote = chunk.footnote or ""
        
        parts = [p for p in (caption, footnote) if p]
        retrieval_text = "\n".join(parts) if parts else content
        
        return {
            'chunk_type': ChunkType.TABLE.value,
            'content': content,
            'retrieval_text': retrieval_text,
            'metadata': metadata
        }
    
    def _build_chunk_metadata(self, chunk) -> Dict[str, Any]:
        """构建 chunk 的元数据字典"""
        caption = chunk.caption or ""
        metadata = {
            "bboxes": chunk.chunk_bboxes,
            "source": chunk.source
        }
        if caption:
            metadata["caption"] = caption
        if chunk.footnote:
            metadata["footnote"] = chunk.footnote
        return metadata

    async def _generate_document_summary(self, blocks, file_name: str) -> str:
        """调用 EnhancementService 生成文档摘要（供 create_task 使用）"""
        try:
            return await self.enhancer.summarize_document(blocks, doc_name=file_name)
        except Exception as e:
            logger.warning(f"文档摘要生成异常: {e}")
            return ""
