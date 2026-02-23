"""
Chunk 模块类型定义和常量配置

定义分块结果的数据结构和分块配置常量。
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class Chunk:
    """
    分块结果
    
    Attributes:
        content: 文本内容
        chunk_index: 分块序号
        chunk_type: 主要类型 (Title, Text, Table, Image, Formula)
        chunk_bboxes: 位置信息列表 [{page: int, bbox: [x0, y0, x1, y1]}, ...]
        source: 来源文件名
        caption: 图表标题（可选）
        footnote: 图表脚注（可选）
    """
    content: str
    chunk_index: int
    chunk_type: str
    chunk_bboxes: List[Dict]
    source: str = ""
    caption: Optional[str] = None
    footnote: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        result = {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type,
            "chunk_bboxes": self.chunk_bboxes,
            "source": self.source,
        }
        if self.caption:
            result["caption"] = self.caption
        if self.footnote:
            result["footnote"] = self.footnote
        return result


@dataclass
class MergedDocument:
    """
    合并后的文档（用于递归分块）
    
    Attributes:
        content: 合并后的完整文本
        indexes: 每个 partition 在 content 中的 [start, end] 位置
        bboxes: 每个 partition 的 bbox 坐标
        pages: 每个 partition 的页码
        types: 每个 partition 的类型
    """
    content: str
    indexes: List[List[int]]
    bboxes: List[List[float]]
    pages: List[int]
    types: List[str]


# ============== 分块配置常量 ==============

# Block 分块的合并阈值
DEFAULT_MAX_CHUNK_SIZE = 1024

# 递归分块的目标大小
DEFAULT_CHUNK_SIZE = 500

# 递归分块的重叠大小
DEFAULT_CHUNK_OVERLAP = 50

# 递归分块的分隔符优先级（从高到低）
DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "。", "；", "，", " ", ""]

# 独立保存的类型（不参与合并/切分）
STANDALONE_TYPES = {"Table", "Image"}


# ============== 可视化颜色配置 ==============

CHUNK_COLORS = {
    "Title": (1, 0, 0),        # 红色
    "Text": (0, 0.6, 0),       # 绿色
    "Image": (0, 0.4, 1),      # 蓝色
    "Table": (1, 0.5, 0),      # 橙色
    "Formula": (0.6, 0, 0.8),  # 紫色
    "Figure": (0, 0.4, 1),     # 蓝色
}
