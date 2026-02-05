"""向量化服务"""

import logging
import numpy as np
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from crud.config_manager import config

logger = logging.getLogger(__name__)


class VectorService:
    """向量化服务类"""
    
    def __init__(self):
        """初始化向量服务"""
        self.API_MAX_BATCH_SIZE = 10
        self.EMBEDDING_MAX_LENGTH = 1024
        self.max_workers = min(self.API_MAX_BATCH_SIZE, 4)
        self.max_retries = 3
        self.request_timeout = 30
        
        # 初始化HTTP会话
        self.session = requests.Session()
        retries = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            "Authorization": f"Bearer {config.get('embedding_api_key')}",
            "Content-Type": "application/json"
        })
    
    def _embed_batch_cloud(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        调用云端API进行批量向量化
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表或None
        """
        payload = {
            "model": config.get('embedding_model_name'),
            "input": texts,
            "encoding_format": "float"
        }
        
        try:
            response = self.session.post(
                config.get('embedding_base_url'),
                json=payload,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            data = response.json()["data"]
            data.sort(key=lambda x: x['index'])
            
            return [item["embedding"] for item in data]
            
        except Exception as e:
            logger.error(f"云端embedding批处理失败: {e}")
            return None
    
    def get_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        获取文本向量（不可中断）
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        import time
        
        if not texts:
            return []
        
        start_time = time.time()
        logger.info(f"开始向量化 | 文本数={len(texts)} | 批次大小={self.API_MAX_BATCH_SIZE}")
        
        all_embeddings: List[Optional[List[float]]] = [None] * len(texts)
        batches = [
            texts[i:i + self.API_MAX_BATCH_SIZE] 
            for i in range(0, len(texts), self.API_MAX_BATCH_SIZE)
        ]
        
        logger.debug(f"向量化配置 | 总批次={len(batches)} | 并发数={self.max_workers} | 超时={self.request_timeout}s")
        
        completed_batches = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_index = {
                executor.submit(self._embed_batch_cloud, batch): i * self.API_MAX_BATCH_SIZE
                for i, batch in enumerate(batches)
            }
            
            for future in as_completed(future_to_index):
                start_index = future_to_index[future]
                batch_embeddings = future.result()
                
                if batch_embeddings:
                    for i, emb in enumerate(batch_embeddings):
                        all_embeddings[start_index + i] = emb
                    completed_batches += 1
                    logger.debug(f"批次完成 | 当前={completed_batches}/{len(batches)} | 起始索引={start_index}")
                else:
                    logger.warning(f"批次失败 | 批次索引={start_index // self.API_MAX_BATCH_SIZE} | 起始索引={start_index}")
        
        success_count = sum(1 for emb in all_embeddings if emb is not None)
        failed_count = len(texts) - success_count
        success_rate = (success_count / len(texts) * 100) if texts else 0
        duration = time.time() - start_time
        
        logger.info(f"向量化完成 | 总数={len(texts)} | 成功={success_count} | 失败={failed_count} | 成功率={success_rate:.1f}% | 耗时={duration:.2f}s")
        
        if failed_count > 0:
            failed_indices = [i for i, emb in enumerate(all_embeddings) if emb is None]
            logger.debug(f"失败索引 | {failed_indices[:10]}{'...' if len(failed_indices) > 10 else ''}")
        
        return all_embeddings
    
    async def get_embeddings_interruptible(
        self,
        doc_id: str,
        db_session,
        texts: List[str],
        batch_size: int = 32
    ) -> Optional[List[List[float]]]:
        """
        可中断的向量化（会话轨道专用）
        
        在每批次之间检查任务是否已被取消
        
        Args:
            doc_id: 文档ID
            db_session: 数据库会话
            texts: 文本列表
            batch_size: 批次大小
            
        Returns:
            向量列表或None（如果任务被取消）
        """
        from crud.document_crud import DocumentCRUD
        
        if not texts:
            return []
        
        logger.info(f"开始可中断向量化 | doc_id={doc_id} | 文本数={len(texts)} | 批次大小={batch_size}")
        
        all_embeddings = []
        total_batches = (len(texts) - 1) // batch_size + 1
        
        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            # 检查点：任务是否仍然有效
            if not DocumentCRUD.is_document_task_valid(db_session, doc_id):
                logger.warning(f"任务已取消 | doc_id={doc_id} | 检查点=向量化批次{batch_num}")
                return None
            
            # 处理当前批次
            logger.debug(f"处理批次 | 批次={batch_num}/{total_batches} | 文本数={len(batch)}")
            batch_embeddings = self.get_embeddings(batch)
            
            # 检查是否有失败的
            failed_in_batch = sum(1 for emb in batch_embeddings if emb is None)
            if failed_in_batch > 0:
                logger.warning(f"批次部分失败 | 批次={batch_num} | 失败数={failed_in_batch}/{len(batch)}")
            
            all_embeddings.extend(batch_embeddings)
            
            logger.info(f"批次完成 | 当前={batch_num}/{total_batches} | 累计向量数={len(all_embeddings)}")
        
        # 最后再检查一次
        if not DocumentCRUD.is_document_task_valid(db_session, doc_id):
            logger.warning(f"任务已取消 | doc_id={doc_id} | 检查点=向量化完成后")
            return None
        
        total_failed = sum(1 for emb in all_embeddings if emb is None)
        logger.info(f"可中断向量化完成 | doc_id={doc_id} | 总数={len(all_embeddings)} | 失败={total_failed}")
        return all_embeddings
    
    def close(self):
        """关闭HTTP会话"""
        if hasattr(self, 'session'):
            self.session.close()
            logger.info("向量服务HTTP会话已关闭")

