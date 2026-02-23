"""
基于 Block 的文档分块

核心原则：
1. Block 是最小单位，不可切分
2. 只能合并，不能切分
3. Title 必须与下一个 block 合并
4. 表格/图片独立保存，不参与合并

需求: 3.1, 3.2
"""

from typing import List, Dict

from .types import Chunk, STANDALONE_TYPES, DEFAULT_MAX_CHUNK_SIZE


def chunk_by_block(
    partitions: List[Dict],
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    source: str = ""
) -> List[Chunk]:
    """
    基于 Block 的合并策略
    
    规则：
    1. Block 不可切分，只能合并
    2. Title 必须与下一个 block 合并
    3. 两个 block 合并后 < max_chunk_size 才允许合并
    4. 表格/图片独立保存
    
    Args:
        partitions: 解析结果列表，每项包含 type, content, page, bbox
        max_chunk_size: 合并阈值
        source: 来源文件名
    
    Returns:
        分块结果列表
    """
    chunks = []
    chunk_index = 0
    
    # 当前正在构建的 chunk
    current_content = ""
    current_bboxes = []
    current_types = []
    current_caption = None
    current_footnote = None
    pending_title = None
    
    def flush_current():
        """输出当前 chunk"""
        nonlocal chunk_index, current_content, current_bboxes, current_types
        nonlocal current_caption, current_footnote
        
        if not current_content.strip():
            return
        
        # 确定主要类型：如果包含 Title 则为 Title，否则取第一个类型
        main_type = "Title" if "Title" in current_types else (
            current_types[0] if current_types else "Text"
        )
        
        chunks.append(Chunk(
            content=current_content.strip(),
            chunk_index=chunk_index,
            chunk_type=main_type,
            chunk_bboxes=current_bboxes.copy(),
            source=source,
            caption=current_caption,
            footnote=current_footnote
        ))
        chunk_index += 1
        current_content = ""
        current_bboxes = []
        current_types = []
        current_caption = None
        current_footnote = None
    
    def add_standalone(part: Dict, part_type: str):
        """添加独立 chunk（表格/图片）"""
        nonlocal chunk_index
        chunks.append(Chunk(
            content=part.get("content", ""),
            chunk_index=chunk_index,
            chunk_type=part_type,
            chunk_bboxes=[{"page": part.get("page", 0), "bbox": part.get("bbox", [])}],
            source=source,
            caption=part.get("caption"),
            footnote=part.get("footnote")
        ))
        chunk_index += 1
    
    for part in partitions:
        part_type = part.get("type", "Text")
        content = part.get("content", "")
        
        # 表格/图片独立保存（即使 content 为空也要保留）
        if part_type in STANDALONE_TYPES:
            flush_current()
            add_standalone(part, part_type)
            pending_title = None
            continue
        
        # 跳过空内容（仅对非独立类型）
        if not content or not content.strip():
            continue
        
        # Title：等待与下一个 block 合并
        if part_type == "Title":
            if current_content:
                flush_current()
            pending_title = part
            continue
        
        # 处理普通 block
        block_content = content
        block_bbox = {"page": part.get("page", 0), "bbox": part.get("bbox", [])}
        block_type = part_type
        
        # 如果有待合并的 Title
        if pending_title:
            title_content = pending_title.get("content", "")
            title_bbox = {
                "page": pending_title.get("page", 0),
                "bbox": pending_title.get("bbox", [])
            }
            combined_content = title_content + "\n\n" + block_content
            combined_bboxes = [title_bbox, block_bbox]
            combined_types = ["Title", block_type]
            
            if current_content:
                test_len = len(current_content) + 1 + len(combined_content)
                if test_len < max_chunk_size:
                    current_content += "\n" + combined_content
                    current_bboxes.extend(combined_bboxes)
                    current_types.extend(combined_types)
                else:
                    flush_current()
                    current_content = combined_content
                    current_bboxes = combined_bboxes
                    current_types = combined_types
            else:
                current_content = combined_content
                current_bboxes = combined_bboxes
                current_types = combined_types
            
            pending_title = None
            continue
        
        # 普通 block 合并逻辑
        if current_content:
            test_len = len(current_content) + 1 + len(block_content)
            if test_len < max_chunk_size:
                current_content += "\n" + block_content
                current_bboxes.append(block_bbox)
                current_types.append(block_type)
            else:
                flush_current()
                current_content = block_content
                current_bboxes = [block_bbox]
                current_types = [block_type]
        else:
            current_content = block_content
            current_bboxes = [block_bbox]
            current_types = [block_type]
    
    # 处理末尾的 pending_title
    if pending_title:
        if current_content:
            title_content = pending_title.get("content", "")
            title_bbox = {
                "page": pending_title.get("page", 0),
                "bbox": pending_title.get("bbox", [])
            }
            current_content = title_content + "\n\n" + current_content
            current_bboxes.insert(0, title_bbox)
            current_types.insert(0, "Title")
        else:
            current_content = pending_title.get("content", "")
            current_bboxes = [{
                "page": pending_title.get("page", 0),
                "bbox": pending_title.get("bbox", [])
            }]
            current_types = ["Title"]
    
    flush_current()
    return chunks
