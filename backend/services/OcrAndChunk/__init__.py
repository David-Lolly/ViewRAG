"""
OCR 解析模块

提供可扩展的 OCR 解析架构，支持多种解析器实现（PaddleOCR、MonkeyOCR 等）。
所有解析器输出统一的 SimpleBlock 格式。
"""

from .types import SimpleBlock, BlockType
from .base import BaseOCRParser
from .factory import OCRParserFactory
from .paddle_ocr.parser import PaddleOCRParser
from .image_extractor import (
    extract_image_from_pdf,
    extract_and_upload_images,
    extract_image_bytes_from_pdf,
    compute_sha256,
)

# 注册 PaddleOCR 解析器
OCRParserFactory.register("paddle_ocr", PaddleOCRParser)

__all__ = [
    "SimpleBlock",
    "BlockType",
    "BaseOCRParser",
    "OCRParserFactory",
    "PaddleOCRParser",
    # 图片裁剪工具
    "extract_image_from_pdf",
    "extract_and_upload_images",
    "extract_image_bytes_from_pdf",
    "compute_sha256",
]
