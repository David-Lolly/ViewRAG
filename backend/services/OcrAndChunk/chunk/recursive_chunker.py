"""
递归字符分块

流程：
1. 合并文本类型的 partition 为长文本
2. 表格/图片作为独立 chunk 保留
3. 递归按分隔符切分文本
4. 追踪每个 chunk 对应的原始位置

需求: 3.3, 3.5
"""

import bisect
from typing import List, Dict, Tuple, Optional
from collections import Counter

from .types import (
    Chunk,
    MergedDocument,
    STANDALONE_TYPES,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_SEPARATORS,
)


class IntervalSearcher:
    """
    区间搜索器 - 快速定位 chunk 对应的原始 partition
    
    通过二分查找快速确定文本片段覆盖了哪些原始 partition。
    """
    
    def __init__(self, indexes: List[List[int]]):
        """
        初始化区间搜索器
        
        Args:
            indexes: partition 的 [start, end] 索引列表
        """
        self.boundaries = []
        for start, end in indexes:
            self.boundaries.append(start)
            self.boundaries.append(end)
        self.n = len(self.boundaries)
    
    def _normalize_index(self, idx: int, value: int) -> int:
        """
        规范化二分查找结果的索引
        
        Args:
            idx: 二分查找返回的索引
            value: 查找的值
            
        Returns:
            规范化后的索引
        """
        if idx >= self.n:
            return self.n - 1
        if idx <= 0:
            return 0
        if self.boundaries[idx] == value:
            return idx
        if idx % 2 == 0:
            if idx > 0 and value > self.boundaries[idx - 1] and value < self.boundaries[idx]:
                return idx - 1
            return idx
        return idx
    
    def find(self, chunk_start: int, chunk_end: int) -> List[int]:
        """
        返回 chunk 覆盖的 partition 索引列表
        
        Args:
            chunk_start: chunk 在合并文本中的起始位置
            chunk_end: chunk 在合并文本中的结束位置
            
        Returns:
            覆盖的 partition 索引列表
        """
        if not self.boundaries:
            return []
            
        left_idx = bisect.bisect_left(self.boundaries, chunk_start)
        right_idx = bisect.bisect_left(self.boundaries, chunk_end)
        left_idx = self._normalize_index(left_idx, chunk_start)
        right_idx = self._normalize_index(right_idx, chunk_end)
        return list(range(left_idx // 2, right_idx // 2 + 1))


def _merge_partitions(partitions: List[Dict]) -> Tuple[MergedDocument, List[Dict]]:
    """
    合并文本 partition，提取独立的表格/图片
    
    Args:
        partitions: 解析结果列表
        
    Returns:
        (合并后的文档, 独立 chunk 列表)
    """
    doc_content = []
    indexes, bboxes, pages, types = [], [], [], []
    standalone_chunks = []
    current_pos = 0
    last_type = ""
    
    for part in partitions:
        part_type = part.get("type", "Text")
        content = part.get("content", "")
        
        # 表格/图片独立保存
        if part_type in STANDALONE_TYPES:
            standalone_chunks.append({
                "content": content,
                "chunk_type": part_type,
                "chunk_bboxes": [{"page": part.get("page", 0), "bbox": part.get("bbox", [])}],
                "caption": part.get("caption"),
                "footnote": part.get("footnote"),
            })
            continue
        
        # 跳过空内容
        if not content or not content.strip():
            continue
        
        # 根据类型添加分隔符
        if not doc_content:
            # 第一个 partition
            text = content + "\n" if part_type == "Title" else content
        elif last_type == "Title" and part_type == "Title":
            # 连续 Title
            text = "\n" + content
        elif part_type == "Title":
            # 新 Title 前加双换行
            text = "\n\n" + content
        else:
            # 普通内容加单换行
            text = "\n" + content
        
        doc_content.append(text)
        start = current_pos
        end = current_pos + len(text) - 1
        indexes.append([start, end])
        bboxes.append(part.get("bbox", []))
        pages.append(part.get("page", 0))
        types.append(part_type)
        current_pos = end + 1
        last_type = part_type
    
    return MergedDocument(
        content="".join(doc_content),
        indexes=indexes,
        bboxes=bboxes,
        pages=pages,
        types=types
    ), standalone_chunks


def _split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: List[str]
) -> List[str]:
    """
    递归字符切分
    
    按分隔符优先级递归切分文本，确保每个 chunk 不超过 chunk_size。
    
    Args:
        text: 待切分文本
        chunk_size: 目标 chunk 大小
        chunk_overlap: 重叠大小
        separators: 分隔符列表（按优先级从高到低）
        
    Returns:
        切分后的文本片段列表
    """
    
    def _split_recursive(text: str, seps: List[str]) -> List[str]:
        # 基础情况：文本已足够小或没有更多分隔符
        if not seps or len(text) <= chunk_size:
            if len(text) <= chunk_size:
                return [text] if text else []
            # 强制按字符切分（最后手段）
            chunks = []
            for i in range(0, len(text), chunk_size - chunk_overlap):
                chunk = text[i:i + chunk_size]
                if chunk:
                    chunks.append(chunk)
            return chunks
        
        sep = seps[0]
        remaining_seps = seps[1:]
        
        # 空分隔符表示按字符切分
        if sep == "":
            parts = [text[i:i+1] for i in range(len(text))]
        else:
            parts = text.split(sep)
        
        chunks = []
        current_chunk = ""
        
        for i, part in enumerate(parts):
            # 重新添加分隔符（除了最后一个部分）
            part_with_sep = part + sep if sep and i < len(parts) - 1 else part
            test_chunk = current_chunk + part_with_sep
            
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                # 当前 chunk 已满，输出它
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果单个部分超过 chunk_size，递归切分
                if len(part_with_sep) > chunk_size:
                    chunks.extend(_split_recursive(part_with_sep, remaining_seps))
                    current_chunk = ""
                else:
                    current_chunk = part_with_sep
        
        # 输出最后一个 chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    return _split_recursive(text, separators)


def chunk_by_recursive(
    partitions: List[Dict],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    separators: Optional[List[str]] = None,
    source: str = ""
) -> List[Chunk]:
    """
    递归字符分块
    
    流程：
    1. 合并文本类型 partition 为长文本
    2. 表格/图片作为独立 chunk 保留
    3. 按分隔符优先级递归切分文本
    4. 追踪每个 chunk 对应的原始 bbox 位置
    
    Args:
        partitions: 解析结果列表，每项包含 type, content, page, bbox
        chunk_size: 目标 chunk 大小
        chunk_overlap: 重叠大小
        separators: 分隔符列表（按优先级从高到低）
        source: 来源文件名
    
    Returns:
        分块结果列表
    """
    if separators is None:
        separators = DEFAULT_SEPARATORS
    
    # 合并文本，提取独立 chunk
    merged_doc, standalone_chunks = _merge_partitions(partitions)
    
    # 如果没有文本内容，只返回独立 chunk
    if not merged_doc.content:
        chunks = []
        for idx, standalone in enumerate(standalone_chunks):
            chunks.append(Chunk(
                content=standalone["content"],
                chunk_index=idx,
                chunk_type=standalone["chunk_type"],
                chunk_bboxes=standalone["chunk_bboxes"],
                source=source,
                caption=standalone.get("caption"),
                footnote=standalone.get("footnote"),
            ))
        return chunks
    
    # 切分文本
    split_texts = _split_text(merged_doc.content, chunk_size, chunk_overlap, separators)
    
    # 创建区间搜索器
    searcher = IntervalSearcher(merged_doc.indexes)
    
    chunks = []
    chunk_index = 0
    search_start = 0
    
    for chunk_text in split_texts:
        # 在合并文本中定位 chunk 位置
        pos = merged_doc.content.find(chunk_text, search_start)
        if pos == -1:
            # 回退到从头搜索
            pos = merged_doc.content.find(chunk_text)
        if pos == -1:
            # 找不到则跳过
            continue
        
        chunk_start = pos
        chunk_end = pos + len(chunk_text) - 1
        search_start = pos + 1
        
        # 跳过开头和末尾的换行符，避免因分隔符导致错误关联相邻 partition
        leading_newlines = len(chunk_text) - len(chunk_text.lstrip('\n'))
        trailing_newlines = len(chunk_text) - len(chunk_text.rstrip('\n'))
        adjusted_start = chunk_start + leading_newlines
        adjusted_end = chunk_end - trailing_newlines
        
        # 确保调整后的范围有效
        if adjusted_start > adjusted_end:
            adjusted_start = chunk_start
            adjusted_end = chunk_end
        
        # 查找覆盖的 partition 索引
        partition_indices = searcher.find(adjusted_start, adjusted_end)
        
        # 收集 bbox 信息和类型统计
        chunk_bboxes = []
        type_counts = Counter()
        
        for idx in partition_indices:
            if idx < len(merged_doc.bboxes):
                chunk_bboxes.append({
                    "page": merged_doc.pages[idx],
                    "bbox": merged_doc.bboxes[idx]
                })
                type_counts[merged_doc.types[idx]] += 1
        
        # 确定主要类型（出现次数最多的类型）
        chunk_type = type_counts.most_common(1)[0][0] if type_counts else "Text"
        
        chunks.append(Chunk(
            content=chunk_text,
            chunk_index=chunk_index,
            chunk_type=chunk_type,
            chunk_bboxes=chunk_bboxes,
            source=source
        ))
        chunk_index += 1
    
    # 添加独立 chunk（表格/图片）
    for standalone in standalone_chunks:
        chunks.append(Chunk(
            content=standalone["content"],
            chunk_index=chunk_index,
            chunk_type=standalone["chunk_type"],
            chunk_bboxes=standalone["chunk_bboxes"],
            source=source,
            caption=standalone.get("caption"),
            footnote=standalone.get("footnote"),
        ))
        chunk_index += 1
    
    return chunks
