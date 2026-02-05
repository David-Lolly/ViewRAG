"""会话文档API路由"""

import logging
import uuid
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
from celery_tasks.document_processing import process_session_document

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
    上传文档到会话
    
    流程：
    1. 校验文件类型和大小
    2. 上传到MinIO
    3. 创建数据库记录
    4. 派发Celery任务
    5. 立即返回202
    """
    try:
        # 1. 校验文件
        filename = file.filename
        if not filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 获取文件扩展名
        ext = filename.split('.')[-1].upper()
        
        # 校验文件类型
        try:
            doc_type = DocumentType[ext]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}。支持的类型: PDF, DOCX, TXT, MARKDOWN, PPTX"
            )
        
        # 2. 上传到MinIO
        minio_result = await minio_storage.upload_document_stream(
            file_stream=file.file,
            file_size=file.size,
            filename=filename,
            content_type=file.content_type or 'application/octet-stream',
            owner_id=session_id,
            owner_type='session'
        )
        
        storage_path = minio_result['storage_path']
        
        # 3. 创建数据库记录
        document = DocumentCRUD.create_document(
            session=db,
            file_name=filename,
            file_path=storage_path,
            document_type=doc_type,
            session_id=session_id
        )
        
        if not document:
            raise HTTPException(status_code=500, detail="创建文档记录失败")
        
        # 4. 派发Celery任务
        process_session_document.delay(document.id)
        
        logger.info(f"文档上传成功: {document.id}, 文件名: {filename}")
        
        # 5. 返回202
        return DocumentUploadResponse(
            message="文件已接收，正在后台处理中",
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
    - 如果文档正在处理，会触发协作式取消
    - 如果文档已完成，会删除所有相关数据
    - 通过ON DELETE CASCADE自动清理关联数据
    """
    try:
        success = DocumentCRUD.delete_document(db, doc_id, session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="文档不存在或无权删除")
        
        logger.info(f"文档已删除: {doc_id}")
        
        return DocumentDeleteResponse(
            message="文档已删除",
            doc_id=doc_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.get("/documents_status")
async def get_documents_status(
    doc_ids: str,  # 逗号分隔的doc_id列表
    db: Session = Depends(get_db)
):
    """
    批量查询文档处理状态（用于前端轮询）
    
    Args:
        doc_ids: 逗号分隔的文档ID，如 "id1,id2,id3"
    """
    try:
        doc_id_list = [id.strip() for id in doc_ids.split(',') if id.strip()]
        
        if not doc_id_list:
            return {"statuses": []}
        
        statuses = []
        for doc_id in doc_id_list:
            document = DocumentCRUD.get_document_by_id(db, doc_id)
            if document:
                statuses.append(DocumentStatusResponse(
                    id=document.id,
                    file_name=document.file_name,
                    status=document.status,
                    error_message=document.error_message
                ))
        
        return {"statuses": statuses}
        
    except Exception as e:
        logger.error(f"查询文档状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

