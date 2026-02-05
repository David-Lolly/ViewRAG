"""统一RAG检索服务"""

import logging
from typing import List, Dict, Any, Optional
from crud.document_crud import DocumentCRUD, ChunkCRUD
from services.document.vector_service import VectorService

logger = logging.getLogger(__name__)


class UnifiedRetrievalService:
    """统一的RAG检索引擎（简化版）"""
    
    def __init__(self):
        """初始化检索服务"""
        self.vector_service = VectorService()
    
    async def search(
        self,
        query: str,
        db_session,
        kb_id: Optional[str] = None,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        向量检索
        
        Args:
            query: 查询文本
            db_session: 数据库会话
            kb_id: 知识库 ID（可选）
            doc_ids: 文档 ID 列表（可选）
            top_k: 返回数量
            
        Returns:
            检索结果列表，每个元素包含:
            {
                'chunk_id': str,
                'chunk_type': str,
                'content': str,
                'retrieval_text': str,
                'metadata': dict,
                'score': float
            }
        """
        try:
            logger.info(f"开始检索 | query={query[:50]}... | kb_id={kb_id} | doc_ids={doc_ids}")
            
            # 1. 向量化查询文本
            query_vectors = self.vector_service.get_embeddings([query])
            query_vector = query_vectors[0] if query_vectors else None
            
            if not query_vector:
                logger.error("查询向量化失败")
                return []
            
            # 2. 使用 ChunkCRUD 进行向量检索
            results = ChunkCRUD.search_chunks(
                db_session,
                query_vector,
                kb_id=kb_id,
                doc_ids=doc_ids,
                top_k=top_k
            )
            
            logger.info(f"检索完成 | 结果数={len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"检索失败: {e}", exc_info=True)
            return []
    
    def build_context(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        构建 LLM 上下文
        
        根据 chunk_type 区分处理：
        - TEXT: 返回 content
        - IMAGE: 返回图片 URL（content 字段）
        - TABLE: 返回原始 Markdown（content 字段）
        
        Args:
            chunks: 检索结果列表
            
        Returns:
            上下文列表，每个元素包含:
            {
                'type': 'text' | 'image' | 'table',
                'content': str
            }
        """
        context_items = []
        
        for chunk in chunks:
            chunk_type = chunk.get('chunk_type', 'TEXT')
            content = chunk.get('content', '')
            
            if chunk_type == 'TEXT':
                context_items.append({
                    'type': 'text',
                    'content': content
                })
            elif chunk_type == 'IMAGE':
                context_items.append({
                    'type': 'image',
                    'content': content  # 图片 URL
                })
            elif chunk_type == 'TABLE':
                context_items.append({
                    'type': 'table',
                    'content': content  # 原始 Markdown
                })
        
        return context_items
    
    async def get_rag_context(
        self,
        query: str,
        document_ids: List[str],
        db_session,
        top_k: int = 5
    ) -> str:
        """
        统一RAG引擎入口（简化版）
        
        Args:
            query: 用户查询
            document_ids: 文档ID列表
            db_session: 数据库会话
            top_k: 返回结果数量
            
        Returns:
            格式化的上下文文本
        """
        try:
            logger.info(f"开始RAG检索 | query={query[:50]}... | 文档数={len(document_ids)}")
            
            # 1. 执行检索
            results = await self.search(
                query=query,
                db_session=db_session,
                doc_ids=document_ids,
                top_k=top_k
            )
            
            if not results:
                logger.warning("检索结果为空")
                return ""
            
            # 2. 构建上下文
            context_items = self.build_context(results)
            
            # 3. 格式化上下文
            formatted_context = self._format_context(context_items, results)
            
            logger.info(f"RAG检索完成 | 上下文长度={len(formatted_context)}")
            return formatted_context
            
        except Exception as e:
            logger.error(f"RAG检索失败: {e}", exc_info=True)
            return ""
    
    def _format_context(
        self, 
        context_items: List[Dict[str, Any]], 
        chunks: List[Dict[str, Any]]
    ) -> str:
        """
        格式化检索结果为上下文文本
        
        Args:
            context_items: 上下文项列表
            chunks: 原始检索结果（用于获取 metadata）
            
        Returns:
            格式化的上下文字符串
        """
        if not context_items:
            return ""
        
        formatted_parts = []
        for i, (ctx, chunk) in enumerate(zip(context_items, chunks), 1):
            content = ctx.get('content', '')
            ctx_type = ctx.get('type', 'text')
            metadata = chunk.get('metadata', {})
            
            # 添加元数据信息
            meta_info = ""
            if ctx_type == 'image':
                caption = metadata.get('caption', '')
                meta_info = f"[图片: {caption}]" if caption else "[图片]"
            elif ctx_type == 'table':
                caption = metadata.get('caption', '')
                meta_info = f"[表格: {caption}]" if caption else "[表格]"
            else:
                heading_path = metadata.get('heading_path', [])
                if heading_path:
                    meta_info = f"[章节: {' > '.join(heading_path)}]"
            
            formatted_parts.append(f"片段{i}{meta_info}:\n{content}\n")
        
        return "\n".join(formatted_parts)
    
    def close(self):
        """关闭资源"""
        if hasattr(self, 'vector_service'):
            self.vector_service.close()

