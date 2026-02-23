"""会话文档API路由

使用 SSE（Server-Sent Events）实时推送文档处理进度。
上传和处理分离：上传接口快速返回，处理通过 SSE 端点进行。
"""

import hashlib
import logging
import time
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session

from crud.database import SessionLocal
from crud.document_crud import DocumentCRUD
from schemas.document_schemas import (
    DocumentResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
    DocumentDeleteResponse,
    DocumentListResponse
)
from models.models import DocumentType, DocumentStatus
from services.storage import minio_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/session", tags=["会话文档"])


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{session_id}/upload_document", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上传文档到会话（仅上传，不处理）
    
    流程：
    1. 校验文件类型和大小
    2. 上传到MinIO
    3. 创建数据库记录（状态为QUEUED）
    4. 立即返回 doc_id
    
    前端收到 doc_id 后，需要调用 /documents/{doc_id}/process 端点开始处理
    """
    try:
        total_start = time.time()
        
        # 1. 校验文件
        filename = file.filename
        if not filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 获取文件扩展名
        ext = filename.split('.')[-1].upper()
        
        # 目前仅支持 PDF 文档
        if ext != 'PDF':
            raise HTTPException(
                status_code=400,
                detail=f"目前仅支持 PDF 文档，暂不支持 {ext} 格式"
            )
        
        # 校验文件类型
        try:
            doc_type = DocumentType[ext]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}"
            )
        
        # 2. 计算文件哈希并查重
        file_content = await file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        await file.seek(0)  # 重置指针，后续上传MinIO需要
        
        existing = DocumentCRUD.check_duplicate_by_hash(db, file_hash, session_id=session_id)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"该会话中已存在相同文件：{existing.file_name}"
            )
        
        file_size = file.size or len(file_content)
        file_size_mb = f"{file_size / 1024 / 1024:.2f}MB" if file_size else "未知"
        logger.info(f"[上传] 开始 | session={session_id} | 文件={filename} | 大小={file_size_mb} | hash={file_hash[:12]}...")
        
        # 3. 上传到MinIO
        minio_start = time.time()
        minio_result = await minio_storage.upload_document_stream(
            file_stream=file.file,
            file_size=file.size,
            filename=filename,
            content_type=file.content_type or 'application/octet-stream',
            owner_id=session_id,
            owner_type='session'
        )
        minio_elapsed = time.time() - minio_start
        
        storage_path = minio_result['storage_path']
        logger.info(f"[上传] MinIO上传完成 | 文件={filename} | 耗时={minio_elapsed:.2f}s | 路径={storage_path}")
        
        # 4. 创建数据库记录（状态为QUEUED）
        db_start = time.time()
        document = DocumentCRUD.create_document(
            session=db,
            file_name=filename,
            file_path=storage_path,
            document_type=doc_type,
            session_id=session_id,
            file_hash=file_hash
        )
        db_elapsed = time.time() - db_start
        
        if not document:
            raise HTTPException(status_code=500, detail="创建文档记录失败")
        
        logger.info(f"[上传] 数据库记录创建完成 | doc_id={document.id} | 耗时={db_elapsed:.2f}s")
        
        total_elapsed = time.time() - total_start
        logger.info(
            f"[上传] 接口完成 | doc_id={document.id} | 文件={filename} | "
            f"总耗时={total_elapsed:.2f}s | MinIO={minio_elapsed:.2f}s | DB={db_elapsed:.2f}s"
        )
        
        # 4. 立即返回 doc_id，前端需要调用 /documents/{doc_id}/process 开始处理
        return DocumentUploadResponse(
            message="文件上传成功，请调用处理接口开始解析",
            doc_id=document.id,
            status=DocumentStatus.QUEUED
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router.get("/{session_id}/documents")
async def list_documents(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    获取会话的所有文档列表
    """
    try:
        documents = DocumentCRUD.get_documents_by_session_id(db, session_id)
        
        return DocumentListResponse(
            documents=[DocumentResponse.from_orm(doc) for doc in documents],
            total=len(documents)
        )
        
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.delete("/{session_id}/document/{doc_id}")
async def delete_document(
    session_id: str,
    doc_id: str,
    db: Session = Depends(get_db)
):
    """
    删除/取消文档
    
    功能：
    - 删除 MinIO 中的文档文件
    - 删除数据库记录（通过 CASCADE 自动清理关联的 Chunk）
    """
    try:
        # 1. 先获取文档信息，确认存在且属于该会话
        document = DocumentCRUD.get_document_by_id(db, doc_id)
        if not document or document.session_id != session_id:
            raise HTTPException(status_code=404, detail="文档不存在或无权删除")
        
        # 2. 删除 MinIO 中的文件
        if minio_storage:
            try:
                minio_storage.delete_document_files(
                    owner_id=session_id,
                    owner_type='session',
                    doc_id=doc_id
                )
                logger.info(f"MinIO 文件已删除: doc_id={doc_id}")
            except Exception as e:
                logger.warning(f"删除 MinIO 文件失败: doc_id={doc_id}, 错误: {e}")
        
        # 3. 删除数据库记录（CASCADE 自动删除关联的 Chunk）
        success = DocumentCRUD.delete_document(db, doc_id, session_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="删除数据库记录失败")
        
        logger.info(f"文档已完全删除: doc_id={doc_id}, session_id={session_id}")
        
        return DocumentDeleteResponse(
            message="文档已删除",
            doc_id=doc_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")




