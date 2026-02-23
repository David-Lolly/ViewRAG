"""文档处理器模块"""

from .base import BaseDocumentProcessor
from .pdf_processor import PDFProcessor

# 处理器映射表：(文档类型, 轨道) -> 处理器类
PROCESSOR_MAP = {
    ('PDF', 'session'): PDFProcessor,
    ('PDF', 'kb'): PDFProcessor,
}

__all__ = [
    "BaseDocumentProcessor",
    "PDFProcessor",
    "PROCESSOR_MAP"
]






