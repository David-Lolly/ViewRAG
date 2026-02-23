"""知识库相关的数据库CRUD操作"""

import logging
import uuid
from typing import List, Optional
from sqlalchemy import select, delete, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.models import KnowledgeBase, Document

logger = logging.getLogger(__name__)


class KnowledgeBaseCRUD:
    """知识库CRUD操作类"""
    
    @staticmethod
    def create_kb(
        session: Session,
        user_id: str,
        name: str,
        description: Optional[str] = None
    ) -> Optional[KnowledgeBase]:
        """
        创建知识库
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            name: 知识库名称
            description: 知识库描述
            
        Returns:
            KnowledgeBase对象或None
        """
        try:
            kb_id = str(uuid.uuid4())
            kb = KnowledgeBase(
                id=kb_id,
                user_id=user_id,
                name=name,
                description=description
            )
            session.add(kb)
            session.commit()
            session.refresh(kb)
            logger.info(f"知识库创建成功: {kb_id}, 名称: {name}")
            return kb
        except SQLAlchemyError as e:
            logger.error(f"创建知识库失败: {e}")
            session.rollback()
            return None
    
    @staticmethod
    def get_kb_by_id(session: Session, kb_id: str) -> Optional[KnowledgeBase]:
        """
        根据ID获取知识库
        
        Args:
            session: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            KnowledgeBase对象或None
        """
        try:
            return session.get(KnowledgeBase, kb_id)
        except SQLAlchemyError as e:
            logger.error(f"获取知识库失败: {e}")
            return None
    
    @staticmethod
    def get_user_kbs(session: Session, user_id: str) -> List[KnowledgeBase]:
        """
        获取用户的所有知识库
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            
        Returns:
            知识库列表
        """
        try:
            stmt = select(KnowledgeBase).where(
                KnowledgeBase.user_id == user_id
            ).order_by(KnowledgeBase.created_at.desc())
            result = session.execute(stmt).scalars().all()
            return list(result)
        except SQLAlchemyError as e:
            logger.error(f"获取用户知识库列表失败: {e}")
            return []
    
    @staticmethod
    def get_user_kbs_with_count(session: Session, user_id: str) -> List[dict]:
        """
        获取用户的所有知识库（包含文档数量）
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            
        Returns:
            知识库列表（包含document_count字段）
        """
        try:
            stmt = (
                select(
                    KnowledgeBase,
                    func.count(Document.id).label('document_count')
                )
                .outerjoin(Document, KnowledgeBase.id == Document.kb_id)
                .where(KnowledgeBase.user_id == user_id)
                .group_by(KnowledgeBase.id)
                .order_by(KnowledgeBase.created_at.desc())
            )
            results = session.execute(stmt).all()
            
            output = []
            for kb, doc_count in results:
                kb_dict = {
                    'id': kb.id,
                    'user_id': kb.user_id,
                    'name': kb.name,
                    'description': kb.description,
                    'summary': kb.summary,
                    'created_at': kb.created_at,
                    'document_count': doc_count
                }
                output.append(kb_dict)
            
            return output
        except SQLAlchemyError as e:
            logger.error(f"获取用户知识库列表（含计数）失败: {e}")
            return []
    
    @staticmethod
    def update_kb(
        session: Session,
        kb_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        summary: Optional[str] = None
    ) -> bool:
        """
        更新知识库信息
        
        Args:
            session: 数据库会话
            kb_id: 知识库ID
            name: 新名称
            description: 新描述
            summary: 新摘要（由LLM生成）
            
        Returns:
            是否更新成功
        """
        try:
            values = {}
            if name is not None:
                values['name'] = name
            if description is not None:
                values['description'] = description
            if summary is not None:
                values['summary'] = summary
            
            if not values:
                return True
            
            stmt = update(KnowledgeBase).where(
                KnowledgeBase.id == kb_id
            ).values(**values)
            
            result = session.execute(stmt)
            session.commit()
            success = result.rowcount > 0
            if success:
                logger.info(f"知识库更新成功: {kb_id}")
            return success
        except SQLAlchemyError as e:
            logger.error(f"更新知识库失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def delete_kb(session: Session, kb_id: str, user_id: str) -> bool:
        """
        删除知识库（权限验证）
        
        Args:
            session: 数据库会话
            kb_id: 知识库ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            是否删除成功
        """
        try:
            stmt = delete(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.user_id == user_id
            )
            result = session.execute(stmt)
            session.commit()
            success = result.rowcount > 0
            if success:
                logger.info(f"知识库已删除: {kb_id}")
            else:
                logger.warning(f"知识库删除失败，可能不存在或权限不足: {kb_id}")
            return success
        except SQLAlchemyError as e:
            logger.error(f"删除知识库失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def delete_kb_by_id(session: Session, kb_id: str) -> bool:
        """
        按 ID 删除知识库（不校验 user_id）
        
        Args:
            session: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            是否删除成功
        """
        try:
            stmt = delete(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            result = session.execute(stmt)
            session.commit()
            success = result.rowcount > 0
            if success:
                logger.info(f"知识库已删除: {kb_id}")
            else:
                logger.warning(f"知识库删除失败，可能不存在: {kb_id}")
            return success
        except SQLAlchemyError as e:
            logger.error(f"删除知识库失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def kb_exists(session: Session, kb_id: str, user_id: str) -> bool:
        """
        检查知识库是否存在且属于该用户
        
        Args:
            session: 数据库会话
            kb_id: 知识库ID
            user_id: 用户ID
            
        Returns:
            是否存在
        """
        try:
            stmt = select(KnowledgeBase.id).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.user_id == user_id
            )
            result = session.execute(stmt).scalar_one_or_none()
            return result is not None
        except SQLAlchemyError as e:
            logger.error(f"检查知识库存在性失败: {e}")
            return False

