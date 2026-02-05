"""api request schemas."""
from typing import Optional, List
from pydantic import BaseModel


class LoginRequest(BaseModel):
    user_id: str
    password: str


class RegisterRequest(BaseModel):
    user_id: str
    password: str

class SearchRequest(BaseModel):
    query: Optional[str] = None
    session_id: Optional[str] = None
    user_id: str
    use_web: bool = True
    selected_model: Optional[str] = None  # 新增：用户选择的对话模型名称
    image_url: Optional[str] = None  # 新增：上传的图片URL（base64或URL）
    document_ids: Optional[List[str]] = None  # 新增：RAG文档ID列表（用于文档问答）

class SessionRequest(BaseModel):
    user_id: str
    title: Optional[str] = None

class TestRequest(BaseModel):
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    cse_id: Optional[str] = None
    model_type: Optional[str] = None  # 模型类型 (chat, vision, embedding, rerank)
    chat_model_type: Optional[str] = None  # 聊天模型子类型 (text-model, multi-model)

class RegenerateRequest(BaseModel):
    """编辑重试请求"""
    session_id: str
    message_id: str  # 要编辑的用户消息ID
    new_query: str   # 新的问题文本
    new_image_urls: Optional[list[str]] = None  # 新的图片URL列表
    selected_model: Optional[str] = None  # 使用的模型
    use_web: bool = False  # 是否使用联网搜索