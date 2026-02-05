"""文档处理器模块"""

from .base import BaseDocumentProcessor
from .session_pdf_processor import SessionPDFProcessor
from .kb_pdf_processor import KBPDFProcessor

# 处理器映射表：(文档类型, 轨道) -> 处理器类
PROCESSOR_MAP = {
    ('PDF', 'session'): SessionPDFProcessor,
    ('PDF', 'kb'): KBPDFProcessor,
    # 未来扩展：
    # ('DOCX', 'session'): SessionDOCXProcessor,
    # ('DOCX', 'kb'): KBDOCXProcessor,
}

__all__ = [
    "BaseDocumentProcessor",
    "SessionPDFProcessor",
    "KBPDFProcessor",
    "PROCESSOR_MAP"
]






