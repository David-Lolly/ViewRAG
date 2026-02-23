"""
图片裁剪工具（OCR 模块通用）

根据 bbox 坐标从 PDF 页面裁剪图片，支持批量提取和上传到 MinIO。
"""

import hashlib
import logging
from typing import Optional, Tuple, List, Dict, Any

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from .types import SimpleBlock, BlockType

logger = logging.getLogger(__name__)


def compute_sha256(data: str) -> str:
    """
    计算 SHA256 哈希
    
    Args:
        data: 输入字符串
        
    Returns:
        SHA256 哈希值（完整64位）
    """
    return hashlib.sha256(data.encode()).hexdigest()


def extract_image_from_pdf(
    page: "fitz.Page",
    page_num: int,
    bbox: Tuple[float, float, float, float],
    zoom_factor: float = 3.0,
    jpeg_quality: int = 95,
    expand_px: float = 5.0
) -> Tuple[Optional[bytes], str]:
    """
    根据 bbox 坐标从 PDF 页面裁剪图片
    
    Args:
        page: PyMuPDF 页面对象
        page_num: 页码（从 0 开始）
        bbox: PDF 坐标 (x0, y0, x1, y1)
        zoom_factor: 放大倍数，默认 3 倍提高清晰度
        jpeg_quality: JPEG 质量，默认 95
        expand_px: bbox 上下左右扩展像素数，默认 5，避免边缘字体裁剪不完整
        
    Returns:
        (图片字节流 JPEG 格式, 文件名) 或 (None, "")
        文件名格式: {hash前12位}.jpg
    """
    if fitz is None:
        logger.error("PyMuPDF (fitz) 未安装，无法裁剪图片")
        return None, ""
    
    try:
        # 1. 验证 bbox 有效性
        x0, y0, x1, y1 = bbox
        if x0 >= x1 or y0 >= y1:
            logger.warning(f"无效的 bbox 坐标: page={page_num}, bbox={bbox}")
            return None, ""
        
        # 2. 生成文件名：基于原始 bbox 生成（保持稳定性）
        filename_base = f'{page_num}_{int(x0)}_{int(y0)}_{int(x1)}_{int(y1)}'
        img_hash = compute_sha256(filename_base)[:12]  # 取前 12 位
        filename = f"{img_hash}.jpg"
        
        # 3. 扩展 bbox，上下左右各延伸 expand_px，clamp 到页面边界内
        page_rect = page.rect
        x0 = max(0, x0 - expand_px)
        y0 = max(0, y0 - expand_px)
        x1 = min(page_rect.width, x1 + expand_px)
        y1 = min(page_rect.height, y1 + expand_px)
        
        # 4. 使用 PyMuPDF 裁剪
        rect = fitz.Rect(x0, y0, x1, y1)
        zoom = fitz.Matrix(zoom_factor, zoom_factor)  # 放大提高清晰度
        pix = page.get_pixmap(clip=rect, matrix=zoom)
        
        # 5. 转为 JPEG
        byte_data = pix.tobytes(output='jpeg', jpg_quality=jpeg_quality)
        
        logger.debug(f"图片裁剪成功: page={page_num}, bbox={bbox}, expand={expand_px}, size={len(byte_data)} bytes")
        return byte_data, filename
        
    except Exception as e:
        logger.error(f"图片裁剪失败: page={page_num}, bbox={bbox}, error={e}")
        return None, ""


async def extract_and_upload_images(
    pdf_bytes: bytes,
    blocks: List[SimpleBlock],
    kb_id: str,
    doc_id: str,
    storage_service: Any
) -> List[SimpleBlock]:
    """
    批量提取图片并上传到 MinIO
    
    遍历 SimpleBlock 列表，对 Image 类型的块：
    1. 根据 bbox 从 PDF 裁剪图片
    2. 上传到 MinIO
    3. 将相对路径填入 block.content
    
    Args:
        pdf_bytes: PDF 文件字节流
        blocks: SimpleBlock 列表
        kb_id: 知识库 ID
        doc_id: 文档 ID
        storage_service: MinIO 存储服务实例
        
    Returns:
        更新后的 SimpleBlock 列表（Image 类型的 content 已填充路径）
    """
    if fitz is None:
        logger.error("PyMuPDF (fitz) 未安装，无法处理图片")
        return blocks
    
    try:
        # 打开 PDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error(f"无法打开 PDF 文件: {e}")
        return blocks
    
    try:
        # 遍历所有块，处理 Image 类型
        for block in blocks:
            if block.type != BlockType.IMAGE.value:
                continue
            
            page_num = block.page
            
            # 验证页码有效性
            if page_num < 0 or page_num >= len(doc):
                logger.warning(f"无效的页码: page={page_num}, total_pages={len(doc)}")
                continue
            
            page = doc[page_num]
            bbox = tuple(block.bbox)
            
            # 裁剪图片
            image_bytes, filename = extract_image_from_pdf(page, page_num, bbox)
            
            if image_bytes is None:
                logger.warning(f"图片裁剪失败，跳过: page={page_num}, bbox={bbox}")
                continue
            
            # 构建存储路径: kbs/{kb_id}/images/{doc_id}/{hash}.jpg
            relative_path = f"kbs/{kb_id}/images/{doc_id}/{filename}"
            
            try:
                # 上传到 MinIO
                await storage_service.upload_file_bytes(
                    bucket_name=storage_service.doc_bucket,
                    object_name=relative_path,
                    file_bytes=image_bytes,
                    content_type='image/jpeg'
                )
                
                # 将相对路径填入 block.content
                block.content = relative_path
                logger.info(f"图片上传成功: {relative_path}")
                
            except Exception as e:
                logger.error(f"图片上传失败: {relative_path}, error={e}")
                # 继续处理其他图片，不中断流程
                continue
        
        return blocks
        
    finally:
        doc.close()


def extract_image_bytes_from_pdf(
    pdf_bytes: bytes,
    page_num: int,
    bbox: Tuple[float, float, float, float],
    zoom_factor: float = 3.0,
    jpeg_quality: int = 95
) -> Optional[bytes]:
    """
    从 PDF 字节流中提取指定位置的图片
    
    便捷函数，用于单独提取一张图片（如 LLM 增强时获取图片内容）
    
    Args:
        pdf_bytes: PDF 文件字节流
        page_num: 页码（从 0 开始）
        bbox: PDF 坐标 (x0, y0, x1, y1)
        zoom_factor: 放大倍数
        jpeg_quality: JPEG 质量
        
    Returns:
        图片字节流或 None
    """
    if fitz is None:
        logger.error("PyMuPDF (fitz) 未安装，无法提取图片")
        return None
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error(f"无法打开 PDF 文件: {e}")
        return None
    
    try:
        if page_num < 0 or page_num >= len(doc):
            logger.warning(f"无效的页码: page={page_num}, total_pages={len(doc)}")
            return None
        
        page = doc[page_num]
        image_bytes, _ = extract_image_from_pdf(page, page_num, bbox, zoom_factor, jpeg_quality)
        return image_bytes
        
    finally:
        doc.close()
