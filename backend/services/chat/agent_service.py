"""AgentService — 基于 OpenAI Function Calling 的 Agentic RAG 编排服务

职责：
- 判断是否注册检索工具（根据 session 文档状态或 kb_id）
- 执行 Agent 主循环：工具调用阶段（非流式）→ 最终回答阶段（流式）
- 多轮检索结果合并去重
- 通过 SSE 回调通知前端工具执行状态
"""

import json
import logging
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

from crud.document_crud import DocumentCRUD
from models.models import DocumentStatus
from services.chat.context_builder import ContextBuilder
from services.chat.prompts import REFERENCE_SYSTEM_PROMPT
from services.chat.sse_handler import sse_event
from services.chat.tools import SEARCH_DOCUMENTS_TOOL
from services.chat_service import ChatService
from services.llm_service import LLMService
from services.retrieval_service import UnifiedRetrievalService
import crud.database as db

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3


def deduplicate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按 chunk_id 去重，保留首次出现的结果（分数更高）"""
    seen = set()
    result = []
    for chunk in chunks:
        cid = chunk["chunk_id"]
        if cid not in seen:
            seen.add(cid)
            result.append(chunk)
    return result


class AgentService:
    """Agentic RAG 编排服务"""

    def __init__(
        self,
        session_id: str,
        kb_id: Optional[str] = None,
    ):
        self.session_id = session_id
        self.kb_id = kb_id
        self.has_tools = False
        self.search_kwargs: Dict[str, Any] = {}
        # 多轮检索收集的所有 chunks
        self._all_chunks: List[Dict[str, Any]] = []

    async def resolve_search_scope(self) -> Optional[str]:
        """判断检索范围，决定是否注册工具。

        Returns:
            early_message: 如果文档正在处理中，返回提示消息；否则返回 None
        """
        if self.kb_id:
            self.has_tools = True
            self.search_kwargs = {"kb_id": self.kb_id}
            return None

        if self.session_id:
            with db.SessionLocal() as db_session:
                docs = DocumentCRUD.get_documents_by_session_id(
                    db_session, self.session_id
                )

            completed = [d for d in docs if d.status == DocumentStatus.COMPLETED]
            pending = [
                d
                for d in docs
                if d.status not in (DocumentStatus.COMPLETED, DocumentStatus.FAILED)
            ]

            if pending and not completed:
                return "文档正在处理中，请稍后再试..."

            if completed:
                self.has_tools = True
                self.search_kwargs = {"session_id": self.session_id}

        return None

    async def run(
        self,
        messages: List[dict],
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Agent 主循环，yield SSE 事件字符串。

        流程：
        1. 如果 has_tools=False，直接流式输出 LLM 回答
        2. 如果 has_tools=True，进入工具调用循环（最多 MAX_TOOL_ROUNDS 轮）
           - 非流式调用 LLM，判断是否需要工具
           - 执行工具，收集 chunks，发送 tool_start/tool_result SSE
           - 循环结束后，用 ContextBuilder 构建上下文，流式输出最终回答

        Args:
            messages: 已构建好的消息列表（含 system prompt）
            model_name: 模型名称

        Yields:
            SSE 事件 JSON 字符串
        """
        if not self.has_tools:
            # 无工具模式：直接流式输出
            async for event in self._stream_final_answer(messages, model_name):
                yield event
            return

        # 有工具模式：进入 Agent 循环
        tools = [SEARCH_DOCUMENTS_TOOL]
        working_messages = list(messages)  # 工作副本，包含中间 tool messages

        for round_idx in range(MAX_TOOL_ROUNDS):
            logger.info(f"[Agent] 工具调用轮次 {round_idx + 1}/{MAX_TOOL_ROUNDS}")

            try:
                result = LLMService.call_with_tools(
                    working_messages, tools, model_name=model_name
                )
            except RuntimeError as e:
                yield sse_event("error", str(e))
                return

            if result["finish_reason"] == "stop":
                # LLM 决定不调用工具，直接回答
                break

            # 处理工具调用
            if result["tool_calls"]:
                # 追加 assistant 的 tool_call 消息
                assistant_msg = {
                    "role": "assistant",
                    "content": result["content"],
                    "tool_calls": result["tool_calls"],
                }
                working_messages.append(assistant_msg)

                for tc in result["tool_calls"]:
                    func_name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {"query": tc["function"]["arguments"]}

                    if func_name == "search_documents":
                        query = args.get("query", "")
                        top_k = args.get("top_k", 5)

                        # 发送 tool_start 事件
                        yield sse_event(
                            "tool_start",
                            {"tool": func_name, "query": query},
                        )

                        # 执行检索
                        chunks = await self._execute_search(query, top_k)
                        self._all_chunks.extend(chunks)

                        # 发送 tool_result 事件
                        yield sse_event(
                            "tool_result",
                            {"tool": func_name, "chunks_found": len(chunks)},
                        )

                        # 构建 tool message 返回给 LLM
                        tool_content = self._format_tool_result(chunks)
                        working_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": tool_content,
                            }
                        )
                    else:
                        # 未知工具
                        working_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": json.dumps(
                                    {"error": f"未知工具: {func_name}"},
                                    ensure_ascii=False,
                                ),
                            }
                        )
        else:
            # 达到最大轮次，强制生成最终回答
            logger.warning(
                f"[Agent] 达到最大工具调用轮次 {MAX_TOOL_ROUNDS}，强制生成回答"
            )

        # 合并去重所有检索结果，构建最终上下文
        unique_chunks = deduplicate_chunks(self._all_chunks)

        if unique_chunks:
            ctx_builder = ContextBuilder()
            rag_context, references = ctx_builder.build_context_and_references(
                unique_chunks
            )

            # 发送 references 事件
            if references:
                yield sse_event("references", references)

                # 推送 retrieved_documents 事件：文档去重列表
                doc_ids_with_none = [ref.get("doc_id") for ref in references]
                unique_doc_ids = list(set(d for d in doc_ids_with_none if d is not None))
                if unique_doc_ids:
                    with db.SessionLocal() as db_session:
                        doc_dict = DocumentCRUD.get_documents_by_ids(db_session, unique_doc_ids)
                        retrieved_documents = [
                            {
                                "doc_id": doc_id,
                                "file_name": doc.file_name,
                                "summary": doc.summary or ""
                            }
                            for doc_id, doc in doc_dict.items()
                        ]
                        yield sse_event("retrieved_documents", retrieved_documents)
                        logger.info(f"[Agent] 发送 retrieved_documents 事件: {len(retrieved_documents)} 篇文档")

            # 重建最终消息：用原始 messages + RAG 上下文替换 system prompt
            final_messages = self._build_final_messages(messages, rag_context)
        else:
            final_messages = list(messages)

        # 流式输出最终回答
        async for event in self._stream_final_answer(final_messages, model_name):
            yield event

    async def _execute_search(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """执行检索工具，复用 UnifiedRetrievalService"""
        retrieval_service = UnifiedRetrievalService()
        try:
            with db.SessionLocal() as db_session:
                chunks = await retrieval_service.search(
                    query=query,
                    db_session=db_session,
                    top_k=top_k,
                    **self.search_kwargs,
                )
                return chunks
        except Exception as e:
            logger.error(f"[Agent] 检索失败: {e}", exc_info=True)
            return []
        finally:
            retrieval_service.close()

    @staticmethod
    def _format_tool_result(chunks: List[Dict[str, Any]]) -> str:
        """将检索结果格式化为 tool message 的 content"""
        if not chunks:
            return json.dumps(
                {"message": "未找到相关内容", "chunks": []}, ensure_ascii=False
            )

        summaries = []
        for i, chunk in enumerate(chunks, 1):
            summaries.append(
                {
                    "index": i,
                    "file_name": chunk.get("file_name", ""),
                    "chunk_type": chunk.get("chunk_type", "TEXT"),
                    "content": chunk.get("content", "")[:500],
                    "score": chunk.get("score", 0),
                }
            )

        return json.dumps(
            {"message": f"找到 {len(chunks)} 个相关片段", "chunks": summaries},
            ensure_ascii=False,
        )

    @staticmethod
    def _build_final_messages(
        original_messages: List[dict], rag_context: str
    ) -> List[dict]:
        """用 RAG 上下文重建最终消息列表，替换 system prompt"""
        final_messages = []
        system_replaced = False

        for msg in original_messages:
            if msg.get("role") == "system" and not system_replaced:
                final_messages.append(
                    {
                        "role": "system",
                        "content": REFERENCE_SYSTEM_PROMPT + "\n\n" + rag_context,
                    }
                )
                system_replaced = True
            else:
                final_messages.append(msg)

        # 如果原始消息没有 system 消息，在开头插入
        if not system_replaced:
            final_messages.insert(
                0,
                {
                    "role": "system",
                    "content": REFERENCE_SYSTEM_PROMPT + "\n\n" + rag_context,
                },
            )

        return final_messages

    async def _stream_final_answer(
        self,
        messages: List[dict],
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """流式输出 LLM 最终回答，直接透传 SSE 事件"""
        assistant_text = ""

        for chunk in LLMService.stream_chat(messages, model_name=model_name):
            chunk_str = chunk.decode("utf-8", errors="ignore")
            if not chunk_str:
                continue

            # LLMService 已经返回 SSE 格式的事件，直接透传
            yield chunk_str
            
            # 收集 answer_chunk 用于存储
            try:
                chunk_data = json.loads(chunk_str.strip())
                if chunk_data.get("type") == "answer_chunk":
                    assistant_text += chunk_data.get("data", "")
            except (json.JSONDecodeError, AttributeError):
                pass

        yield sse_event("done", None)

        # 将最终文本存储到实例属性，供路由层读取
        self.final_answer_text = assistant_text
