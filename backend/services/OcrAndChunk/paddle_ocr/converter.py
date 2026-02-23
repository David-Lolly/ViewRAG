"""
PaddleX API 响应转换器

将 PaddleX 版式解析 API 的返回结果转换为 SimpleBlock 格式。
bbox 直接转换为 PDF 坐标（72 DPI 点坐标），后续使用无需再转换。
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from ..types import SimpleBlock
from .types import (
    MAIN_TYPE_MAP,
    SKIP_TYPES,
    CAPTION_TYPES,
    FOOTNOTE_TYPES,
    IMAGE_TYPES,
    TABLE_TYPES,
    DEFAULT_PDF_SIZE,
)

logger = logging.getLogger(__name__)


def convert_bbox_to_pdf_coords(
    bbox: List[int],
    api_size: Tuple[int, int],
    pdf_size: Tuple[float, float] = DEFAULT_PDF_SIZE
) -> List[float]:
    """
    将 API 像素坐标转换为 PDF 点坐标
    
    Args:
        bbox: API 返回的像素坐标 [x0, y0, x1, y1]
        api_size: API 渲染的页面尺寸 (width, height)
        pdf_size: PDF 页面尺寸 (width, height)，默认 Letter
    
    Returns:
        PDF 点坐标 [x0, y0, x1, y1]
    """
    if not bbox or len(bbox) != 4:
        return [0.0, 0.0, 0.0, 0.0]
    
    scale_x = pdf_size[0] / api_size[0] if api_size[0] > 0 else 1.0
    scale_y = pdf_size[1] / api_size[1] if api_size[1] > 0 else 1.0
    
    return [
        bbox[0] * scale_x,
        bbox[1] * scale_y,
        bbox[2] * scale_x,
        bbox[3] * scale_y,
    ]


def _find_adjacent_block_type(
    blocks: List[Dict],
    current_idx: int
) -> Optional[str]:
    """
    查找相邻块的类型，用于判断 figure_title 属于 Image 还是 Table
    
    Args:
        blocks: 块列表
        current_idx: 当前块索引
        
    Returns:
        "Image" 或 "Table" 或 None
    """
    # 向后查找
    for i in range(current_idx + 1, min(current_idx + 3, len(blocks))):
        label = blocks[i].get("block_label", "")
        if label in IMAGE_TYPES:
            return "Image"
        if label in TABLE_TYPES:
            return "Table"
        if label in MAIN_TYPE_MAP:
            break
    
    # 向前查找
    for i in range(current_idx - 1, max(current_idx - 3, -1), -1):
        label = blocks[i].get("block_label", "")
        if label in IMAGE_TYPES:
            return "Image"
        if label in TABLE_TYPES:
            return "Table"
        if label in MAIN_TYPE_MAP:
            break
    
    return None


def _determine_caption_type(
    block: Dict,
    blocks: List[Dict],
    idx: int
) -> str:
    """
    判断 figure_title/table_title 应该归属于 Image 还是 Table
    
    Args:
        block: 当前块
        blocks: 所有块列表
        idx: 当前块索引
        
    Returns:
        "_TableCaption" 或 "_ImageCaption"
    """
    # 首先根据相邻块判断
    adjacent_type = _find_adjacent_block_type(blocks, idx)
    if adjacent_type == "Table":
        return "_TableCaption"
    if adjacent_type == "Image":
        return "_ImageCaption"
    
    # 根据内容判断
    content = block.get("block_content", "").strip().lower()
    if content.startswith("table"):
        return "_TableCaption"
    if content.startswith(("figure", "fig.", "fig ")):
        return "_ImageCaption"
    
    # 默认归属于 Image
    return "_ImageCaption"


def convert_to_simple_blocks(
    api_result: Dict[str, Any],
    recognize_table: bool = True,
    pdf_size: Tuple[float, float] = DEFAULT_PDF_SIZE,
    page_sizes: Optional[Dict[int, Tuple[float, float]]] = None,
) -> List[SimpleBlock]:
    """
    将 PaddleX API 返回结果转换为 SimpleBlock 列表
    bbox 直接转换为 PDF 坐标
    
    Args:
        api_result: API 返回的 result 字段
        recognize_table: 是否识别表格为 HTML
        pdf_size: PDF 页面尺寸回退默认值，默认 Letter (612x792)
        page_sizes: 每页真实 PDF 尺寸字典 {page_idx: (width, height)}，
                    优先级高于 pdf_size，用于多页/混合尺寸文档
        
    Returns:
        SimpleBlock 列表
    """
    all_blocks: List[SimpleBlock] = []
    
    layout_results = api_result.get("layoutParsingResults", [])
    
    for page_idx, page_result in enumerate(layout_results):
        pruned = page_result.get("prunedResult", {})
        parsing_res_list = pruned.get("parsing_res_list", [])
        
        if not parsing_res_list:
            continue
        
        # 获取 API 页面尺寸用于坐标转换
        api_size = (
            pruned.get("width", 1224),
            pruned.get("height", 1584)
        )
        
        # 优先使用每页真实 PDF 尺寸，其次回退到全局 pdf_size
        current_pdf_size = (
            page_sizes[page_idx]
            if page_sizes and page_idx in page_sizes
            else pdf_size
        )
        
        # 第一遍：确定每个块的类型
        block_types: List[str] = []
        for idx, block in enumerate(parsing_res_list):
            label = block.get("block_label", "")
            
            if label in SKIP_TYPES:
                block_types.append("_Skip")
            elif label in MAIN_TYPE_MAP:
                block_types.append(MAIN_TYPE_MAP[label])
            elif label in CAPTION_TYPES:
                block_types.append(_determine_caption_type(block, parsing_res_list, idx))
            elif label in FOOTNOTE_TYPES:
                adjacent = _find_adjacent_block_type(parsing_res_list, idx)
                block_types.append(
                    "_TableFootnote" if adjacent == "Table" else "_ImageFootnote"
                )
            else:
                # 未知类型默认为 Text
                block_types.append("Text")
        
        # 第二遍：构建 SimpleBlock，合并 caption/footnote
        page_blocks: List[Dict[str, Any]] = []
        used_indices: set = set()
        
        for idx, block in enumerate(parsing_res_list):
            if idx in used_indices:
                continue
            
            block_type = block_types[idx]
            
            # 跳过内部类型
            if block_type == "_Skip" or block_type.startswith("_"):
                continue
            
            # 查找关联的 caption 和 footnote
            caption: Optional[str] = None
            footnote: Optional[str] = None
            
            if block_type in ("Image", "Table"):
                target_caption = f"_{block_type}Caption"
                target_footnote = f"_{block_type}Footnote"
                
                # 在前后各 2 个块中查找
                for i in range(max(0, idx - 2), min(len(parsing_res_list), idx + 3)):
                    if i == idx or i in used_indices:
                        continue
                    if block_types[i] == target_caption:
                        caption = parsing_res_list[i].get("block_content", "")
                        used_indices.add(i)
                    elif block_types[i] == target_footnote:
                        footnote = parsing_res_list[i].get("block_content", "")
                        used_indices.add(i)
            
            # 构建内容
            content = block.get("block_content", "")
            if block_type == "Image":
                # Image 类型的 content 为空，后续通过 bbox 裁剪
                content = ""
            elif block_type == "Table" and not recognize_table:
                content = ""
            
            # 转换 bbox 为 PDF 坐标（使用当前页真实尺寸）
            api_bbox = block.get("block_bbox", [0, 0, 0, 0])
            pdf_bbox = convert_bbox_to_pdf_coords(api_bbox, api_size, current_pdf_size)
            
            # 获取排序顺序
            order = block.get("block_order")
            if order is None:
                order = block.get("block_id", 0)
            
            page_blocks.append({
                "type": block_type,
                "content": content,
                "caption": caption,
                "footnote": footnote,
                "page": page_idx,
                "bbox": pdf_bbox,
                "_order": order,
            })
            
            used_indices.add(idx)
        
        # 按阅读顺序排序
        page_blocks.sort(
            key=lambda x: x["_order"] if x["_order"] is not None else float('inf')
        )
        
        # 转换为 SimpleBlock 并移除内部字段
        for block_dict in page_blocks:
            del block_dict["_order"]
            simple_block = SimpleBlock(
                type=block_dict["type"],
                content=block_dict["content"],
                page=block_dict["page"],
                bbox=block_dict["bbox"],
                caption=block_dict.get("caption"),
                footnote=block_dict.get("footnote"),
            )
            all_blocks.append(simple_block)
    
    return all_blocks


def parse_response(
    api_response: Dict[str, Any],
    recognize_table: bool = True,
    pdf_size: Tuple[float, float] = DEFAULT_PDF_SIZE,
    page_sizes: Optional[Dict[int, Tuple[float, float]]] = None,
) -> Dict[str, Any]:
    """
    解析 API 响应并返回标准格式
    bbox 已转换为 PDF 坐标，可直接使用
    
    Args:
        api_response: PaddleX API 返回的完整响应
        recognize_table: 是否识别表格为 HTML
        pdf_size: PDF 页面尺寸回退默认值
        page_sizes: 每页真实 PDF 尺寸字典 {page_idx: (width, height)}
        
    Returns:
        {
            "success": bool,
            "data": List[SimpleBlock] | None,
            "error": str | None
        }
    """
    try:
        # API 响应可能直接是 result，也可能包含在 result 字段中
        result = api_response.get("result", api_response)
        blocks = convert_to_simple_blocks(result, recognize_table, pdf_size, page_sizes)
        
        logger.debug(f"解析成功，共 {len(blocks)} 个块")
        
        return {
            "success": True,
            "data": blocks,
            "error": None
        }
    except Exception as e:
        logger.error(f"解析 API 响应失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }
