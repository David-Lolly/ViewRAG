"""知识库API路由"""

import logging
import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session

from crud.database import SessionLocal
from crud.kb_crud import KnowledgeBaseCRUD
from crud.document_crud import DocumentCRUD
from schemas.kb_schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseCreateResponse,
    KnowledgeBaseDeleteResponse
)
from schemas.document_schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse
)
from models.models import DocumentType
from celery_tasks.document_processing import process_kb_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kb", tags=["知识库"])


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_kb(
    kb_data: KnowledgeBaseCreate,
    user_id: str,  # TODO: 从JWT token或session获取
    db: Session = Depends(get_db)
):
    """创建知识库"""
    try:
        kb = KnowledgeBaseCRUD.create_kb(
            session=db,
            user_id=user_id,
            name=kb_data.name,
            description=kb_data.description
        )
        
        if not kb:
            raise HTTPException(status_code=500, detail="创建知识库失败")
        
        logger.info(f"知识库创建成功: {kb.id}, 名称: {kb.name}")
        
        return KnowledgeBaseCreateResponse(
            message="知识库创建成功",
            kb_id=kb.id
        )
        
    except Exception as e:
        logger.error(f"创建知识库失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("/")
async def list_kbs(
    user_id: str,  # TODO: 从JWT token或session获取
    db: Session = Depends(get_db)
):
    """获取用户的所有知识库"""
    try:
        kbs = KnowledgeBaseCRUD.get_user_kbs_with_count(db, user_id)
        
        return KnowledgeBaseListResponse(
            knowledge_bases=kbs,
            total=len(kbs)
        )
        
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/{kb_id}/documents")
async def list_kb_documents(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """获取知识库的所有文档"""
    try:
        documents = DocumentCRUD.get_documents_by_kb_id(db, kb_id)
        
        return DocumentListResponse(
            documents=[DocumentResponse.from_orm(doc) for doc in documents],
            total=len(documents)
        )
        
    except Exception as e:
        logger.error(f"获取知识库文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/{kb_id}/upload_file", status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    kb_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上传文档到知识库
    
    流程：
    1. 校验文件
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
        
        ext = filename.split('.')[-1].upper()
        
        try:
            doc_type = DocumentType[ext]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}"
            )
        
        # 2. 上传到MinIO
        from services.storage import minio_storage
        
        minio_result = await minio_storage.upload_document_stream(
            file_stream=file.file,
            file_size=file.size,
            filename=filename,
            content_type=file.content_type or 'application/octet-stream',
            owner_id=kb_id,
            owner_type='kb'
        )
        
        storage_path = minio_result['storage_path']
        
        # 3. 创建数据库记录
        document = DocumentCRUD.create_document(
            session=db,
            file_name=filename,
            file_path=storage_path,
            document_type=doc_type,
            kb_id=kb_id
        )
        
        if not document:
            raise HTTPException(status_code=500, detail="创建文档记录失败")
        
        # 4. 派发Celery任务
        process_kb_document.delay(document.id)
        
        logger.info(f"知识库文档上传成功: {document.id}")
        
        # 5. 返回202
        return DocumentUploadResponse(
            message="文件已接收，正在后台处理中",
            doc_id=document.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: str,
    user_id: str,  # TODO: 从JWT token获取
    db: Session = Depends(get_db)
):
    """删除知识库（包括所有文档和数据）"""
    try:
        success = KnowledgeBaseCRUD.delete_kb(db, kb_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="知识库不存在或无权删除")
        
        logger.info(f"知识库已删除: {kb_id}")
        
        return KnowledgeBaseDeleteResponse(
            message="知识库已删除",
            kb_id=kb_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

