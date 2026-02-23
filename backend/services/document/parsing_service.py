"""
文档解析服务（已废弃）

警告: 此模块已废弃，请使用新的 OCR 模块替代。
- 新模块位置: backend/services/ocr/
- 新处理器: backend/services/document/processors/pdf_processor.py

废弃原因（需求 5）:
- 5.1: 移除对 http://127.0.0.1:8011 外部微服务的调用
- 5.2: 移除 pymupdf4llm 快速解析
- 5.3: 移除 ZIP 文件提取逻辑
- 5.4: 由新的 OCR 模块替代

迁移指南:
1. 使用 OCRParserFactory.create("paddle_ocr") 获取解析器
2. 调用 parser.parse_bytes(file_bytes, file_name) 进行解析
3. 使用 extract_and_upload_images() 处理图片
4. 使用 chunk_by_block() 或 chunk_by_recursive() 进行分块
"""

import warnings
import logging
import httpx
import zipfile
import io
import os
from typing import Optional
from pathlib import Path

from utils.text_cleaner import clean_markdown, is_text_empty

logger = logging.getLogger(__name__)

# 发出废弃警告
warnings.warn(
    "ParsingService 已废弃，请使用 services.ocr 模块替代。"
    "详见 backend/services/document/parsing_service.py 文件头部注释。",
    DeprecationWarning,
    stacklevel=2
)


class ParsingService:
    """
    文档解析服务类（已废弃）
    
    警告: 此类已废弃，请使用新的 OCR 模块替代。
    
    废弃的功能:
    - parse_document_fast(): 使用 pymupdf4llm 快速解析（需求 5.2）
    - parse_document_quality_get_zip(): 调用外部微服务（需求 5.1）
    - _extract_markdown_from_zip(): ZIP 文件提取（需求 5.3）
    - process_zip_and_upload_images(): ZIP 图片处理（需求 5.3）
    
    替代方案:
    - 使用 services.ocr.OCRParserFactory 获取解析器
    - 使用 services.ocr.extract_and_upload_images() 处理图片
    """
    
    def __init__(self):
        """初始化解析服务（已废弃）"""
        warnings.warn(
            "ParsingService 已废弃，请使用 services.ocr 模块替代",
            DeprecationWarning,
            stacklevel=2
        )
        # 以下配置已废弃（需求 5.1）
        # self.quality_parse_url = "http://127.0.0.1:8011/parse"
        # self.timeout = 300
    
    async def parse_document_fast(self, file_path: str, doc_type: str, minio_client) -> Optional[str]:
        """
        使用pymupdf4llm进行快速本地解析（已废弃）
        
        警告: 此方法已废弃（需求 5.2），请使用新的 OCR 模块替代。
        
        Args:
            file_path: MinIO文件路径
            doc_type: 文档类型
            minio_client: MinIO客户端实例
            
        Returns:
            Markdown文本或None
            
        Raises:
            DeprecationWarning: 此方法已废弃
        """
        warnings.warn(
            "parse_document_fast() 已废弃（需求 5.2），请使用 OCRParserFactory 替代",
            DeprecationWarning,
            stacklevel=2
        )
        
        # 以下代码已废弃，保留仅供参考
        raise NotImplementedError(
            "此方法已废弃。请使用新的 OCR 模块:\n"
            "  from services.ocr import OCRParserFactory\n"
            "  parser = OCRParserFactory.create('paddle_ocr')\n"
            "  blocks = await parser.parse_bytes(file_bytes, file_name)"
        )
    
    async def parse_document_quality_get_zip(
        self, 
        file_path: str, 
        doc_type: str,
        minio_client
    ) -> Optional[bytes]:
        """
        调用高质量解析微服务，返回ZIP内容（已废弃）
        
        警告: 此方法已废弃（需求 5.1, 5.3），请使用新的 OCR 模块替代。
        
        Args:
            file_path: MinIO文件路径
            doc_type: 文档类型
            minio_client: MinIO客户端实例
            
        Returns:
            ZIP文件的二进制内容或None
            
        Raises:
            DeprecationWarning: 此方法已废弃
        """
        warnings.warn(
            "parse_document_quality_get_zip() 已废弃（需求 5.1, 5.3），请使用 OCRParserFactory 替代",
            DeprecationWarning,
            stacklevel=2
        )
        
        # 以下代码已废弃，保留仅供参考
        raise NotImplementedError(
            "此方法已废弃。请使用新的 OCR 模块:\n"
            "  from services.ocr import OCRParserFactory\n"
            "  parser = OCRParserFactory.create('paddle_ocr')\n"
            "  blocks = await parser.parse_bytes(file_bytes, file_name)"
        )
    
    async def parse_document_quality(
        self, 
        file_path: str, 
        doc_type: str,
        minio_client
    ) -> Optional[str]:
        """
        调用高质量解析微服务（已废弃）
        
        警告: 此方法已废弃（需求 5.1, 5.3），请使用新的 OCR 模块替代。
        
        Args:
            file_path: MinIO文件路径
            doc_type: 文档类型
            minio_client: MinIO客户端实例
            
        Returns:
            Markdown文本或None
            
        Raises:
            DeprecationWarning: 此方法已废弃
        """
        warnings.warn(
            "parse_document_quality() 已废弃（需求 5.1, 5.3），请使用 OCRParserFactory 替代",
            DeprecationWarning,
            stacklevel=2
        )
        
        raise NotImplementedError(
            "此方法已废弃。请使用新的 OCR 模块:\n"
            "  from services.ocr import OCRParserFactory\n"
            "  parser = OCRParserFactory.create('paddle_ocr')\n"
            "  blocks = await parser.parse_bytes(file_bytes, file_name)"
        )
    
    def _extract_markdown_from_zip(self, zip_content: bytes) -> Optional[str]:
        """
        从ZIP内容中提取Markdown文本（已废弃）
        
        警告: 此方法已废弃（需求 5.3），请使用新的 OCR 模块替代。
        
        Args:
            zip_content: ZIP文件的二进制内容
            
        Returns:
            Markdown文本或None
            
        Raises:
            DeprecationWarning: 此方法已废弃
        """
        warnings.warn(
            "_extract_markdown_from_zip() 已废弃（需求 5.3），ZIP 文件提取逻辑已移除",
            DeprecationWarning,
            stacklevel=2
        )
        
        raise NotImplementedError(
            "此方法已废弃。新的 OCR 模块直接返回 SimpleBlock 列表，不再使用 ZIP 格式。"
        )
    
    async def parse_document(
        self, 
        file_path: str, 
        doc_type: str,
        minio_client,
        track: str = 'session',
        kb_id: Optional[str] = None,
        doc_id: Optional[str] = None
    ) -> Optional[str]:
        """
        统一文档解析入口（已废弃）
        
        警告: 此方法已废弃（需求 5.4），请使用新的 OCR 模块替代。
        
        Args:
            file_path: MinIO文件路径
            doc_type: 文档类型
            minio_client: MinIO客户端实例
            track: 轨道类型 ('session' 或 'kb')
            kb_id: 知识库ID（仅kb轨道需要）
            doc_id: 文档ID（仅kb轨道需要）
            
        Returns:
            Markdown文本或None
            
        Raises:
            DeprecationWarning: 此方法已废弃
        """
        warnings.warn(
            "parse_document() 已废弃（需求 5.4），请使用 PDFProcessor 替代",
            DeprecationWarning,
            stacklevel=2
        )
        
        raise NotImplementedError(
            "此方法已废弃。请使用新的 PDFProcessor:\n"
            "  from services.document.processors import PDFProcessor\n"
            "  processor = PDFProcessor(doc_id, db, crud, vector_service, ...)\n"
            "  await processor.process()"
        )
    
    async def _parse_kb_document(
        self,
        file_path: str,
        doc_type: str,
        minio_client,
        kb_id: str,
        doc_id: str
    ) -> Optional[str]:
        """
        知识库轨道解析流程（已废弃）
        
        警告: 此方法已废弃（需求 5.4），请使用新的 PDFProcessor 替代。
        """
        warnings.warn(
            "_parse_kb_document() 已废弃（需求 5.4），请使用 PDFProcessor 替代",
            DeprecationWarning,
            stacklevel=2
        )
        
        raise NotImplementedError(
            "此方法已废弃。请使用新的 PDFProcessor。"
        )
    
    async def process_zip_and_upload_images(
        self,
        zip_content: bytes,
        kb_id: str,
        doc_id: str,
        minio_client
    ) -> Optional[str]:
        """
        处理解析服务返回的ZIP包（已废弃）
        
        警告: 此方法已废弃（需求 5.3），请使用新的 OCR 模块替代。
        
        新的图片处理流程:
        - 使用 services.ocr.extract_and_upload_images() 处理图片
        - 图片直接从 PDF 裁剪，不再从 ZIP 提取
        
        Args:
            zip_content: ZIP文件的二进制内容
            kb_id: 知识库ID
            doc_id: 文档ID
            minio_client: MinIO客户端实例
            
        Returns:
            处理后的Markdown文本
            
        Raises:
            DeprecationWarning: 此方法已废弃
        """
        warnings.warn(
            "process_zip_and_upload_images() 已废弃（需求 5.3），请使用 extract_and_upload_images() 替代",
            DeprecationWarning,
            stacklevel=2
        )
        
        raise NotImplementedError(
            "此方法已废弃。请使用新的图片处理流程:\n"
            "  from services.ocr import extract_and_upload_images\n"
            "  blocks = await extract_and_upload_images(\n"
            "      pdf_bytes, blocks, kb_id, doc_id, storage_service\n"
            "  )"
        )
    
    @staticmethod
    def _get_image_content_type(filename: str) -> str:
        """根据文件名获取Content-Type"""
        ext = filename.lower().split('.')[-1]
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'bmp': 'image/bmp'
        }
        return content_types.get(ext, 'application/octet-stream')

