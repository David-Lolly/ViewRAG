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
    ContentUnit, 
    RetrievalIndex,
    DocumentType, 
    DocumentStatus,
    UnitType
)

logger = logging.getLogger(__name__)


class DocumentCRUD:
    """文档CRUD操作类"""
    
    @staticmethod
    def create_document(
        session: Session,
        file_name: str,
        file_path: str,
        document_type: DocumentType,
        session_id: Optional[str] = None,
        kb_id: Optional[str] = None
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
    def save_pipeline_data(
        session: Session,
        doc_id: str,
        units_data: List[Dict[str, Any]],
        summary: Optional[str] = None,
        summary_vector: Optional[List[float]] = None
    ) -> bool:
        """
        批量保存处理流水线产生的数据（核心事务性操作）
        
        Args:
            session: 数据库会话
            doc_id: 文档ID
            units_data: 内容单元数据列表，每个元素包含：
                {
                    'unit_type': UnitType,
                    'content': str,
                    'summary': Optional[str],
                    'metadata': Optional[dict],
                    'parent_id': Optional[str],
                    'retrieval_text': str,
                    'text_vector': List[float]
                }
            summary: 文档级摘要（KB轨道）
            summary_vector: 文档摘要向量（KB轨道）
            
        Returns:
            是否保存成功
        """
        try:
            # 1. 获取文档信息
            document = session.get(Document, doc_id)
            if not document:
                logger.error(f"文档不存在: {doc_id}")
                return False
            
            # 2. 更新文档摘要（如果提供）
            if summary:
                document.summary = summary
            if summary_vector:
                document.summary_vector = summary_vector
            
            # 3. 批量插入content_units和retrieval_index，确保L1/L2层级关系
            l1_id_map: Dict[str, str] = {}
            pending_children: List[Dict[str, Any]] = []
            inserted_count = 0

            def insert_unit(data: Dict[str, Any]) -> Optional[str]:
                nonlocal inserted_count
                unit_payload = dict(data)
                temp_l1_id = unit_payload.pop('temp_l1_id', None)
                unit_payload.pop('parent_l1_id_temp', None)
                parent_id = unit_payload.get('parent_id')

                unit_id = str(uuid.uuid4())
                content_unit = ContentUnit(
                    id=unit_id,
                    doc_id=doc_id,
                    parent_id=parent_id,
                    unit_type=unit_payload['unit_type'],
                    content=unit_payload.get('content'),
                    summary=unit_payload.get('summary'),
                    metadata=json.dumps(unit_payload.get('metadata')) if unit_payload.get('metadata') else None
                )
                session.add(content_unit)

                retrieval_index = RetrievalIndex(
                    unit_id=unit_id,
                    doc_id=doc_id,
                    session_id=document.session_id,
                    kb_id=document.kb_id,
                    parent_id=parent_id,
                    retrieval_text=unit_payload['retrieval_text'],
                    text_vector=unit_payload['text_vector']
                )
                session.add(retrieval_index)

                if temp_l1_id:
                    l1_id_map[temp_l1_id] = unit_id

                inserted_count += 1
                return unit_id

            for unit_data in units_data:
                if unit_data.get('parent_l1_id_temp'):
                    pending_children.append(unit_data)
                    continue
                insert_unit(unit_data)

            for unit_data in pending_children:
                parent_temp_id = unit_data.get('parent_l1_id_temp')
                parent_real_id = l1_id_map.get(parent_temp_id)
                if not parent_real_id:
                    logger.warning(f"跳过L2单元，未找到父节点: temp_id={parent_temp_id}")
                    continue
                child_payload = dict(unit_data)
                child_payload['parent_id'] = parent_real_id
                insert_unit(child_payload)
            
            session.commit()
            logger.info(f"流水线数据保存成功: {doc_id}, 单元数: {inserted_count}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"保存流水线数据失败: {e}")
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
    def search_session_flat(
        session: Session,
        session_id: str,
        doc_ids: List[str],
        query_vector: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        会话轨道：单阶段扁平化检索
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            doc_ids: 文档ID列表
            query_vector: 查询向量
            top_k: 返回数量
            
        Returns:
            检索结果列表
        """
        try:
            # 使用pgvector的向量相似度搜索
            # 注意：这里需要使用原生SQL或特定的向量搜索语法
            # 简化实现：先获取所有单元，再计算相似度
            # 使用pgvector的L2距离进行向量相似度搜索
            stmt = (
                select(
                    RetrievalIndex, 
                    ContentUnit,
                    RetrievalIndex.text_vector.l2_distance(query_vector).label('distance')
                )
                .join(ContentUnit, RetrievalIndex.unit_id == ContentUnit.id)
                .where(and_(
                    RetrievalIndex.session_id == session_id,
                    RetrievalIndex.doc_id.in_(doc_ids)
                ))
                .order_by(text('distance'))  # 按距离升序排序（距离越小越相似）
                .limit(top_k)
            )
            results = session.execute(stmt).all()
            
            # 构建输出结果
            output = []
            for retrieval, content, distance in results:
                output.append({
                    'unit_id': content.id,
                    'content': content.content,
                    'metadata': json.loads(content.metadata) if content.metadata else {},
                    'distance': float(distance)  # 添加相似度分数
                })
            
            logger.info(f"会话检索完成: session_id={session_id}, 结果数={len(output)}")
            return output
            
        except SQLAlchemyError as e:
            logger.error(f"会话检索失败: {e}")
            return []
    
    # KB轨道的多阶段检索方法
    # search_documents_by_summary, search_l1_chunks, search_l2_splits
    # 这些方法的实现类似，都需要使用pgvector的向量搜索
    # 由于篇幅限制，这里暂时省略，实际开发时需要完整实现



class ChunkCRUD:
    """Chunk CRUD 操作类 - 简化后的统一内容块操作"""
    
    @staticmethod
    def save_chunks(
        session: Session,
        doc_id: str,
        kb_id: Optional[str],
        chunks_data: List[Dict[str, Any]]
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
                    chunk_type=chunk_type,
                    content=chunk_data['content'],
                    retrieval_text=chunk_data['retrieval_text'],
                    content_vector=chunk_data['content_vector'],
                    chunk_metadata=json.dumps(chunk_data.get('metadata')) if chunk_data.get('metadata') else None
                )
                chunks_to_insert.append(chunk)
            
            session.add_all(chunks_to_insert)
            session.commit()
            
            logger.info(f"Chunk 批量保存成功: doc_id={doc_id}, 数量={len(chunks_to_insert)}")
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
        doc_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        向量检索 Chunk
        
        Args:
            session: 数据库会话
            query_vector: 查询向量
            kb_id: 知识库 ID（可选）
            doc_ids: 文档 ID 列表（可选）
            top_k: 返回数量
            
        Returns:
            检索结果列表，按相似度降序排列
        """
        from models.models import Chunk
        
        try:
            # 构建查询
            stmt = select(
                Chunk,
                Chunk.content_vector.l2_distance(query_vector).label('distance')
            )
            
            # 添加过滤条件
            conditions = []
            if kb_id:
                conditions.append(Chunk.kb_id == kb_id)
            if doc_ids:
                conditions.append(Chunk.doc_id.in_(doc_ids))
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            # 按距离排序并限制数量
            stmt = stmt.order_by(text('distance')).limit(top_k)
            
            results = session.execute(stmt).all()
            
            # 构建输出结果
            output = []
            for chunk, distance in results:
                # 将 L2 距离转换为相似度分数（距离越小，相似度越高）
                # 使用 1 / (1 + distance) 转换
                similarity = 1.0 / (1.0 + float(distance))
                
                output.append({
                    'chunk_id': chunk.id,
                    'chunk_type': chunk.chunk_type.value,
                    'content': chunk.content,
                    'retrieval_text': chunk.retrieval_text,
                    'metadata': json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {},
                    'score': similarity
                })
            
            logger.info(f"Chunk 检索完成: kb_id={kb_id}, doc_ids={doc_ids}, 结果数={len(output)}")
            return output
            
        except SQLAlchemyError as e:
            logger.error(f"Chunk 检索失败: {e}")
            return []
