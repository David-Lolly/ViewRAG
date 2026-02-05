"""文档处理Celery任务"""

import logging
import asyncio
from celery_app import celery
from crud.database import SessionLocal
from crud.document_crud import DocumentCRUD
from services.document import (
    ParsingService,
    ChunkingService,
    VectorService,
    EnhancementService,
    MarkdownProcessor
)
from services.document.processors import PROCESSOR_MAP
from services.storage import minio_storage

logger = logging.getLogger(__name__)


@celery.task(name="process_session_document", bind=True)
def process_session_document(self, doc_id: str):
    """
    处理会话轨道文档的Celery任务
    
    Args:
        doc_id: 文档ID
    """
    logger.info(f"接收到会话文档处理任务: {doc_id}")
    
    db = SessionLocal()
    
    try:
        # 1. 获取文档信息
        document = DocumentCRUD.get_document_by_id(db, doc_id)
        if not document:
            logger.error(f"文档不存在: {doc_id}")
            return
        
        # 2. 初始化所有Service
        parsing_service = ParsingService()
        chunking_service = ChunkingService()
        vector_service = VectorService()
        
        # 3. 获取处理器类
        doc_type = document.document_type.value
        ProcessorClass = PROCESSOR_MAP.get((doc_type, 'session'))
        
        if not ProcessorClass:
            error_msg = f"不支持的文档类型: {doc_type}"
            logger.error(error_msg)
            DocumentCRUD.update_document_status(
                db, doc_id, 'FAILED', error_msg
            )
            return
        
        # 4. 实例化处理器
        processor = ProcessorClass(
            doc_id=doc_id,
            db_session=db,
            crud_service=DocumentCRUD,
            parsing_service=parsing_service,
            chunking_service=chunking_service,
            vector_service=vector_service,
            minio_service=minio_storage
        )
        
        # 5. 执行处理（异步转同步）
        asyncio.run(processor.process())
        
        logger.info(f"会话文档处理完成: {doc_id}")
        
    except Exception as e:
        logger.error(f"会话文档处理失败: {doc_id}, 错误: {e}", exc_info=True)
        DocumentCRUD.update_document_status(
            db, doc_id, 'FAILED', str(e)
        )
    finally:
        db.close()


@celery.task(name="process_kb_document", bind=True)
def process_kb_document(self, doc_id: str):
    """
    处理知识库轨道文档的Celery任务
    
    Args:
        doc_id: 文档ID
    """
    logger.info(f"接收到知识库文档处理任务: {doc_id}")
    
    db = SessionLocal()
    
    try:
        # 1. 获取文档信息
        document = DocumentCRUD.get_document_by_id(db, doc_id)
        if not document:
            logger.error(f"文档不存在: {doc_id}")
            return
        
        # 2. 初始化所有Service
        parsing_service = ParsingService()
        chunking_service = ChunkingService()
        vector_service = VectorService()
        enhancement_service = EnhancementService(minio_service=minio_storage)
        markdown_processor = MarkdownProcessor()
        
        # 3. 获取处理器类
        doc_type = document.document_type.value
        ProcessorClass = PROCESSOR_MAP.get((doc_type, 'kb'))
        
        if not ProcessorClass:
            error_msg = f"不支持的文档类型: {doc_type}"
            logger.error(error_msg)
            DocumentCRUD.update_document_status(
                db, doc_id, 'FAILED', error_msg
            )
            return
        
        # 4. 实例化处理器
        processor = ProcessorClass(
            doc_id=doc_id,
            db_session=db,
            crud_service=DocumentCRUD,
            parsing_service=parsing_service,
            chunking_service=chunking_service,
            vector_service=vector_service,
            enhancement_service=enhancement_service,
            markdown_processor=markdown_processor,
            minio_service=minio_storage
        )
        
        # 5. 执行处理（异步转同步）
        asyncio.run(processor.process())
        
        logger.info(f"知识库文档处理完成: {doc_id}")
        
    except Exception as e:
        logger.error(f"知识库文档处理失败: {doc_id}, 错误: {e}", exc_info=True)
        DocumentCRUD.update_document_status(
            db, doc_id, 'FAILED', str(e)
        )
    finally:
        db.close()

