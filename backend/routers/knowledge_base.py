"""知识库API路由

使用 SSE 实时推送文档处理进度，替代轮询方案。
上传接口只负责上传到 MinIO + 创建数据库记录，立即返回 doc_id。
前端通过 SSE 端点 /api/v1/documents/{doc_id}/process?track=kb 获取处理进度。
"""

import hashlib
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
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseCreateResponse,
    KnowledgeBaseDeleteResponse
)
from schemas.document_schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    DocumentDeleteResponse
)
from models.models import DocumentType, DocumentStatus

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
    kb_data: KnowledgeBaseCreateRequest,
    db: Session = Depends(get_db)
):
    """创建知识库（user_id 从请求体中读取）"""
    try:
        kb = KnowledgeBaseCRUD.create_kb(
            session=db,
            user_id=kb_data.user_id,
            name=kb_data.name,
            description=kb_data.description
        )
        
        if not kb:
            raise HTTPException(status_code=500, detail="创建知识库失败")
        
        logger.info(f"知识库创建成功: {kb.id}, 名称: {kb.name}")
        
        return KnowledgeBaseResponse(
            id=kb.id,
            user_id=kb.user_id,
            name=kb.name,
            description=kb.description,
            summary=kb.summary,
            created_at=kb.created_at,
            document_count=0
        )
        
    except HTTPException:
        raise
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


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_kb_detail(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """获取知识库详情"""
    try:
        kb = KnowledgeBaseCRUD.get_kb_by_id(db, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        doc_count = len(DocumentCRUD.get_documents_by_kb_id(db, kb_id))
        
        return KnowledgeBaseResponse(
            id=kb.id,
            user_id=kb.user_id,
            name=kb.name,
            description=kb.description,
            summary=kb.summary,
            created_at=kb.created_at,
            document_count=doc_count
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库详情失败: {e}")
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


# 单个文件最大 10MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# 支持的文件扩展名集合
SUPPORTED_EXTENSIONS = {dt.name for dt in DocumentType}


def _validate_file(file: UploadFile) -> tuple:
    """
    校验单个文件的类型和大小。
    返回 (doc_type, error_message)，error_message 为 None 表示校验通过。
    """
    filename = file.filename
    if not filename:
        return None, "文件名不能为空"

    ext = filename.rsplit('.', 1)[-1].upper() if '.' in filename else ""
    
    # 目前仅支持 PDF 文档
    if ext != 'PDF':
        return None, f"目前仅支持 PDF 文档，暂不支持 {ext} 格式"

    if file.size is not None and file.size > MAX_FILE_SIZE_BYTES:
        return None, f"文件 {filename} 超过 10MB 大小限制"

    return DocumentType[ext], None


@router.post("/{kb_id}/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_files(
    kb_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    上传文档到知识库（新端点，支持多文件，字段名 files，单个文件≤10MB）

    流程：
    1. 校验每个文件的类型和大小
    2. 上传到MinIO
    3. 创建数据库记录（状态为QUEUED）
    4. 返回每个文件的 doc_id，前端通过 SSE 端点获取处理进度
    """
    from services.storage import minio_storage

    results = []
    for file in files:
        doc_type, error = _validate_file(file)
        if error:
            results.append({"file_name": file.filename or "unknown", "success": False, "error": error})
            continue

        try:
            # 计算文件哈希并查重
            file_content = await file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            await file.seek(0)
            
            existing = DocumentCRUD.check_duplicate_by_hash(db, file_hash, kb_id=kb_id)
            if existing:
                results.append({
                    "file_name": file.filename,
                    "success": False,
                    "error": f"该知识库中已存在相同文件：{existing.file_name}"
                })
                continue

            minio_result = await minio_storage.upload_document_stream(
                file_stream=file.file,
                file_size=file.size,
                filename=file.filename,
                content_type=file.content_type or 'application/octet-stream',
                owner_id=kb_id,
                owner_type='kb'
            )

            document = DocumentCRUD.create_document(
                session=db,
                file_name=file.filename,
                file_path=minio_result['storage_path'],
                document_type=doc_type,
                kb_id=kb_id,
                file_hash=file_hash
            )

            if not document:
                results.append({"file_name": file.filename, "success": False, "error": "创建文档记录失败"})
                continue

            logger.info(f"知识库文档上传成功: {document.id}，等待前端建立 SSE 连接处理")
            results.append({
                "file_name": file.filename,
                "success": True,
                "doc_id": document.id,
                "status": DocumentStatus.QUEUED.value
            })

        except Exception as e:
            logger.error(f"文件 {file.filename} 上传失败: {e}", exc_info=True)
            results.append({"file_name": file.filename, "success": False, "error": str(e)})

    return {"documents": results}


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_kb_document(
    kb_id: str,
    doc_id: str,
    db: Session = Depends(get_db)
):
    """
    删除知识库中的单个文档
    
    功能：
    - 删除 MinIO 中的文档文件
    - 删除数据库记录（通过 CASCADE 自动清理关联的 Chunk）
    """
    from services.storage import minio_storage
    
    try:
        # 1. 先获取文档信息，确认存在且属于该知识库
        document = DocumentCRUD.get_document_by_id(db, doc_id)
        if not document or document.kb_id != kb_id:
            raise HTTPException(status_code=404, detail="文档不存在或不属于该知识库")
        
        # 2. 删除 MinIO 中的文件
        if minio_storage:
            try:
                minio_storage.delete_document_files(
                    owner_id=kb_id,
                    owner_type='kb',
                    doc_id=doc_id
                )
                logger.info(f"MinIO 文件已删除: doc_id={doc_id}, kb_id={kb_id}")
            except Exception as e:
                logger.warning(f"删除 MinIO 文件失败: doc_id={doc_id}, 错误: {e}")
        
        # 3. 删除数据库记录（CASCADE 自动删除关联的 Chunk）
        success = DocumentCRUD.delete_document(db, doc_id, owner_id=kb_id)

        if not success:
            raise HTTPException(status_code=500, detail="删除数据库记录失败")

        logger.info(f"知识库文档已完全删除: doc_id={doc_id}, kb_id={kb_id}")

        return DocumentDeleteResponse(
            message="文档已删除",
            doc_id=doc_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """删除知识库（包括所有文档和数据）"""
    try:
        success = KnowledgeBaseCRUD.delete_kb_by_id(db, kb_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
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

