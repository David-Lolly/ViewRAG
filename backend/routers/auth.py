from fastapi import APIRouter
from schemas.request import LoginRequest, RegisterRequest
from services import AuthService

router = APIRouter()

@router.post("/login")
async def login(req: LoginRequest):
    """用户登录"""
    return AuthService.login_user(req.user_id, req.password)

@router.post("/register")
async def register(req: RegisterRequest):
    """用户注册"""
    return AuthService.register_user_service(req.user_id, req.password)
