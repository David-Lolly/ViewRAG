"""知识库相关的Pydantic模式定义"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模式 ====================

class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求（旧版，保留兼容）"""
    name: str = Field(..., min_length=1, max_length=255, description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")


class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库请求（新版，user_id 在 body 中）"""
    user_id: str = Field(..., description="用户ID")
    name: str = Field(..., min_length=1, max_length=255, description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")


# ==================== 响应模式 ====================

class KnowledgeBaseResponse(BaseModel):
    """知识库详情响应"""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    summary: Optional[str]
    created_at: datetime
    document_count: Optional[int] = 0  # 文档数量（可选）
    
    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    knowledge_bases: list[KnowledgeBaseResponse]
    total: int


class KnowledgeBaseCreateResponse(BaseModel):
    """知识库创建成功响应"""
    message: str = "知识库创建成功"
    kb_id: str


class KnowledgeBaseDeleteResponse(BaseModel):
    """知识库删除响应"""
    message: str = "知识库已删除"
    kb_id: str






