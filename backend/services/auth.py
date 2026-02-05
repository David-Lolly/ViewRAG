import logging
from fastapi import HTTPException
import crud.database as db

logger = logging.getLogger(__name__)

class AuthService:
    """认证服务类"""
    
    @staticmethod
    def login_user(user_id: str, password: str) -> dict:
        """用户登录验证"""
        if not user_id or not password:
            logger.error(f"登录尝试失败: 缺少用户ID或密码")
            raise HTTPException(status_code=400, detail="用户ID和密码为必填项")

        logger.info(f"用户登录尝试: {user_id}")

        is_valid = db.verify_user(user_id, password)

        if not is_valid:
            logger.warning(f"用户登录失败: {user_id}")
            raise HTTPException(status_code=401, detail="无效的凭据或用户不存在")

        logger.info(f"用户登录成功: {user_id}")
        return {"message": "登录成功", "user_id": user_id}

    @staticmethod
    def register_user_service(user_id: str, password: str) -> dict:
        """用户注册"""
        if not user_id or not password:
            logger.error("注册尝试失败: 缺少用户ID或密码")
            raise HTTPException(status_code=400, detail="用户ID和密码为必填项")

        logger.info(f"用户注册尝试: {user_id}")

        if db.user_exists(user_id):
            logger.warning(f"注册失败: 用户已存在: {user_id}")
            raise HTTPException(status_code=409, detail="用户已存在")

        success = db.register_user(user_id, password)
        if not success:
            logger.error(f"注册用户失败: {user_id}")
            raise HTTPException(status_code=500, detail="注册用户失败")

        logger.info(f"用户注册成功: {user_id}")
        return {"message": "注册成功", "user_id": user_id}
