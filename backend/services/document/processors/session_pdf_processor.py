"""会话轨道PDF处理器"""

import logging
from typing import List, Dict, Any
from .base import BaseDocumentProcessor
from models.models import DocumentStatus, UnitType

logger = logging.getLogger(__name__)


class SessionPDFProcessor(BaseDocumentProcessor):
    """
    会话轨道PDF处理器
    
    处理流程（全自动，可中断）：
    1. 快速解析 + 清洗 + 兜底
    2. 扁平化分块（L1→L2，只保留L2）
    3. 可中断向量化
    4. 批量入库
    """
    
    async def process(self):
        """执行会话轨道的PDF处理流程"""
        import time
        
        try:
            start_time = time.time()
            logger.info(f"开始处理 | doc_id={self.doc_id} | 轨道=会话")
            
            # ========== 检查点1：任务是否有效 ==========
            if not self.crud.is_document_task_valid(self.db, self.doc_id):
                logger.warning(f"任务已取消 | doc_id={self.doc_id} | 检查点=初始")
                return
            
            # 获取文档信息
            document = self.crud.get_document_by_id(self.db, self.doc_id)
            if not document:
                logger.error(f"文档不存在: {self.doc_id}")
                return
            
            # ========== 阶段1: 解析 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | QUEUED -> PARSING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.PARSING
            )
            
            # 使用会话轨道策略（快速+清洗+兜底）
            md_text = await self.parser.parse_document(
                document.file_path,
                document.document_type.value,
                self.minio,
                track='session'
            )
            
            if not md_text:
                error_msg = "解析失败，未能获取文本内容"
                self.crud.update_document_status(
                    self.db, self.doc_id, DocumentStatus.FAILED, error_msg
                )
                logger.error(f"[{self.doc_id}] {error_msg}")
                return
            
            # ========== 检查点2：分块前 ==========
            if not self.crud.is_document_task_valid(self.db, self.doc_id):
                logger.warning(f"任务已取消 | doc_id={self.doc_id} | 检查点=解析后")
                return
            
            # ========== 阶段2: 分块 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | PARSING -> CHUNKING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.CHUNKING
            )
            
            # 扁平化分块（只保留L2）
            l2_chunks = self.chunker.chunk_flat(md_text)
            
            if not l2_chunks:
                error_msg = "分块失败，未生成任何文本块"
                self.crud.update_document_status(
                    self.db, self.doc_id, DocumentStatus.FAILED, error_msg
                )
                logger.error(f"[{self.doc_id}] {error_msg}")
                return
            
            # ========== 检查点3：向量化前 ==========
            if not self.crud.is_document_task_valid(self.db, self.doc_id):
                logger.warning(f"任务已取消 | doc_id={self.doc_id} | 检查点=分块后")
                return
            
            # ========== 阶段3: 向量化（可中断） ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | CHUNKING -> VECTORIZING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.VECTORIZING
            )
            
            # 使用可中断的向量化
            vectors = await self.vectorizer.get_embeddings_interruptible(
                self.doc_id,
                self.db,
                l2_chunks,
                batch_size=32
            )
            
            # 检查是否在向量化过程中被取消
            if vectors is None:
                logger.warning(f"任务已取消 | doc_id={self.doc_id} | 检查点=向量化中")
                return
            
            # 检查向量化结果
            if len(vectors) != len(l2_chunks):
                error_msg = f"向量化数量不匹配: {len(vectors)} != {len(l2_chunks)}"
                self.crud.update_document_status(
                    self.db, self.doc_id, DocumentStatus.FAILED, error_msg
                )
                logger.error(f"[{self.doc_id}] {error_msg}")
                return
            
            # ========== 检查点4：入库前 ==========
            if not self.crud.is_document_task_valid(self.db, self.doc_id):
                logger.warning(f"任务已取消 | doc_id={self.doc_id} | 检查点=向量化后")
                return
            
            # ========== 阶段4: 入库 ==========
            logger.info(f"开始入库 | doc_id={self.doc_id}")
            
            # 构建units_data
            units_data = []
            for i, (content, vector) in enumerate(zip(l2_chunks, vectors)):
                if vector is None:
                    logger.warning(f"跳过向量化失败的块: {i}")
                    continue
                
                units_data.append({
                    'unit_type': UnitType.TEXT_SPLIT,
                    'content': content,
                    'summary': None,
                    'metadata': {'chunk_index': i},
                    'parent_id': None,  # 扁平结构，无父节点
                    'retrieval_text': content,  # L2使用content
                    'text_vector': vector
                })
            
            # 批量保存
            success = self.crud.save_pipeline_data(
                self.db,
                self.doc_id,
                units_data,
                summary=None,  # 会话轨道无文档摘要
                summary_vector=None
            )
            
            if not success:
                error_msg = "数据入库失败"
                self.crud.update_document_status(
                    self.db, self.doc_id, DocumentStatus.FAILED, error_msg
                )
                logger.error(f"[{self.doc_id}] {error_msg}")
                return
            
            logger.info(f"入库完成 | doc_id={self.doc_id} | 单元数={len(units_data)}")
            
            # ========== 阶段5: 完成 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | VECTORIZING -> COMPLETED")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.COMPLETED
            )
            
            duration = time.time() - start_time
            logger.info(f"处理完成 | doc_id={self.doc_id} | 总耗时={duration:.2f}s | ✓")
            
        except Exception as e:
            error_msg = f"处理异常: {str(e)}"
            logger.error(f"处理失败 | doc_id={self.doc_id} | 错误={error_msg}", exc_info=True)
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.FAILED, error_msg
            )

