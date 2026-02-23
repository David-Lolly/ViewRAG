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
    selected_model: Optional[str] = None  # 新增：用户选择的对话模型名称
    image_url: Optional[str] = None  # 新增：上传的图片URL（base64或URL）
    kb_id: Optional[str] = None  # 知识库问答时传入的知识库 ID
    has_docs: bool = False  # 前端标记：当前会话是否有已完成的文档，用于跳过不必要的数据库查询

class SessionRequest(BaseModel):
    user_id: str
    title: Optional[str] = None

class TestRequest(BaseModel):
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_token: Optional[str] = None # OCR token
    api_url: Optional[str] = None   # OCR url
    cse_id: Optional[str] = None
    model_type: Optional[str] = None  # 模型类型 (chat, vision, embedding, rerank, ocr)
    chat_model_type: Optional[str] = None  # 聊天模型子类型 (text-model, multi-model)

class RegenerateRequest(BaseModel):
    """编辑重试请求"""
    session_id: str
    message_id: str  # 要编辑的用户消息ID
    new_query: str   # 新的问题文本
    new_image_urls: Optional[list[str]] = None  # 新的图片URL列表
    selected_model: Optional[str] = None  # 使用的模型
    has_docs: bool = False  # 前端标记：当前会话是否有已完成的文档