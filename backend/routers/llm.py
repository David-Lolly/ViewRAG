import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from schemas.request import SearchRequest, RegenerateRequest
from services.llm_service import LLMService
from services.chat_service import ChatService
from services.session import SessionService
from services.storage import minio_storage
from services.chat.agent_service import AgentService
from services.chat.context_builder import ContextBuilder
from services.chat.query_rewrite import QueryRewriteService
from services.chat.sse_handler import sse_event
from services.chat.prompts import REFERENCE_SYSTEM_PROMPT
from services.retrieval_service import UnifiedRetrievalService
from crud.config_manager import config
from crud.document_crud import DocumentCRUD
from models.models import DocumentStatus
import crud.database as db

router = APIRouter()
logger = logging.getLogger(__name__)


async def _resolve_rag_context(req: SearchRequest, history_messages: list = None):
    """
    判断是否需要 RAG 检索，并返回上下文和引用数据。

    Args:
        req: 搜索请求
        history_messages: 历史消息列表，用于问题重写

    Returns:
        (rag_context, references, early_sse_message)
        - rag_context: str, RAG 上下文文本（空字符串表示无 RAG）
        - references: list, 引用数据列表
        - early_sse_message: str | None, 需要提前发送的 SSE 消息（如文档处理中提示）
    """
    rag_context = ""
    references = []
    early_sse_message = None

    user_query = req.query or ""
    rewritten_query = user_query  # 默认不重写

    # 判断是否需要 RAG 检索，只在需要检索时才进行问题重写
    need_retrieval = False

    if req.kb_id:
        # 知识库问答：需要检索
        need_retrieval = True
    elif req.session_id and req.has_docs:
        # 前端标记有文档时才查数据库，避免纯聊天场景的无效查询
        with db.SessionLocal() as db_session:
            docs = DocumentCRUD.get_documents_by_session_id(db_session, req.session_id)

        completed_docs = [d for d in docs if d.status == DocumentStatus.COMPLETED]
        pending_docs = [
            d for d in docs
            if d.status not in (DocumentStatus.COMPLETED, DocumentStatus.FAILED)
        ]

        if pending_docs and not completed_docs:
            # 有文档在处理中，无已完成文档 → 提示等待
            early_sse_message = sse_event("answer_chunk", "文档正在处理中，请稍后再试...")
            return rag_context, references, early_sse_message

        if completed_docs:
            need_retrieval = True

    if need_retrieval:
        # 仅在需要检索时才进行问题重写（节省一次 LLM 调用）
        if history_messages:
            rewritten_query = QueryRewriteService.rewrite(user_query, history_messages)

        if req.kb_id:
            retrieval_service = UnifiedRetrievalService()
            try:
                with db.SessionLocal() as db_session:
                    chunks = await retrieval_service.search(
                        query=rewritten_query,
                        db_session=db_session,
                        kb_id=req.kb_id,
                    )
                    if chunks:
                        ctx_builder = ContextBuilder()
                        rag_context, references = ctx_builder.build_context_and_references(chunks)
            finally:
                retrieval_service.close()
        else:
            # 会话文档检索
            retrieval_service = UnifiedRetrievalService()
            try:
                with db.SessionLocal() as db_session:
                    chunks = await retrieval_service.search(
                        query=rewritten_query,
                        db_session=db_session,
                        session_id=req.session_id,
                    )
                    if chunks:
                        ctx_builder = ContextBuilder()
                        rag_context, references = ctx_builder.build_context_and_references(chunks)
            finally:
                retrieval_service.close()

    if need_retrieval:
        logger.info(f"RAG检索结果 | 原问题={user_query} | 重写后={rewritten_query} | rag_context长度={len(rag_context)} | references数量={len(references)}")
        for i, ref in enumerate(references):
            logger.info(
                f"Reference[{i}]: ref_id={ref.get('ref_id')} | chunk_id={ref.get('chunk_id')} | "
                f"type={ref.get('chunk_type')} | doc_id={ref.get('doc_id')} | "
                f"file_name={ref.get('file_name')} | image_alias={ref.get('image_alias')} | "
                f"image_url={ref.get('image_url')} | "
                f"content={ref.get('content', '')[:100]}... | "
                f"retrieval_text={ref.get('retrieval_text', '')[:100]}... | "
                f"chunk_bboxes={ref.get('chunk_bboxes')}"
            )
    return rag_context, references, early_sse_message


@router.post("/chat/send")
async def chat_send(req: SearchRequest):
    """聊天发送接口（集成 RAG 检索流程）"""
    if not config.is_configured():
        async def not_configured_stream():
            yield await LLMService.stream_json("error", "系统未配置。请先访问配置页面完成设置。")
        return StreamingResponse(not_configured_stream(), media_type="application/x-json-stream")

    session_id = req.session_id
    if not session_id:
        logger.error("chat_send 调用时缺少 session_id")
        async def error_stream():
            yield await LLMService.stream_json("error", "会话ID丢失，无法处理请求。请尝试刷新页面或新建会话。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")

    logger.info(f"开始为会话 {session_id} 生成直接回复 | kb_id={req.kb_id}")

    # 从数据库获取包含图片（如有）的完整历史记录
    history_data = SessionService.get_and_clean_history(session_id)
    logger.info(f"处理后的历史记录数量: {len(history_data.get('messages', []))}, 包含图片: {history_data.get('has_images', False)}")

    # 获取模型配置，用于兼容性检查和消息构建
    has_images = history_data.get("has_images", False)
    model_name = req.selected_model
    chat_model_config = None
    if model_name:
        chat_model_config = config.get_chat_model_by_name(model_name)
    if not chat_model_config:
        chat_model_config = config.get_default_chat_model()
    model_type = (chat_model_config or {}).get("type", "text-model")
    display_model_name = (chat_model_config or {}).get("name", model_name or "默认模型")

    # 兼容性检查
    compat_error = ChatService.check_model_compatibility(has_images, model_type, display_model_name)
    if compat_error:
        async def compat_error_stream():
            yield await LLMService.stream_json("error", compat_error)
        return StreamingResponse(compat_error_stream(), media_type="application/x-json-stream")

    # RAG 检索（传入历史消息用于问题重写）
    rag_context, references, early_sse_message = await _resolve_rag_context(
        req, history_messages=history_data.get("messages", [])
    )

    # 构建系统提示词（有 RAG 上下文时注入引用规则）
    if rag_context:
        system_prompt = REFERENCE_SYSTEM_PROMPT + "\n\n" + rag_context
    else:
        system_prompt = ChatService.get_default_system_prompt()

    # 构建消息
    messages = ChatService.build_messages(history_data, system_prompt=system_prompt, model_type=model_type)

    async def process_request():
        retrieved_documents = []  # 用于持久化存储
        thinking_content = ""  # 累加思考过程
        try:
            # 如果有提前发送的消息（如文档处理中提示），直接发送并结束
            if early_sse_message:
                yield early_sse_message
                # 存储提示消息
                final_db_content = {"text": "文档正在处理中，请稍后再试...", "references": [], "retrieved_documents": []}
                SessionService.add_assistant_message(session_id, json.dumps(final_db_content, ensure_ascii=False))
                return

            # 推送 references 事件（如果有引用）
            if references:
                yield sse_event("references", references)
                
                # 推送 retrieved_documents 事件：文档去重列表
                doc_ids_with_none = [ref.get("doc_id") for ref in references]
                unique_doc_ids = list(set(d for d in doc_ids_with_none if d is not None))  # 过滤None并去重
                if unique_doc_ids:
                    with db.SessionLocal() as db_session:
                        doc_dict = DocumentCRUD.get_documents_by_ids(db_session, unique_doc_ids)
                        retrieved_documents = [
                            {
                                "doc_id": doc_id,
                                "file_name": doc.file_name,
                                "summary": doc.summary or ""  # 空摘要返回空字符串
                            }
                            for doc_id, doc in doc_dict.items()
                        ]
                        yield sse_event("retrieved_documents", retrieved_documents)
                        logger.info(f"发送 retrieved_documents 事件: {len(retrieved_documents)} 篇文档")

            assistant_response_text = ""
            for chunk in LLMService.stream_chat(messages, model_name=model_name):
                chunk_str = chunk.decode("utf-8", errors="ignore")
                if not chunk_str:
                    continue

                # 解析 SSE 事件
                try:
                    chunk_data = json.loads(chunk_str.strip())
                    event_type = chunk_data.get("type")
                    event_data = chunk_data.get("data")
                    
                    # 直接转发事件（LLMService已经返回了正确的SSE格式）
                    yield chunk
                    
                    # 累加thinking_chunk的纯文本内容
                    if event_type == "thinking_chunk" and event_data:
                        thinking_content += event_data
                    # 累加answer_chunk的纯文本内容
                    elif event_type == "answer_chunk" and event_data:
                        assistant_response_text += event_data
                    elif event_type == "error":
                        # 错误事件直接返回，不继续处理
                        continue
                except (json.JSONDecodeError, AttributeError):
                    # 如果解析失败，跳过这个chunk
                    logger.warning(f"无法解析chunk: {chunk_str[:100]}")
                    pass

            # 推送 done 事件
            yield sse_event("done", None)

            # 保存助手回复（含 references、retrieved_documents 和 thinking_content）
            final_db_content = {"text": assistant_response_text, "references": references, "retrieved_documents": retrieved_documents}
            SessionService.add_assistant_message(
                session_id, 
                json.dumps(final_db_content, ensure_ascii=False),
                thinking_content=thinking_content if thinking_content else None
            )

        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            # 回滚：删除最后一条用户消息
            messages_list = SessionService.get_session_messages(session_id)
            if messages_list and messages_list[-1].get('role') == 'user':
                last_user_msg_id = messages_list[-1].get('message_id')
                if last_user_msg_id:
                    SessionService.delete_message_and_cleanup(last_user_msg_id)
                    logger.info(f"已回滚用户消息: {last_user_msg_id}")
            yield sse_event("error", "抱歉，生成回答时遇到内部错误。请稍后重试。")

    return StreamingResponse(
        process_request(),
        media_type="application/x-json-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked"
        }
    )


@router.post("/chat/regenerate")
async def chat_regenerate(req: RegenerateRequest):
    """
    编辑重试接口：从任意用户消息节点重新生成对话（集成 RAG 检索流程）
    
    流程：
    1. 验证message_id是否属于该session且是user消息
    2. 删除该消息之后的所有消息
    3. 更新该用户消息的内容
    4. 执行 RAG 检索（如果有文档）
    5. 重新生成AI回答
    """
    if not config.is_configured():
        async def not_configured_stream():
            yield await LLMService.stream_json("error", "系统未配置。请先访问配置页面完成设置。")
        return StreamingResponse(not_configured_stream(), media_type="application/x-json-stream")
    
    # 验证消息是否存在且属于该会话
    message = db.get_message_by_id(req.message_id)
    if not message:
        async def error_stream():
            yield await LLMService.stream_json("error", "操作失败：需要编辑的消息不存在或已被删除。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")
    
    if message['session_id'] != req.session_id:
        async def error_stream():
            yield await LLMService.stream_json("error", "操作失败：消息与当前会话不匹配。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")
    
    if message['role'] != 'user':
        async def error_stream():
            yield await LLMService.stream_json("error", "操作失败：您只能对自己发送的消息进行编辑。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")
    
    try:
        # 1. 删除该消息之后的所有消息
        deleted_count = SessionService.delete_messages_after_and_cleanup(req.session_id, req.message_id)
        logger.info(f"编辑消息 {req.message_id}，已删除后续 {deleted_count} 条消息")
        
        # 2. 将前端代理路径转回 MinIO URL 后再更新
        minio_image_urls = None
        if req.new_image_urls and minio_storage:
            minio_image_urls = []
            for url in req.new_image_urls:
                converted = minio_storage.proxy_path_to_minio_url(url)
                minio_image_urls.append(converted if converted else url)
        elif req.new_image_urls:
            minio_image_urls = req.new_image_urls
        
        success = SessionService.update_user_message(req.message_id, req.new_query, minio_image_urls)
        if not success:
            async def error_stream():
                yield await LLMService.stream_json("error", "数据库更新消息失败，请重试。")
            return StreamingResponse(error_stream(), media_type="application/x-json-stream")
        
        # 3. 获取更新后的历史记录
        history_data = SessionService.get_and_clean_history(req.session_id)
        logger.info(f"获取更新后的历史记录: {len(history_data.get('messages', []))}条")

        # 4. 获取模型配置，用于兼容性检查和消息构建
        has_images = history_data.get("has_images", False)
        model_name = req.selected_model
        chat_model_config = None
        if model_name:
            chat_model_config = config.get_chat_model_by_name(model_name)
        if not chat_model_config:
            chat_model_config = config.get_default_chat_model()
        model_type = (chat_model_config or {}).get("type", "text-model")
        display_model_name = (chat_model_config or {}).get("name", model_name or "默认模型")

        # 5. 兼容性检查
        compat_error = ChatService.check_model_compatibility(has_images, model_type, display_model_name)
        if compat_error:
            async def compat_error_stream():
                yield await LLMService.stream_json("error", compat_error)
            return StreamingResponse(compat_error_stream(), media_type="application/x-json-stream")

        # 6. RAG 检索（构造一个临时 SearchRequest 用于复用 _resolve_rag_context）
        rag_req = SearchRequest(
            query=req.new_query,
            session_id=req.session_id,
            user_id="system",  # regenerate 不需要 user_id 做检索
            selected_model=req.selected_model,
            has_docs=req.has_docs,
        )
        rag_context, references, early_sse_message = await _resolve_rag_context(
            rag_req, history_messages=history_data.get("messages", [])
        )

        # 7. 构建系统提示词
        if rag_context:
            system_prompt = REFERENCE_SYSTEM_PROMPT + "\n\n" + rag_context
        else:
            system_prompt = ChatService.get_default_system_prompt()

        # 8. 构建消息
        messages = ChatService.build_messages(history_data, system_prompt=system_prompt, model_type=model_type)
        
        # 9. 流式调用 LLM 并保存回复
        async def process_request():
            retrieved_documents = []  # 用于持久化存储
            thinking_content = ""  # 累加思考过程
            try:
                # 如果有提前发送的消息（如文档处理中提示）
                if early_sse_message:
                    yield early_sse_message
                    final_db_content = {"text": "文档正在处理中，请稍后再试...", "references": [], "retrieved_documents": []}
                    SessionService.add_assistant_message(req.session_id, json.dumps(final_db_content, ensure_ascii=False))
                    return

                # 推送 references 事件
                if references:
                    yield sse_event("references", references)
                    
                    # 推送 retrieved_documents 事件：文档去重列表
                    doc_ids_with_none = [ref.get("doc_id") for ref in references]
                    unique_doc_ids = list(set(d for d in doc_ids_with_none if d is not None))  # 过滤None并去重
                    if unique_doc_ids:
                        with db.SessionLocal() as db_session:
                            doc_dict = DocumentCRUD.get_documents_by_ids(db_session, unique_doc_ids)
                            retrieved_documents = [
                                {
                                    "doc_id": doc_id,
                                    "file_name": doc.file_name,
                                    "summary": doc.summary or ""  # 空摘要返回空字符串
                                }
                                for doc_id, doc in doc_dict.items()
                            ]
                            yield sse_event("retrieved_documents", retrieved_documents)
                            logger.info(f"[Regenerate] 发送 retrieved_documents 事件: {len(retrieved_documents)} 篇文档")

                assistant_response_text = ""

                for chunk in LLMService.stream_chat(messages, model_name=model_name):
                    chunk_str = chunk.decode("utf-8", errors="ignore")
                    if not chunk_str:
                        continue

                    # 解析 SSE 事件
                    try:
                        chunk_data = json.loads(chunk_str.strip())
                        event_type = chunk_data.get("type")
                        event_data = chunk_data.get("data")
                        
                        # 直接转发事件（LLMService已经返回了正确的SSE格式）
                        yield chunk
                        
                        # 累加thinking_chunk的纯文本内容
                        if event_type == "thinking_chunk" and event_data:
                            thinking_content += event_data
                        # 累加answer_chunk的纯文本内容
                        elif event_type == "answer_chunk" and event_data:
                            assistant_response_text += event_data
                        elif event_type == "error":
                            # 错误事件直接返回，不继续处理
                            continue
                    except (json.JSONDecodeError, AttributeError):
                        # 如果解析失败，跳过这个chunk
                        logger.warning(f"无法解析chunk: {chunk_str[:100]}")
                        pass

                # 推送 done 事件
                yield sse_event("done", None)

                # 保存助手回复（含 references、retrieved_documents 和 thinking_content）
                final_db_content = {"text": assistant_response_text, "references": references, "retrieved_documents": retrieved_documents}
                SessionService.add_assistant_message(
                    req.session_id, 
                    json.dumps(final_db_content, ensure_ascii=False),
                    thinking_content=thinking_content if thinking_content else None
                )
                logger.info(f"助手回复已添加至会话 {req.session_id}")
                    
            except Exception as e:
                logger.error(f"重新生成回答失败: {e}")
                yield sse_event("error", "抱歉，重新生成回答时遇到内部错误。请稍后重试。")
        
        return StreamingResponse(
            process_request(),
            media_type="application/x-json-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
                "Transfer-Encoding": "chunked"
            }
        )
        
    except Exception as e:
        logger.error(f"编辑重试失败: {e}")
        async def error_stream():
            yield await LLMService.stream_json("error", "抱歉，处理编辑请求时遇到未知错误，请刷新后重试。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")


# ============================================================
# Agent 模式路由（独立于固定流水线，前端通过开关选择）
# ============================================================

_AGENT_SSE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
    "Transfer-Encoding": "chunked",
}


@router.post("/chat/agent/send")
async def agent_chat_send(req: SearchRequest):
    """Agent 模式聊天接口 — LLM 自主决策是否检索文档"""
    if not config.is_configured():
        async def not_configured_stream():
            yield await LLMService.stream_json("error", "系统未配置。请先访问配置页面完成设置。")
        return StreamingResponse(not_configured_stream(), media_type="application/x-json-stream")

    session_id = req.session_id
    if not session_id:
        async def error_stream():
            yield await LLMService.stream_json("error", "会话ID丢失，无法处理请求。请尝试刷新页面或新建会话。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")

    logger.info(f"[Agent] 开始为会话 {session_id} 生成回复 | kb_id={req.kb_id}")

    # 历史记录
    history_data = SessionService.get_and_clean_history(session_id)

    # 模型配置 & 兼容性检查
    has_images = history_data.get("has_images", False)
    model_name = req.selected_model
    chat_model_config = config.get_chat_model_by_name(model_name) if model_name else None
    if not chat_model_config:
        chat_model_config = config.get_default_chat_model()
    model_type = (chat_model_config or {}).get("type", "text-model")
    display_model_name = (chat_model_config or {}).get("name", model_name or "默认模型")

    compat_error = ChatService.check_model_compatibility(has_images, model_type, display_model_name)
    if compat_error:
        async def compat_error_stream():
            yield await LLMService.stream_json("error", compat_error)
        return StreamingResponse(compat_error_stream(), media_type="application/x-json-stream")

    # 创建 AgentService 并判断检索范围
    agent = AgentService(session_id=session_id, kb_id=req.kb_id)
    early_message = await agent.resolve_search_scope()

    # 构建消息（Agent 模式使用默认 system prompt，检索上下文由 Agent 循环注入）
    system_prompt = ChatService.get_default_system_prompt()
    messages = ChatService.build_messages(history_data, system_prompt=system_prompt, model_type=model_type)

    async def process_request():
        try:
            if early_message:
                yield sse_event("answer_chunk", early_message)
                yield sse_event("done", None)
                final_db_content = {"text": early_message, "references": [], "retrieved_documents": []}
                SessionService.add_assistant_message(session_id, json.dumps(final_db_content, ensure_ascii=False))
                return

            references = []
            retrieved_documents = []
            thinking_content = ""  # 累加思考过程
            async for event in agent.run(messages, model_name=model_name):
                # 捕获 references、retrieved_documents 和 thinking_chunk 事件用于存储
                try:
                    parsed = json.loads(event.strip())
                    if isinstance(parsed, dict):
                        if parsed.get("type") == "references":
                            references = parsed.get("data", [])
                        elif parsed.get("type") == "retrieved_documents":
                            retrieved_documents = parsed.get("data", [])
                        elif parsed.get("type") == "thinking_chunk":
                            thinking_content += parsed.get("data", "")
                except (json.JSONDecodeError, AttributeError):
                    pass
                yield event

            # 保存助手回复（含 references、retrieved_documents 和 thinking_content）
            final_text = getattr(agent, "final_answer_text", "")
            final_db_content = {"text": final_text, "references": references, "retrieved_documents": retrieved_documents}
            SessionService.add_assistant_message(
                session_id, 
                json.dumps(final_db_content, ensure_ascii=False),
                thinking_content=thinking_content if thinking_content else None
            )

        except Exception as e:
            logger.error(f"[Agent] 调用失败: {e}", exc_info=True)
            messages_list = SessionService.get_session_messages(session_id)
            if messages_list and messages_list[-1].get("role") == "user":
                last_user_msg_id = messages_list[-1].get("message_id")
                if last_user_msg_id:
                    SessionService.delete_message_and_cleanup(last_user_msg_id)
                    logger.info(f"[Agent] 已回滚用户消息: {last_user_msg_id}")
            yield sse_event("error", "抱歉，生成回答时遇到内部错误。请稍后重试。")

    return StreamingResponse(
        process_request(),
        media_type="application/x-json-stream",
        headers=_AGENT_SSE_HEADERS,
    )


@router.post("/chat/agent/regenerate")
async def agent_chat_regenerate(req: RegenerateRequest):
    """Agent 模式编辑重试接口"""
    if not config.is_configured():
        async def not_configured_stream():
            yield await LLMService.stream_json("error", "系统未配置。请先访问配置页面完成设置。")
        return StreamingResponse(not_configured_stream(), media_type="application/x-json-stream")

    # 验证消息
    message = db.get_message_by_id(req.message_id)
    if not message:
        async def error_stream():
            yield await LLMService.stream_json("error", "操作失败：需要编辑的消息不存在或已被删除。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")

    if message["session_id"] != req.session_id:
        async def error_stream():
            yield await LLMService.stream_json("error", "操作失败：消息与当前会话不匹配。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")

    if message["role"] != "user":
        async def error_stream():
            yield await LLMService.stream_json("error", "操作失败：您只能对自己发送的消息进行编辑。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")

    try:
        # 1. 删除后续消息 & 更新用户消息
        deleted_count = SessionService.delete_messages_after_and_cleanup(req.session_id, req.message_id)
        logger.info(f"[Agent] 编辑消息 {req.message_id}，已删除后续 {deleted_count} 条消息")

        # 将前端代理路径转回 MinIO URL 后再更新
        minio_image_urls = None
        if req.new_image_urls and minio_storage:
            minio_image_urls = []
            for url in req.new_image_urls:
                converted = minio_storage.proxy_path_to_minio_url(url)
                minio_image_urls.append(converted if converted else url)
        elif req.new_image_urls:
            minio_image_urls = req.new_image_urls

        success = SessionService.update_user_message(req.message_id, req.new_query, minio_image_urls)
        if not success:
            async def error_stream():
                yield await LLMService.stream_json("error", "数据库更新消息失败，请重试。")
            return StreamingResponse(error_stream(), media_type="application/x-json-stream")

        # 2. 获取更新后的历史记录
        history_data = SessionService.get_and_clean_history(req.session_id)

        # 3. 模型配置 & 兼容性检查
        has_images = history_data.get("has_images", False)
        model_name = req.selected_model
        chat_model_config = config.get_chat_model_by_name(model_name) if model_name else None
        if not chat_model_config:
            chat_model_config = config.get_default_chat_model()
        model_type = (chat_model_config or {}).get("type", "text-model")
        display_model_name = (chat_model_config or {}).get("name", model_name or "默认模型")

        compat_error = ChatService.check_model_compatibility(has_images, model_type, display_model_name)
        if compat_error:
            async def compat_error_stream():
                yield await LLMService.stream_json("error", compat_error)
            return StreamingResponse(compat_error_stream(), media_type="application/x-json-stream")

        # 4. 创建 AgentService
        agent = AgentService(session_id=req.session_id)
        early_message = await agent.resolve_search_scope()

        # 5. 构建消息
        system_prompt = ChatService.get_default_system_prompt()
        messages = ChatService.build_messages(history_data, system_prompt=system_prompt, model_type=model_type)

        async def process_request():
            try:
                if early_message:
                    yield sse_event("answer_chunk", early_message)
                    yield sse_event("done", None)
                    final_db_content = {"text": early_message, "references": [], "retrieved_documents": []}
                    SessionService.add_assistant_message(req.session_id, json.dumps(final_db_content, ensure_ascii=False))
                    return

                references = []
                retrieved_documents = []
                thinking_content = ""  # 累加思考过程
                async for event in agent.run(messages, model_name=model_name):
                    try:
                        parsed = json.loads(event.strip())
                        if isinstance(parsed, dict):
                            if parsed.get("type") == "references":
                                references = parsed.get("data", [])
                            elif parsed.get("type") == "retrieved_documents":
                                retrieved_documents = parsed.get("data", [])
                            elif parsed.get("type") == "thinking_chunk":
                                thinking_content += parsed.get("data", "")
                    except (json.JSONDecodeError, AttributeError):
                        pass
                    yield event

                final_text = getattr(agent, "final_answer_text", "")
                final_db_content = {"text": final_text, "references": references, "retrieved_documents": retrieved_documents}
                SessionService.add_assistant_message(
                    req.session_id, 
                    json.dumps(final_db_content, ensure_ascii=False),
                    thinking_content=thinking_content if thinking_content else None
                )
                logger.info(f"[Agent] 助手回复已添加至会话 {req.session_id}")

            except Exception as e:
                logger.error(f"[Agent] 重新生成回答失败: {e}", exc_info=True)
                yield sse_event("error", "抱歉，重新生成回答时遇到内部错误。请稍后重试。")

            except Exception as e:
                logger.error(f"[Agent] 重新生成回答失败: {e}", exc_info=True)
                yield sse_event("error", "抱歉，重新生成回答时遇到内部错误。请稍后重试。")

        return StreamingResponse(
            process_request(),
            media_type="application/x-json-stream",
            headers=_AGENT_SSE_HEADERS,
        )

    except Exception as e:
        logger.error(f"[Agent] 编辑重试失败: {e}", exc_info=True)
        async def error_stream():
            yield await LLMService.stream_json("error", "抱歉，处理编辑请求时遇到未知错误，请刷新后重试。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")
