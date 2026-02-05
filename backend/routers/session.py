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
