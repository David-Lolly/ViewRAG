"""SSE 流式响应事件工具函数

支持的事件类型：
- thinking_chunk: 推理模型思考过程片段
- thinking_done: 思考阶段结束
- references: 所有引用 Chunk 详情
- retrieved_documents: 召回的文档列表
- answer_chunk: LLM 输出的文本片段
- done: 流结束标志
- error: 错误信息
- tool_start: Agent 开始调用工具（含工具名称和查询文本）
- tool_result: Agent 工具执行完成（含找到的片段数量）
"""

import json
from typing import Any, List, Optional


def sse_event(event_type: str, data: Any) -> str:
    """生成 SSE 事件 JSON 字符串

    Args:
        event_type: 事件类型，支持 thinking_chunk / thinking_done / references / retrieved_documents / answer_chunk / done / error / tool_start / tool_result
        data: 事件数据
            - thinking_chunk: str，思考过程片段
            - thinking_done: None
            - references: List[dict]，ReferenceItem 列表
            - retrieved_documents: List[dict]，文档列表
            - answer_chunk: str，LLM 输出片段
            - done: None
            - error: str，错误描述
            - tool_start: dict，{"tool": str, "query": str}
            - tool_result: dict，{"tool": str, "chunks_found": int}

    Returns:
        JSON 字符串 + 换行符，格式为 {"type": "<event_type>", "data": <data>}
    """
    return json.dumps({"type": event_type, "data": data}, ensure_ascii=False) + "\n"
