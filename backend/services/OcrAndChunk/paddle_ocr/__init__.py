"""
PaddleOCR 解析器模块

基于 PaddleX API 的 PDF 版式解析实现。
"""

from .parser import PaddleOCRParser
from .client import PaddleOCRClient
from .converter import (
    convert_bbox_to_pdf_coords,
    convert_to_simple_blocks,
    parse_response,
)
from .types import (
    API_URL,
    API_TOKEN,
    DEFAULT_TIMEOUT,
    DEFAULT_PDF_SIZE,
    MAIN_TYPE_MAP,
    SKIP_TYPES,
    CAPTION_TYPES,
    FOOTNOTE_TYPES,
    IMAGE_TYPES,
    TABLE_TYPES,
)

__all__ = [
    # 解析器
    "PaddleOCRParser",
    "PaddleOCRClient",
    # 转换器
    "convert_bbox_to_pdf_coords",
    "convert_to_simple_blocks",
    "parse_response",
    # 配置
    "API_URL",
    "API_TOKEN",
    "DEFAULT_TIMEOUT",
    "DEFAULT_PDF_SIZE",
    # 类型映射
    "MAIN_TYPE_MAP",
    "SKIP_TYPES",
    "CAPTION_TYPES",
    "FOOTNOTE_TYPES",
    "IMAGE_TYPES",
    "TABLE_TYPES",
]
