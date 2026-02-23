"""
OCR 模块公共类型定义

定义所有 OCR 解析器的统一输出格式 SimpleBlock。
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from enum import Enum


class BlockType(str, Enum):
    """Block 类型枚举"""
    TITLE = "Title"
    TEXT = "Text"
    IMAGE = "Image"
    TABLE = "Table"
    FORMULA = "Formula"


@dataclass
class SimpleBlock:
    """
    标准化的文档块格式
    
    所有 OCR 解析器的统一输出格式，包含：
    - type: 块类型（Title/Text/Image/Table/Formula）
    - content: 文本内容/HTML表格/LaTeX公式（Image类型为空）
    - page: 页码（从0开始）
    - bbox: PDF点坐标 [x0, y0, x1, y1]
    - caption: 图表标题（可选）
    - footnote: 图表脚注（可选）
    """
    type: str
    content: str
    page: int
    bbox: List[float]
    caption: Optional[str] = None
    footnote: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "type": self.type,
            "content": self.content,
            "page": self.page,
            "bbox": self.bbox,
        }
        if self.caption:
            result["caption"] = self.caption
        if self.footnote:
            result["footnote"] = self.footnote
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimpleBlock":
        """从字典创建 SimpleBlock"""
        return cls(
            type=data.get("type", ""),
            content=data.get("content", ""),
            page=data.get("page", 0),
            bbox=data.get("bbox", [0, 0, 0, 0]),
            caption=data.get("caption"),
            footnote=data.get("footnote"),
        )
    
    def is_valid(self) -> bool:
        """验证 SimpleBlock 格式是否有效"""
        # 必须有类型
        if not self.type or self.type not in [t.value for t in BlockType]:
            return False
        # bbox 必须是4个数值
        if not isinstance(self.bbox, list) or len(self.bbox) != 4:
            return False
        # bbox 坐标必须有效 (x0 <= x1, y0 <= y1)
        if self.bbox[0] > self.bbox[2] or self.bbox[1] > self.bbox[3]:
            return False
        # page 必须非负
        if self.page < 0:
            return False
        return True


# ============== 类型映射常量 ==============

# 主类型映射（将各种 OCR 输出类型映射到标准类型）
MAIN_TYPE_MAP = {
    # Title 类型
    "doc_title": BlockType.TITLE.value,
    "paragraph_title": BlockType.TITLE.value,
    "section_title": BlockType.TITLE.value,
    "title": BlockType.TITLE.value,
    # Text 类型
    "text": BlockType.TEXT.value,
    "paragraph": BlockType.TEXT.value,
    "list": BlockType.TEXT.value,
    "reference": BlockType.TEXT.value,
    "abstract": BlockType.TEXT.value,
    # Image 类型
    "image": BlockType.IMAGE.value,
    "figure": BlockType.IMAGE.value,
    "chart": BlockType.IMAGE.value,
    # Table 类型
    "table": BlockType.TABLE.value,
    # Formula 类型
    "display_formula": BlockType.FORMULA.value,
    "formula": BlockType.FORMULA.value,
    "equation": BlockType.FORMULA.value,
}

# 需要跳过的类型
SKIP_TYPES = {
    "aside_text",
    "header",
    "footer",
    "header_image",
    "number",
    "formula_number",
    "inline_formula",
}

# Caption 和 Footnote 类型（需要合并到父块）
CAPTION_TYPES = {"figure_title", "table_title"}
FOOTNOTE_TYPES = {"figure_footnote", "table_footnote", "footnote"}

# Image/Table 相关的块类型
IMAGE_TYPES = {"image", "figure", "chart"}
TABLE_TYPES = {"table"}

# 标准 PDF 页面尺寸（Letter: 612x792点）
DEFAULT_PDF_SIZE = (612.0, 792.0)
