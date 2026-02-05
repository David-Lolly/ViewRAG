"""文档处理器抽象基类"""

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseDocumentProcessor(ABC):
    """
    文档处理器的抽象基类
    
    所有具体处理器（如PDF处理器）都必须继承此类并实现process方法
    """
    
    def __init__(
        self,
        doc_id: str,
        db_session,
        crud_service,
        parsing_service,
        chunking_service,
        vector_service,
        enhancement_service=None,
        markdown_processor=None,
        minio_service=None
    ):
        """
        初始化处理器
        
        Args:
            doc_id: 文档ID
            db_session: 数据库会话
            crud_service: DocumentCRUD实例
            parsing_service: ParsingService实例
            chunking_service: ChunkingService实例
            vector_service: VectorService实例
            enhancement_service: EnhancementService实例（可选，KB轨道需要）
            markdown_processor: MarkdownProcessor实例（可选，KB轨道需要）
            minio_service: MinIO服务实例（可选）
        """
        self.doc_id = doc_id
        self.db = db_session
        self.crud = crud_service
        self.parser = parsing_service
        self.chunker = chunking_service
        self.vectorizer = vector_service
        self.enhancer = enhancement_service
        self.md_processor = markdown_processor
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






