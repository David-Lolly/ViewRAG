"""ContextBuilder - 将检索结果格式化为 LLM 上下文并生成引用数据"""

import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class ContextBuilder:
    """构建 LLM 上下文和引用数据

    职责：
    - 为每个 Chunk 分配从 1 开始的连续引用编号
    - 相同 chunk_id 去重，复用同一编号
    - 按 chunk_type 格式化上下文文本（TEXT / IMAGE / TABLE）
    - 生成前端所需的 references 数组
    """

    def build_context_and_references(
        self, chunks: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        输入: 检索结果列表（来自 ChunkCRUD.search_chunks）
        输出: (context_text, references)

        Args:
            chunks: 检索结果列表，每个元素包含:
                chunk_id, chunk_type, content, retrieval_text,
                metadata, score, doc_id, kb_id, session_id, file_name

        Returns:
            (context_text, references) 元组
        """
        references: List[Dict[str, Any]] = []
        context_parts: List[str] = []
        seen_chunks: Dict[str, int] = {}  # chunk_id -> ref_id
        ref_counter = 0
        image_counter = 0

        for chunk in chunks:
            chunk_id = chunk["chunk_id"]

            # 去重：同一 chunk_id 只分配一次编号
            if chunk_id in seen_chunks:
                continue

            ref_counter += 1
            chunk_type = chunk["chunk_type"]
            bboxes = chunk.get("metadata", {}).get("bboxes", [])
            page_range = self.get_page_range(bboxes)

            # 记录图片序号
            image_alias: Optional[str] = None
            if chunk_type == "IMAGE":
                image_counter += 1
                image_alias = f"图片{image_counter}"

            # 格式化上下文文本
            context_line = self.format_chunk_for_context(
                ref_counter, chunk_type, chunk, page_range, image_alias
            )
            context_parts.append(context_line)

            # 构建 reference item
            ref_item = {
                "ref_id": ref_counter,
                "chunk_id": chunk_id,
                "chunk_type": chunk_type,
                "content": chunk["content"],
                "retrieval_text": chunk.get("retrieval_text", ""),
                "doc_id": chunk["doc_id"],
                "file_name": chunk["file_name"],
                "chunk_bboxes": bboxes,
                "image_alias": image_alias,
                "image_url": f"/api/images/{chunk['content']}" if chunk_type == "IMAGE" and chunk["content"] else None,
            }
            references.append(ref_item)
            seen_chunks[chunk_id] = ref_counter

        if not context_parts:
            return "", references

        context_text = "参考资料：\n\n" + "\n\n".join(context_parts)
        return context_text, references

    def format_chunk_for_context(
        self,
        ref_id: int,
        chunk_type: str,
        chunk: Dict[str, Any],
        page_range: str,
        image_alias: Optional[str] = None,
    ) -> str:
        """根据 chunk_type 格式化单个 Chunk 的上下文文本

        - TEXT:  [N] {file_name} P{pages}\\n{content}
        - IMAGE: [图片N] {file_name} P{page}\\n{retrieval_text}
        - TABLE: [表格N] {file_name} P{pages}\\n{retrieval_text}
        """
        file_name = chunk["file_name"]
        page_suffix = f" {page_range}" if page_range else ""

        if chunk_type == "TEXT":
            prefix = f"[{ref_id}]"
            body = chunk["content"]
        elif chunk_type == "IMAGE":
            prefix = f"[{image_alias}]" if image_alias else f"[图片{ref_id}]"
            body = chunk.get("retrieval_text", "")
        elif chunk_type == "TABLE":
            prefix = f"[表格{ref_id}]"
            body = chunk.get("retrieval_text", "")
        else:
            prefix = f"[{ref_id}]"
            body = chunk["content"]

        return f"{prefix} {file_name}{page_suffix}\n{body}"

    @staticmethod
    def get_page_range(bboxes: List[Dict[str, Any]]) -> str:
        """将 bboxes 数组转换为页码范围字符串

        - 空数组 → ""
        - 单页   → "P3"
        - 多页   → "P3-P5"
        """
        if not bboxes:
            return ""

        pages = sorted(set(b["page"] for b in bboxes))

        if len(pages) == 1:
            return f"P{pages[0]}"

        return f"P{pages[0]}-P{pages[-1]}"
