"""文档相关的数据库CRUD操作"""

import logging
import uuid
import json
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, update, and_, or_, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.models import (
    Document, 
    DocumentType, 
    DocumentStatus
)

logger = logging.getLogger(__name__)


class DocumentCRUD:
    """文档CRUD操作类"""
    
    @staticmethod
    def check_duplicate_by_hash(
        session: Session,
        file_hash: str,
        session_id: Optional[str] = None,
        kb_id: Optional[str] = None
    ) -> Optional[Document]:
        """
        根据文件哈希检查是否存在重复文档
        
        Args:
            session: 数据库会话
            file_hash: 文件SHA256哈希
            session_id: 会话ID（在该会话内查重）
            kb_id: 知识库ID（在该知识库内查重）
            
        Returns:
            重复的Document对象或None
        """
        try:
            stmt = select(Document).where(Document.file_hash == file_hash)
            if session_id:
                stmt = stmt.where(Document.session_id == session_id)
            if kb_id:
                stmt = stmt.where(Document.kb_id == kb_id)
            return session.execute(stmt).scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"检查文件重复失败: {e}")
            return None

    @staticmethod
    def create_document(
        session: Session,
        file_name: str,
        file_path: str,
        document_type: DocumentType,
        session_id: Optional[str] = None,
        kb_id: Optional[str] = None,
        file_hash: Optional[str] = None
    ) -> Optional[Document]:
        """
        创建文档记录
        
        Args:
            session: 数据库会话
            file_name: 文件名
            file_path: MinIO存储路径
            document_type: 文档类型
            session_id: 会话ID（会话轨道）
            kb_id: 知识库ID（知识库轨道）
            file_hash: 文件SHA256哈希（用于去重）
            
        Returns:
            Document对象或None
        """
        try:
            doc_id = str(uuid.uuid4())
            document = Document(
                id=doc_id,
                session_id=session_id,
                kb_id=kb_id,
                file_name=file_name,
                file_path=file_path,
                document_type=document_type,
                file_hash=file_hash,
                status=DocumentStatus.QUEUED
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            logger.info(f"文档创建成功: {doc_id}, 文件名: {file_name}")
            return document
        except SQLAlchemyError as e:
            logger.error(f"创建文档失败: {e}")
            session.rollback()
            return None
    
    @staticmethod
    def get_document_by_id(session: Session, doc_id: str) -> Optional[Document]:
        """
        根据ID获取文档
        
        Args:
            session: 数据库会话
            doc_id: 文档ID
            
        Returns:
            Document对象或None
        """
        try:
            return session.get(Document, doc_id)
        except SQLAlchemyError as e:
            logger.error(f"获取文档失败: {e}")
            return None
    
    @staticmethod
    def get_documents_by_ids(session: Session, doc_ids: List[str]) -> Dict[str, Document]:
        """
        批量查询文档（用于去重后的文档信息获取）
        
        Args:
            session: 数据库会话
            doc_ids: 文档ID列表
            
        Returns:
            {doc_id: Document} 字典
        """
        try:
            if not doc_ids:
                return {}
            stmt = select(Document).where(Document.id.in_(doc_ids))
            result = session.execute(stmt).scalars().all()
            return {doc.id: doc for doc in result}
        except SQLAlchemyError as e:
            logger.error(f"批量获取文档失败: {e}")
            return {}
    
    @staticmethod
    def get_documents_by_session_id(session: Session, session_id: str) -> List[Document]:
        """
        获取会话下的所有文档
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            
        Returns:
            文档列表
        """
        try:
            stmt = select(Document).where(
                Document.session_id == session_id
            ).order_by(Document.created_at.desc())
            result = session.execute(stmt).scalars().all()
            return list(result)
        except SQLAlchemyError as e:
            logger.error(f"获取会话文档列表失败: {e}")
            return []
    
    @staticmethod
    def get_documents_by_kb_id(session: Session, kb_id: str) -> List[Document]:
        """
        获取知识库下的所有文档
        
        Args:
            session: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            文档列表
        """
        try:
            stmt = select(Document).where(
                Document.kb_id == kb_id
            ).order_by(Document.created_at.desc())
            result = session.execute(stmt).scalars().all()
            return list(result)
        except SQLAlchemyError as e:
            logger.error(f"获取知识库文档列表失败: {e}")
            return []
    
    @staticmethod
    def update_document_status(
        session: Session,
        doc_id: str,
        status: DocumentStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新文档状态
        
        Args:
            session: 数据库会话
            doc_id: 文档ID
            status: 新状态
            error_message: 错误信息（可选）
            
        Returns:
            是否更新成功
        """
        try:
            stmt = (
                update(Document)
                .where(Document.id == doc_id)
                .values(status=status, error_message=error_message)
            )
            result = session.execute(stmt)
            session.commit()
            success = result.rowcount > 0
            if success:
                logger.info(f"文档状态已更新: {doc_id} -> {status.value}")
            return success
        except SQLAlchemyError as e:
            logger.error(f"更新文档状态失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def update_document_status_conditionally(
        session: Session,
        doc_id: str,
        new_status: DocumentStatus,
        expected_status: DocumentStatus
    ) -> bool:
        """
        条件性更新文档状态（用于Worker，避免竞态条件）
        
        Args:
            session: 数据库会话
            doc_id: 文档ID
            new_status: 新状态
            expected_status: 期望的当前状态
            
        Returns:
            是否更新成功
        """
        try:
            stmt = (
                update(Document)
                .where(and_(
                    Document.id == doc_id,
                    Document.status == expected_status
                ))
                .values(status=new_status)
            )
            result = session.execute(stmt)
            session.commit()
            success = result.rowcount > 0
            if success:
                logger.info(f"文档状态条件更新成功: {doc_id} {expected_status.value} -> {new_status.value}")
            else:
                logger.warning(f"文档状态条件更新失败: {doc_id}，当前状态可能不是 {expected_status.value}")
            return success
        except SQLAlchemyError as e:
            logger.error(f"条件更新文档状态失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def is_document_task_valid(session: Session, doc_id: str) -> bool:
        """
        检查文档任务是否仍然有效（关键：协作式取消检查点）
        
        Args:
            session: 数据库会话
            doc_id: 文档ID
            
        Returns:
            文档是否存在（True表示任务仍需继续）
        """
        try:
            stmt = select(Document.id).where(Document.id == doc_id)
            result = session.execute(stmt).scalar_one_or_none()
            is_valid = result is not None
            if not is_valid:
                logger.info(f"文档任务已取消: {doc_id}")
            return is_valid
        except SQLAlchemyError as e:
            logger.error(f"检查文档任务有效性失败: {e}")
            return False
    
    @staticmethod
    def delete_document(session: Session, doc_id: str, owner_id: Optional[str] = None) -> bool:
        """
        删除文档（用于取消操作和手动删除）
        
        Args:
            session: 数据库会话
            doc_id: 文档ID
            owner_id: 所有者ID（session_id或kb_id），用于验证权限
            
        Returns:
            是否删除成功
        """
        try:
            stmt = delete(Document).where(Document.id == doc_id)
            if owner_id:
                stmt = stmt.where(or_(
                    Document.session_id == owner_id,
                    Document.kb_id == owner_id
                ))
            result = session.execute(stmt)
            session.commit()
            success = result.rowcount > 0
            if success:
                logger.info(f"文档已删除: {doc_id}")
            else:
                logger.warning(f"文档删除失败，可能不存在或权限不足: {doc_id}")
            return success
        except SQLAlchemyError as e:
            logger.error(f"删除文档失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def get_document_owners(session: Session, doc_ids: List[str]) -> Dict[str, str]:
        """
        获取文档的归属类型（用于RAG引擎路由）
        
        Args:
            session: 数据库会话
            doc_ids: 文档ID列表
            
        Returns:
            字典 {doc_id: 'session' | 'kb'}
        """
        try:
            stmt = select(Document.id, Document.session_id, Document.kb_id).where(
                Document.id.in_(doc_ids)
            )
            results = session.execute(stmt).all()
            
            owner_map = {}
            for doc_id, session_id, kb_id in results:
                owner_map[doc_id] = 'session' if session_id else 'kb'
            
            return owner_map
        except SQLAlchemyError as e:
            logger.error(f"获取文档归属失败: {e}")
            return {}
    
    @staticmethod
    def update_document_summary(session: Session, doc_id: str, summary: str) -> bool:
        """更新文档摘要"""
        try:
            stmt = (
                update(Document)
                .where(Document.id == doc_id)
                .values(summary=summary)
            )
            result = session.execute(stmt)
            session.commit()
            success = result.rowcount > 0
            if success:
                logger.info(f"文档摘要已更新: {doc_id}, 长度={len(summary)}")
            return success
        except SQLAlchemyError as e:
            logger.error(f"更新文档摘要失败: {e}")
            session.rollback()
            return False

    @staticmethod
    def bind_documents_to_message(
        session: Session,
        doc_ids: List[str],
        message_id: str,
        session_id: str
    ) -> bool:
        """
        将文档绑定到消息（用户发送消息时调用）
        
        Args:
            session: 数据库会话
            doc_ids: 文档ID列表
            message_id: 消息ID
            session_id: 会话ID（用于验证权限）
            
        Returns:
            是否绑定成功
        """
        try:
            if not doc_ids:
                return True
            
            stmt = (
                update(Document)
                .where(and_(
                    Document.id.in_(doc_ids),
                    Document.session_id == session_id,
                    Document.message_id.is_(None),  # 只绑定未绑定的文档
                    Document.status == DocumentStatus.COMPLETED  # 只绑定已完成的文档
                ))
                .values(message_id=message_id)
            )
            result = session.execute(stmt)
            session.commit()
            
            updated_count = result.rowcount
            logger.info(f"文档绑定到消息成功: message_id={message_id}, 绑定数量={updated_count}/{len(doc_ids)}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"文档绑定到消息失败: {e}")
            session.rollback()
            return False

    @staticmethod
    def get_documents_by_message_id(session: Session, message_id: str) -> List[Document]:
        """
        获取消息关联的文档列表
        
        Args:
            session: 数据库会话
            message_id: 消息ID
            
        Returns:
            文档列表
        """
        try:
            stmt = select(Document).where(
                Document.message_id == message_id
            ).order_by(Document.created_at)
            result = session.execute(stmt).scalars().all()
            return list(result)
        except SQLAlchemyError as e:
            logger.error(f"获取消息关联文档失败: {e}")
            return []

    @staticmethod
    def get_unbound_completed_documents(session: Session, session_id: str) -> List[Document]:
        """
        获取会话中未绑定消息的已完成文档（用于前端显示待发送的文档）
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            
        Returns:
            文档列表
        """
        try:
            stmt = select(Document).where(and_(
                Document.session_id == session_id,
                Document.message_id.is_(None),
                Document.status == DocumentStatus.COMPLETED
            )).order_by(Document.created_at)
            result = session.execute(stmt).scalars().all()
            return list(result)
        except SQLAlchemyError as e:
            logger.error(f"获取未绑定文档失败: {e}")
            return []


class ChunkCRUD:
    """Chunk CRUD 操作类 - 简化后的统一内容块操作"""
    
    @staticmethod
    def save_chunks(
        session: Session,
        doc_id: str,
        kb_id: Optional[str],
        chunks_data: List[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> bool:
        """
        批量保存 Chunk 数据
        
        Args:
            session: 数据库会话
            doc_id: 文档 ID
            kb_id: 知识库 ID（可选，用于加速检索过滤）
            chunks_data: Chunk 数据列表，每个元素包含：
                {
                    'chunk_type': str,        # 'TEXT' | 'IMAGE' | 'TABLE'
                    'content': str,           # 原始内容
                    'retrieval_text': str,    # 检索用文本
                    'content_vector': List[float],  # 向量
                    'metadata': Optional[dict]      # 元数据
                }
            session_id: 会话 ID（可选，用于加速会话检索过滤）
                
        Returns:
            是否保存成功
        """
        from models.models import Chunk, ChunkType
        
        try:
            chunks_to_insert = []
            
            for chunk_data in chunks_data:
                chunk_id = str(uuid.uuid4())
                chunk_type_str = chunk_data['chunk_type']
                chunk_type = ChunkType(chunk_type_str)
                
                chunk = Chunk(
                    id=chunk_id,
                    doc_id=doc_id,
                    kb_id=kb_id,
                    session_id=session_id,
                    chunk_type=chunk_type,
                    content=chunk_data['content'],
                    retrieval_text=chunk_data['retrieval_text'],
                    content_vector=chunk_data['content_vector'],
                    chunk_metadata=json.dumps(chunk_data.get('metadata')) if chunk_data.get('metadata') else None
                )
                chunks_to_insert.append(chunk)
            
            session.add_all(chunks_to_insert)
            session.commit()
            
            # 验证数据确实写入了
            from sqlalchemy import text
            count_result = session.execute(
                text("SELECT COUNT(*) FROM chunks WHERE doc_id = :doc_id"),
                {"doc_id": doc_id}
            ).scalar()
            logger.info(f"Chunk 批量保存成功: doc_id={doc_id}, 插入数量={len(chunks_to_insert)}, 验证查询数量={count_result}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Chunk 批量保存失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def get_chunks_by_doc_id(
        session: Session,
        doc_id: str
    ) -> List[Dict[str, Any]]:
        """
        根据文档 ID 获取所有 Chunk
        
        Args:
            session: 数据库会话
            doc_id: 文档 ID
            
        Returns:
            Chunk 数据列表
        """
        from models.models import Chunk
        
        try:
            stmt = select(Chunk).where(Chunk.doc_id == doc_id).order_by(Chunk.created_at)
            results = session.execute(stmt).scalars().all()
            
            output = []
            for chunk in results:
                output.append({
                    'id': chunk.id,
                    'doc_id': chunk.doc_id,
                    'kb_id': chunk.kb_id,
                    'chunk_type': chunk.chunk_type.value,
                    'content': chunk.content,
                    'retrieval_text': chunk.retrieval_text,
                    'metadata': json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {}
                })
            
            return output
            
        except SQLAlchemyError as e:
            logger.error(f"获取 Chunk 失败: {e}")
            return []
    
    @staticmethod
    def delete_chunks_by_doc_id(session: Session, doc_id: str) -> bool:
        """
        根据文档 ID 删除所有 Chunk
        
        Args:
            session: 数据库会话
            doc_id: 文档 ID
            
        Returns:
            是否删除成功
        """
        from models.models import Chunk
        
        try:
            stmt = delete(Chunk).where(Chunk.doc_id == doc_id)
            result = session.execute(stmt)
            session.commit()
            
            deleted_count = result.rowcount
            logger.info(f"Chunk 删除成功: doc_id={doc_id}, 删除数量={deleted_count}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"删除 Chunk 失败: {e}")
            session.rollback()
            return False
    
    @staticmethod
    def search_chunks(
        session: Session,
        query_vector: List[float],
        kb_id: Optional[str] = None,
        session_id: Optional[str] = None,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        向量检索 Chunk
        
        Args:
            session: 数据库会话
            query_vector: 查询向量
            kb_id: 知识库 ID（可选）
            session_id: 会话 ID（可选）
            doc_ids: 文档 ID 列表（可选）
            top_k: 返回数量
            
        Returns:
            检索结果列表，按相似度降序排列，包含:
            {
                'chunk_id': str,
                'chunk_type': str,
                'content': str,
                'retrieval_text': str,
                'metadata': dict,
                'score': float,
                'doc_id': str,
                'kb_id': str | None,
                'session_id': str | None,
                'file_name': str,
            }
        """
        from models.models import Chunk
        
        try:
            # 安全兜底：未提供任何过滤条件时返回空结果
            if not kb_id and not session_id and not doc_ids:
                logger.warning("search_chunks 未提供任何过滤条件，返回空结果")
                return []
            
            # 构建查询，JOIN documents 表获取 file_name
            stmt = select(
                Chunk,
                Document.file_name,
                Chunk.content_vector.l2_distance(query_vector).label('distance')
            ).join(Document, Chunk.doc_id == Document.id)
            
            # 添加过滤条件
            conditions = []
            if kb_id:
                conditions.append(Chunk.kb_id == kb_id)
            if session_id:
                conditions.append(Chunk.session_id == session_id)
            if doc_ids:
                conditions.append(Chunk.doc_id.in_(doc_ids))
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            # 按距离排序并限制数量
            stmt = stmt.order_by(text('distance')).limit(top_k)
            
            results = session.execute(stmt).all()
            
            # 构建输出结果
            output = []
            for chunk, file_name, distance in results:
                # 将 L2 距离转换为相似度分数（距离越小，相似度越高）
                similarity = 1.0 / (1.0 + float(distance))
                
                content = chunk.content
                
                output.append({
                    'chunk_id': chunk.id,
                    'chunk_type': chunk.chunk_type.value,
                    'content': content,
                    'retrieval_text': chunk.retrieval_text,
                    'metadata': json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {},
                    'score': similarity,
                    'doc_id': chunk.doc_id,
                    'kb_id': chunk.kb_id,
                    'session_id': chunk.session_id,
                    'file_name': file_name,
                })
            
            logger.info(f"Chunk 检索完成: kb_id={kb_id}, session_id={session_id}, doc_ids={doc_ids}, 结果数={len(output)}")
            return output
            
        except SQLAlchemyError as e:
            logger.error(f"Chunk 检索失败: {e}")
            return []
    
    @staticmethod
    def _to_image_url(content: str) -> str:
        """
        将 MinIO 相对路径转换为完整可访问 URL
        
        如果 content 已经是完整 URL（以 http:// 或 https:// 开头），则直接返回。
        否则拼接 MinIO 文档桶的基础 URL。
        
        Args:
            content: 图片内容路径（可能是相对路径或完整 URL）
            
        Returns:
            完整的可访问 URL
        """
        if not content:
            return content
        if content.startswith('http://') or content.startswith('https://'):
            return content
        
        # 使用 MinIOStorage 单例获取完整 URL
        try:
            from services.storage import minio_storage
            if minio_storage:
                return minio_storage.get_file_url(minio_storage.doc_bucket, content)
        except Exception:
            pass
        
        # 兜底：拼接默认路径
        return f"http://127.0.0.1:9000/viewrag-documents/{content}"
