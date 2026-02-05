"""文档相关的Pydantic模式定义"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from models.models import DocumentType, DocumentStatus


# ==================== 请求模式 ====================

class DocumentCreate(BaseModel):
    """创建文档请求"""
    file_name: str = Field(..., description="文件名")
    file_path: str = Field(..., description="MinIO存储路径")
    document_type: DocumentType = Field(..., description="文档类型")
    session_id: Optional[str] = Field(None, description="会话ID（会话轨道）")
    kb_id: Optional[str] = Field(None, description="知识库ID（知识库轨道）")


# ==================== 响应模式 ====================

class DocumentResponse(BaseModel):
    """文档详情响应"""
    id: str
    session_id: Optional[str]
    kb_id: Optional[str]
    file_name: str
    file_path: str
    document_type: DocumentType
    status: DocumentStatus
    error_message: Optional[str]
    created_at: datetime
    summary: Optional[str] = None
    
    class Config:
        from_attributes = True


class DocumentStatusResponse(BaseModel):
    """文档状态响应（用于前端轮询）"""
    id: str
    file_name: str
    status: DocumentStatus
    error_message: Optional[str] = None
    progress: Optional[str] = None  # 可选的进度描述
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """文档上传成功响应"""
    message: str = "文件已接收，正在后台处理中"
    doc_id: str
    status: DocumentStatus = DocumentStatus.QUEUED


class DocumentDeleteResponse(BaseModel):
    """文档删除响应"""
    message: str = "文档已删除"
    doc_id: str

