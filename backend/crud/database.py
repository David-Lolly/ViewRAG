import logging
import os
import uuid
import yaml
from pathlib import Path
from typing import List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker

from models import Base, ChatSession, Message, User


logger = logging.getLogger(__name__)


def load_database_config():
    """从config.yaml加载数据库配置"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        db_config = config.get('Database_Config', {})
        
        # 优先使用环境变量，否则使用config.yaml
        user = os.getenv('POSTGRES_USER', db_config.get('POSTGRES_USER', 'xll'))
        password = os.getenv('POSTGRES_PASSWORD', db_config.get('POSTGRES_PASSWORD', 'xll3419552864'))
        host = os.getenv('POSTGRES_HOST', db_config.get('POSTGRES_HOST', 'localhost'))
        port = os.getenv('POSTGRES_PORT', db_config.get('POSTGRES_PORT', 5431))
        database = os.getenv('POSTGRES_DB', db_config.get('POSTGRES_DB', 'tinyaisearch_dev'))
        
        # 构建DATABASE_URL
        database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
        
        logger.info(f"数据库配置加载成功: {host}:{port}/{database}")
        return database_url
        
    except FileNotFoundError:
        logger.error(f"配置文件未找到: {config_path}")
        raise RuntimeError("config.yaml 文件未找到")
    except Exception as e:
        logger.error(f"加载数据库配置失败: {e}")
        raise RuntimeError(f"加载数据库配置失败: {e}")


# 获取数据库URL
DATABASE_URL = os.getenv("DATABASE_URL") or load_database_config()

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True))


def create_tables() -> None:
    """
    创建数据库表。
    """
    Base.metadata.create_all(bind=engine)


def register_user(user_id: str, password: str) -> bool:
    """
    注册新用户。
    """
    with SessionLocal() as session:
        if session.get(User, user_id) is not None:
            return False

        user = User(user_id=user_id, password=password)
        session.add(user)
        try:
            session.commit()
            return True
        except SQLAlchemyError as exc:
            logger.error("注册用户失败: %s", exc)
            session.rollback()
            return False


def verify_user(user_id: str, password: str) -> bool:
    """
    验证用户凭据。
    """
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            logger.warning("用户不存在: %s", user_id)
            return False
        is_valid = user.password == password
        if not is_valid:
            logger.warning("用户密码错误: %s", user_id)
        return is_valid


def user_exists(user_id: str) -> bool:
    """
    检查用户是否存在。
    """
    with SessionLocal() as session:
        return session.get(User, user_id) is not None


def create_session(user_id: Optional[str] = None, title: str = "New Chat") -> Optional[str]:
    """
    创建新的会话记录。
    """
    session_id = str(uuid.uuid4())
    chat_session = ChatSession(session_id=session_id, user_id=user_id, title=title)

    with SessionLocal() as session:
        session.add(chat_session)
        try:
            session.commit()
            return session_id
        except SQLAlchemyError as exc:
            logger.error("创建会话失败: %s", exc)
            session.rollback()
            return None


def add_message(session_id: str, role: str, content: str, image_url: Optional[str] = None) -> Optional[str]:
    """
    向会话添加消息。
    
    Args:
        session_id: 会话ID
        role: 角色 (user/assistant)
        content: 消息内容
        image_url: 可选，图片的MinIO URL
    
    Returns:
        消息ID或None
    """
    message_id = str(uuid.uuid4())
    message = Message(
        message_id=message_id, 
        session_id=session_id, 
        role=role, 
        content=content,
        image_url=image_url
    )

    with SessionLocal() as session:
        session.add(message)
        try:
            session.commit()
            logger.info(f"消息已添加: role={role}, image_url={'有' if image_url else '无'}")
            return message_id
        except SQLAlchemyError as exc:
            logger.error("添加消息失败: %s", exc)
            session.rollback()
            return None


def get_messages(session_id: str) -> List[dict]:
    """
    获取指定会话的消息列表（包含message_id和image_url）。
    """
    with SessionLocal() as session:
        stmt = (
            select(Message.message_id, Message.role, Message.content, Message.image_url, Message.timestamp)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp.asc())
        )
        results = session.execute(stmt).all()
        return [
            {
                "message_id": message_id,
                "role": role,
                "content": content,
                "image_url": image_url,
                "timestamp": timestamp.isoformat() if timestamp else None,
            }
            for message_id, role, content, image_url, timestamp in results
        ]


def get_sessions(user_id: Optional[str] = None) -> List[dict]:
    """
    获取会话列表。
    """
    with SessionLocal() as session:
        stmt = select(ChatSession).order_by(ChatSession.created_at.desc())
        if user_id:
            stmt = stmt.where(ChatSession.user_id == user_id)
        results = session.execute(stmt).scalars().all()
        return [
            {
                "session_id": chat.session_id,
                "title": chat.title,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
            }
            for chat in results
        ]


def get_message_by_id(message_id: str) -> Optional[dict]:
    """
    根据message_id获取消息详情。
    
    Returns:
        消息字典或None
    """
    with SessionLocal() as session:
        message = session.get(Message, message_id)
        if not message:
            return None
        return {
            "message_id": message.message_id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "image_url": message.image_url,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
        }


def delete_messages_after(session_id: str, message_id: str) -> List[dict]:
    """
    删除指定消息之后的所有消息（基于timestamp）。
    
    Args:
        session_id: 会话ID
        message_id: 目标消息ID
    
    Returns:
        被删除的消息列表（包含image_url信息，用于清理文件）
    """
    with SessionLocal() as session:
        try:
            # 获取目标消息
            target_msg = session.get(Message, message_id)
            if not target_msg or target_msg.session_id != session_id:
                logger.warning(f"消息不存在或不属于该会话: {message_id}")
                return []
            
            target_timestamp = target_msg.timestamp
            
            # 查询该时间戳之后的所有消息
            stmt = (
                select(Message)
                .where(Message.session_id == session_id)
                .where(Message.timestamp > target_timestamp)
                .order_by(Message.timestamp.asc())
            )
            messages_to_delete = session.execute(stmt).scalars().all()
            
            # 收集消息信息（用于返回和文件清理）
            deleted_messages = [
                {
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "image_url": msg.image_url
                }
                for msg in messages_to_delete
            ]
            
            # 删除消息
            for msg in messages_to_delete:
                session.delete(msg)
            
            session.commit()
            logger.info(f"已删除会话 {session_id} 中消息 {message_id} 之后的 {len(deleted_messages)} 条消息")
            return deleted_messages
            
        except SQLAlchemyError as exc:
            logger.error(f"删除消息失败: {exc}")
            session.rollback()
            return []


def update_user_message(message_id: str, new_content: str, new_image_urls: Optional[str] = None) -> bool:
    """
    更新用户消息的内容和图片。
    
    Args:
        message_id: 消息ID
        new_content: 新的消息内容
        new_image_urls: 新的图片URL（JSON字符串）
    
    Returns:
        是否更新成功
    """
    with SessionLocal() as session:
        try:
            message = session.get(Message, message_id)
            if not message:
                logger.warning(f"消息不存在: {message_id}")
                return False
            
            if message.role != 'user':
                logger.warning(f"只能更新用户消息: {message_id}")
                return False
            
            # 保存旧的image_url用于返回（调用者可能需要清理旧文件）
            old_image_url = message.image_url
            
            # 更新消息
            message.content = new_content
            message.image_url = new_image_urls
            
            session.commit()
            logger.info(f"消息已更新: {message_id}")
            return True
            
        except SQLAlchemyError as exc:
            logger.error(f"更新消息失败: {exc}")
            session.rollback()
            return False


def delete_message(message_id: str) -> Optional[dict]:
    """
    删除单条消息。
    
    Args:
        message_id: 消息ID
    
    Returns:
        被删除的消息信息（包含image_url，用于清理文件），失败返回None
    """
    with SessionLocal() as session:
        try:
            message = session.get(Message, message_id)
            if not message:
                logger.warning(f"消息不存在: {message_id}")
                return None
            
            # 收集消息信息
            deleted_message = {
                "message_id": message.message_id,
                "session_id": message.session_id,
                "role": message.role,
                "content": message.content,
                "image_url": message.image_url
            }
            
            session.delete(message)
            session.commit()
            logger.info(f"消息已删除: {message_id}")
            return deleted_message
            
        except SQLAlchemyError as exc:
            logger.error(f"删除消息失败: {exc}")
            session.rollback()
            return None


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully.")
