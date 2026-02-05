import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.request import SearchRequest, RegenerateRequest
from services.search import SearchService
from services.session import SessionService
from services.storage import minio_storage
from crud.config_manager import config
import crud.database as db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/llm/search")
async def web_search(req: SearchRequest):
    """联网搜索接口"""
    if not config.is_configured():
        async def not_configured_stream():
            yield await SearchService.stream_json("error", "系统未配置。请先访问配置页面完成设置。")
        return StreamingResponse(not_configured_stream(), media_type="application/x-json-stream")

    session_id = req.session_id
    if not session_id:
        session_id = SessionService.create_new_session(user_id=req.user_id, title=req.query[:50])['session_id']
        if not session_id:
            logger.error("创建新会话失败")
            async def error_stream():
                yield await SearchService.stream_json("error", "创建新会话失败")
            return StreamingResponse(error_stream(), media_type="application/x-json-stream")

    # 历史记录中已经包含了最新的用户消息及其图片
    history_data = SessionService.get_and_clean_history(session_id)
    logger.info(f"处理后的历史记录数量: {len(history_data.get('messages', []))}, 包含图片: {history_data.get('has_images', False)}")

    # 从历史记录中获取最新的查询
    # last_query = ""
    # history_messages = history_data.get('messages', [])
    # if history_messages and history_messages[-1].get('role') == 'user':
    #     last_query = history_messages[-1].get('content', "")

    # if not last_query:
    #     # 如果由于某种原因最新的消息不是用户的，则回退到使用req.query
    #     # 或者直接报错，因为这不符合V2的设计
    #     logger.warning(f"无法从会话 {session_id} 的历史记录中找到最新的用户查询，将使用请求中的查询")
    #     last_query = req.query

    async def process_request():
        try:
            final_db_content = {"text": "", "references": []}
            full_response_text = ""  # 收集完整的AI回复文本用于调试
            async for chunk in SearchService.web_search(req.query, history_data, selected_model=req.selected_model):
                # 检查是否是最终内容
                try:
                    chunk_data = json.loads(chunk)
                    if chunk_data.get("type") == "final_content":
                        final_db_content = chunk_data.get("payload", final_db_content)
                        continue
                    # 收集所有answer_chunk文本
                    if chunk_data.get("type") == "answer_chunk":
                        full_response_text += chunk_data.get("payload", "")
                except:
                    pass
                yield chunk
            
            # 流式结束后打印完整的AI回复
            # logger.info(f"===== 联网搜索 - 完整AI回复开始 (会话: {session_id}) =====")
            # logger.info(f"完整回复文本:\n{full_response_text}")
            # logger.info(f"参考来源数量: {len(final_db_content.get('references', []))}")
            # logger.info(f"===== 联网搜索 - 完整AI回复结束 =====")
            
            # 保存助手回复
            SessionService.add_assistant_message(session_id, json.dumps(final_db_content, ensure_ascii=False))
            logger.info(f"助手回复及参考来源已添加至会话 {session_id}")
            
        except Exception as e:
            logger.error(f"联网搜索失败: {e}")
            # 回滚：删除最后一条用户消息
            messages = SessionService.get_session_messages(session_id)
            if messages and messages[-1].get('role') == 'user':
                last_user_msg_id = messages[-1].get('message_id')
                if last_user_msg_id:
                    SessionService.delete_message_and_cleanup(last_user_msg_id)
                    logger.info(f"已回滚用户消息: {last_user_msg_id}")
            # 返回错误信息
            yield await SearchService.stream_json("error", f"搜索失败: {str(e)}")

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

@router.post("/llm/direct")
async def direct_search(req: SearchRequest):
    """直接LLM回答接口"""
    if not config.is_configured():
        async def not_configured_stream():
            yield await SearchService.stream_json("error", "系统未配置。请先访问配置页面完成设置。")
        return StreamingResponse(not_configured_stream(), media_type="application/x-json-stream")

    session_id = req.session_id
    if not session_id:
        # 在V2流程中，调用此接口时必须有session_id，因为消息和图片已先发送
        logger.error("direct_search调用时缺少session_id")
        async def error_stream():
            yield await SearchService.stream_json("error", "会话ID丢失，无法处理请求。请尝试刷新页面或新建会话。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")
    

    
    logger.info(f"开始为会话 {session_id} 生成直接回复")
    
    # V2流程改造: 直接从数据库获取包含图片（如有）的完整历史记录
    history_data = SessionService.get_and_clean_history(session_id)
    logger.info(f"处理后的历史记录数量: {len(history_data.get('messages', []))}, 包含图片: {history_data.get('has_images', False)}")
    


    async def process_request():
        try:
            assistant_response_text = ""
            # V2流程改造: 不再传递image_url, 直接传递base64列表和完整的历史数据
            async for chunk in SearchService.direct_llm_response(
                query=req.query,
                chat_history= history_data, 
                selected_model=req.selected_model, 
            ):
                # 收集响应文本
                try:
                    chunk_data = json.loads(chunk)
                    if chunk_data.get("type") == "answer_chunk":
                        assistant_response_text += chunk_data.get("payload", "")
                except:
                    pass
                yield chunk
                # await asyncio.sleep(0)
            
            
            # 保存助手回复
            final_db_content = {"text": assistant_response_text, "references": []}
            SessionService.add_assistant_message(session_id, json.dumps(final_db_content, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            # 回滚：删除最后一条用户消息
            messages = SessionService.get_session_messages(session_id)
            if messages and messages[-1].get('role') == 'user':
                last_user_msg_id = messages[-1].get('message_id')
                if last_user_msg_id:
                    SessionService.delete_message_and_cleanup(last_user_msg_id)
                    logger.info(f"已回滚用户消息: {last_user_msg_id}")
            # 返回错误信息
            yield await SearchService.stream_json("error", f"抱歉，生成回答时遇到内部错误。请稍后重试。")

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

@router.post("/llm/regenerate")
async def regenerate_message(req: RegenerateRequest):
    """
    编辑重试接口：从任意用户消息节点重新生成对话
    
    流程：
    1. 验证message_id是否属于该session且是user消息
    2. 删除该消息之后的所有消息
    3. 更新该用户消息的内容
    4. 重新生成AI回答
    """
    if not config.is_configured():
        async def not_configured_stream():
            yield await SearchService.stream_json("error", "系统未配置。请先访问配置页面完成设置。")
        return StreamingResponse(not_configured_stream(), media_type="application/x-json-stream")
    
    # 验证消息是否存在且属于该会话
    message = db.get_message_by_id(req.message_id)
    if not message:
        async def error_stream():
            yield await SearchService.stream_json("error", "操作失败：需要编辑的消息不存在或已被删除。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")
    
    if message['session_id'] != req.session_id:
        async def error_stream():
            yield await SearchService.stream_json("error", "操作失败：消息与当前会话不匹配。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")
    
    if message['role'] != 'user':
        async def error_stream():
            yield await SearchService.stream_json("error", "操作失败：您只能对自己发送的消息进行编辑。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")
    
    try:
        # 1. 删除该消息之后的所有消息
        deleted_count = SessionService.delete_messages_after_and_cleanup(req.session_id, req.message_id)
        logger.info(f"编辑消息 {req.message_id}，已删除后续 {deleted_count} 条消息")
        
        # 2. 更新用户消息内容
        success = SessionService.update_user_message(req.message_id, req.new_query, req.new_image_urls)
        if not success:
            async def error_stream():
                yield await SearchService.stream_json("error", "数据库更新消息失败，请重试。")
            return StreamingResponse(error_stream(), media_type="application/x-json-stream")
        
        # 3. 获取更新后的历史记录
        history_data = SessionService.get_and_clean_history(req.session_id)
        logger.info(f"获取更新后的历史记录: {len(history_data.get('messages', []))}条")
        
        # 4. 根据use_web参数选择生成方式
        async def process_request():
            try:
                if req.use_web:
                    # 联网搜索模式
                    final_db_content = {"text": "", "references": []}
                    full_response_text = ""
                    async for chunk in SearchService.web_search(req.new_query, history_data, selected_model=req.selected_model):
                        try:
                            chunk_data = json.loads(chunk)
                            if chunk_data.get("type") == "final_content":
                                final_db_content = chunk_data.get("payload", final_db_content)
                                continue
                            if chunk_data.get("type") == "answer_chunk":
                                full_response_text += chunk_data.get("payload", "")
                        except:
                            pass
                        yield chunk
                    
                    # 流式结束后打印完整的AI回复
                    logger.info(f"===== 重新生成(联网) - 完整AI回复开始 (会话: {req.session_id}) =====")
                    logger.info(f"完整回复文本:\n{full_response_text}")
                    logger.info(f"===== 重新生成(联网) - 完整AI回复结束 =====")
                    
                    # 保存助手回复
                    SessionService.add_assistant_message(req.session_id, json.dumps(final_db_content, ensure_ascii=False))
                    logger.info(f"助手回复已添加至会话 {req.session_id}")
                else:
                    # 直接LLM模式
                    assistant_response_text = ""
                    
                    # 获取当前消息的图片（已更新的）
                    # current_images_base64 = []
                    # history_messages = history_data.get('messages', [])
                    # if history_messages:
                    #     last_message = history_messages[-1]
                    #     if last_message.get('role') == 'user' and last_message.get('image_urls'):
                    #         current_images_base64 = last_message['image_urls']
                    
                    async for chunk in SearchService.direct_llm_response(
                        req.new_query,
                        history_data,
                        selected_model=req.selected_model,
                        # images=current_images_base64
                    ):
                        try:
                            chunk_data = json.loads(chunk)
                            if chunk_data.get("type") == "answer_chunk":
                                assistant_response_text += chunk_data.get("payload", "")
                        except:
                            pass
                        yield chunk
                    
                    # 流式结束后打印完整的AI回复
                    logger.info(f"===== 重新生成(直接LLM) - 完整AI回复开始 (会话: {req.session_id}) =====")
                    logger.info(f"完整回复文本:\n{assistant_response_text}")
                    logger.info(f"===== 重新生成(直接LLM) - 完整AI回复结束 =====")
                    
                    # 保存助手回复
                    final_db_content = {"text": assistant_response_text, "references": []}
                    SessionService.add_assistant_message(req.session_id, json.dumps(final_db_content, ensure_ascii=False))
                    logger.info(f"助手回复已添加至会话 {req.session_id}")
                    
            except Exception as e:
                logger.error(f"重新生成回答失败: {e}")
                yield await SearchService.stream_json("error", f"抱歉，重新生成回答时遇到内部错误。请稍后重试。")
        
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
            yield await SearchService.stream_json("error", f"抱歉，处理编辑请求时遇到未知错误，请刷新后重试。")
        return StreamingResponse(error_stream(), media_type="application/x-json-stream")
