"""文档处理器抽象基类"""

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseDocumentProcessor(ABC):
    """
    文档处理器的抽象基类
    
    所有具体处理器（如PDF处理器）都必须继承此类并实现process方法
    
    注意: 需求 5.4 - parsing_service 参数已废弃，新处理器不再需要此参数
    """
    
    def __init__(
        self,
        doc_id: str,
        db_session,
        crud_service,
        parsing_service=None,  # 已废弃，保留用于向后兼容
        chunking_service=None,  # 已废弃，新处理器使用 OCR 模块的分块功能
        vector_service=None,
        enhancement_service=None,
        markdown_processor=None,  # 已废弃，新处理器不再需要
        minio_service=None,
        **kwargs  # 接受额外参数，便于扩展
    ):
        """
        初始化处理器
        
        Args:
            doc_id: 文档ID
            db_session: 数据库会话
            crud_service: DocumentCRUD实例
            parsing_service: ParsingService实例（已废弃，保留用于向后兼容）
            chunking_service: ChunkingService实例（已废弃）
            vector_service: VectorService实例
            enhancement_service: EnhancementService实例（可选，KB轨道需要）
            markdown_processor: MarkdownProcessor实例（已废弃）
            minio_service: MinIO服务实例（可选）
            **kwargs: 额外参数（如 ocr_parser_name, chunk_strategy 等）
        """
        self.doc_id = doc_id
        self.db = db_session
        self.crud = crud_service
        self.parser = parsing_service  # 已废弃
        self.chunker = chunking_service  # 已废弃
        self.vectorizer = vector_service
        self.enhancer = enhancement_service
        self.md_processor = markdown_processor  # 已废弃
        self.minio = minio_service
        
        logger.info(f"处理器初始化: {self.__class__.__name__}, doc_id={doc_id}")
    
    @abstractmethod
    async def process(self):
        """
        处理该文档类型的完整端到端流程
        
        这是Celery任务调用的唯一入口方法
        方法内部将编排不同的service来完成具体工作
        
        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现process方法")
    
    def _log_status(self, status: str, message: str = ""):
        """
        记录日志并可选地更新数据库状态
        
        Args:
            status: 状态描述
            message: 附加消息
        """
        log_msg = f"[{self.doc_id}] {status}"
        if message:
            log_msg += f": {message}"
        logger.info(log_msg)






