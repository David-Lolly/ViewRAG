from fastapi import APIRouter
from schemas.request import SessionRequest
from services import SessionService

router = APIRouter()

@router.get("/sessions")
async def get_all_sessions(user_id: str):
    """获取所有会话"""
    return SessionService.get_user_sessions(user_id)

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """获取会话消息"""
    return SessionService.get_session_messages(session_id)

@router.post("/session", status_code=201)
async def create_new_session_endpoint(req: SessionRequest):
    """创建新会话"""
    return SessionService.create_new_session(req.user_id, req.title)

@router.post("/sessions/{session_id}/generate_title")
async def generate_session_title(session_id: str):
    """
    根据会话的第一条用户消息，使用 LLM 生成会话标题。
    异步执行，立即返回。前端可轮询获取更新后的标题。
    """
    messages = SessionService.get_session_messages(session_id)
    # 找到第一条用户消息
    user_message = None
    for msg in messages:
        if msg.get('role') == 'user':
            user_message = msg.get('content', '')
            break
    
    if not user_message:
        return {"status": "skipped", "reason": "no user message found"}
    
    # 后台异步生成标题
    SessionService.generate_session_title_async(session_id, user_message)
    return {"status": "generating"}

@router.get("/sessions/{session_id}/title")
async def get_session_title(session_id: str):
    """获取会话标题（用于前端轮询更新）"""
    from crud.database import SessionLocal
    from models.models import ChatSession
    
    with SessionLocal() as db_session:
        chat_session = db_session.get(ChatSession, session_id)
        if chat_session:
            return {"title": chat_session.title}
    return {"title": None}
