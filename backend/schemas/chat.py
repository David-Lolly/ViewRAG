"""RAG 问答引用相关的 Pydantic Schema"""

from typing import List, Optional

from pydantic import BaseModel


class ChunkBbox(BaseModel):
    """Chunk 在 PDF 页面中的位置信息"""

    page: int
    bbox: List[float]  # [x0, y0, x1, y1]


class ReferenceItem(BaseModel):
    """SSE references 事件中的单个引用项"""

    ref_id: int
    chunk_id: str
    chunk_type: str  # TEXT / IMAGE / TABLE
    content: str
    retrieval_text: str
    doc_id: str
    file_name: str
    chunk_bboxes: List[ChunkBbox]
    image_alias: Optional[str] = None
    image_url: Optional[str] = None
