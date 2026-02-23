"""
PaddleOCR 类型定义和常量配置

定义 PaddleX API 相关的配置项和类型映射。
"""

import os
from typing import Tuple

# ============== API 配置项 ==============
# 可通过环境变量覆盖

# PaddleX API 地址
API_URL = os.getenv(
    "PADDLE_API_URL",
    ""
)

# PaddleX API Token
API_TOKEN = os.getenv(
    "PADDLE_API_TOKEN",
    ""
)

# 默认请求超时时间（秒）
DEFAULT_TIMEOUT = 300

# ============== PDF 页面尺寸 ==============

# 标准 PDF 页面尺寸（Letter: 612x792 点）
DEFAULT_PDF_SIZE: Tuple[float, float] = (612.0, 792.0)

# A4 页面尺寸（595x842 点）
A4_PDF_SIZE: Tuple[float, float] = (595.0, 842.0)

# ============== 类型映射 ==============

# 主类型映射（将 PaddleX API 返回的类型映射到标准类型）
MAIN_TYPE_MAP = {
    # Title 类型
    "doc_title": "Title",
    "paragraph_title": "Title",
    "section_title": "Title",
    "title": "Title",
    # Text 类型
    "text": "Text",
    "paragraph": "Text",
    "list": "Text",
    "reference": "Text",
    "abstract": "Text",
    # Image 类型
    "image": "Image",
    "figure": "Image",
    "chart": "Image",
    # Table 类型
    "table": "Table",
    # Formula 类型
    "display_formula": "Formula",
    "formula": "Formula",
    "equation": "Formula",
}

# 需要跳过的类型（不输出到结果中）
SKIP_TYPES = {
    "aside_text",
    "header",
    "footer",
    "header_image",
    "number",
    "formula_number",
    "inline_formula",
}

# Caption 类型（需要合并到父块的标题）
CAPTION_TYPES = {"figure_title", "table_title"}

# Footnote 类型（需要合并到父块的脚注）
FOOTNOTE_TYPES = {"figure_footnote", "table_footnote", "footnote"}

# Image 相关的块类型
IMAGE_TYPES = {"image", "figure", "chart"}

# Table 相关的块类型
TABLE_TYPES = {"table"}

# ============== 可视化颜色（调试用） ==============

TYPE_COLORS = {
    "Title": (1, 0, 0),        # 红色
    "Text": (0, 0.6, 0),       # 绿色
    "Image": (0, 0.4, 1),      # 蓝色
    "Table": (1, 0.5, 0),      # 橙色
    "Formula": (0.6, 0, 0.8),  # 紫色
}
