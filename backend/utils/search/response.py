import json
from typing import List, Optional, Union, Dict, Any
from langchain_core.documents import Document
from openai import OpenAI
import logging
from datetime import date
from openai.types.chat import ChatCompletionMessageParam
from crud.config_manager import config

logger = logging.getLogger(__name__)

def generate(
    chat_history: Optional[Dict] = None,  # 修改为Dict类型，包含messages和has_images
    selected_model: Optional[str] = None, 
):
    """
    用户的问题不需要搜索，直接调用模型回答

    param query: 用户问题
    param chat_history: 对话历史字典 {"messages": List[dict], "has_images": bool}
    param selected_model: 用户选择的模型名称
    """
    # 如果指定了模型，使用指定的；否则使用默认模型
    if selected_model:
        chat_model_config = config.get_chat_model_by_name(selected_model)
        if not chat_model_config:
            logger.warning(f"指定的模型 {selected_model} 不存在，使用默认模型")
            chat_model_config = config.get_default_chat_model()
    else:
        chat_model_config = config.get_default_chat_model()
    
    if not chat_model_config:
        logger.error("未找到默认 chat_model 配置，无法生成回答。")
        def error_stream():
            yield json.dumps({
                "type": "error",
                "payload": "系统默认模型未配置，无法生成回答。请联系管理员检查后台配置。"
            }, ensure_ascii=False).encode('utf-8') + b'\n'
        return error_stream()
    
    base_url = chat_model_config.get('base_url')
    model_name = chat_model_config.get('name')
    api_key = chat_model_config.get('api_key')
    model_type = chat_model_config.get('type', 'text-model')

    if not all([base_url, model_name, api_key]):
        logger.error("Chat model configuration is incomplete.")
        def error_stream():
            yield json.dumps({
                "type": "error",
                "payload": f"模型 '{model_name}' 配置不完整，无法使用。请联系管理员检查后台配置。"
            }, ensure_ascii=False).encode('utf-8') + b'\n'
        return error_stream()   
        # yield await SearchService.stream_json("error", "Chat model configuration is incomplete. Please configure the application.")
    
    # 解析历史记录
    history_messages = []
    has_images_in_history = False
    # if chat_history and isinstance(chat_history, dict):
    try:
        history_messages = chat_history.get('messages', [])
        has_images_in_history = chat_history.get('has_images', False)
    except Exception as e:
        logger.error(f"解析 chat_history 出错: {e}")

    
    # 检查模型兼容性
    # 情况1：历史中有图片，但当前模型是文本模型
    if has_images_in_history and model_type != 'multi-model':
        logger.error(f"历史对话中包含图片，但当前模型 {model_name} 是文本模型")
        def error_stream():
            yield json.dumps({
                "type": "error",
                "payload": f"检测到历史对话中包含图片，但当前选择的 '{model_name}' 是文本模型，无法处理图片。请切换到多模态模型或创建新会话。"
            }, ensure_ascii=False).encode('utf-8') + b'\n'
        return error_stream()
    # yield json.dumps({
    #             "type": "error",
    #             "payload": "这是测试错误信息"
    #         }, ensure_ascii=False).encode('utf-8') + b'\n'

    
    # 准备系统提示词
    current_date = '当前日期：' + date.today().strftime("%Y-%m-%d")
    system_prompt = f"""你是AI搜索助手，名字叫做TinyAISearch，由乐乐开发，{current_date}。请根据你和用户的聊天记录，以及当前用户的问题，充分理解用户意图，进行回答。"""
    
    messages = []
    
    # 根据模型类型采用不同的消息构建策略
    if model_type == 'multi-model':
        # 多模态模型：不使用系统提示词，将提示词放入第一条用户消息
        logger.info("使用多模态模型消息构建策略")
        
        # 有历史记录：重构消息列表
        first_user_msg_found = False
        
        for msg in history_messages:
            if msg.get('role') == 'user' and not first_user_msg_found:
                # 第一条用户消息：在文本前插入系统提示词
                content_parts = [{"type": "text", "text": system_prompt + "\n\n" + "用户问题：" + msg.get('content', '')}]
                
                # 添加该消息的图片
                if msg.get('image_urls'):
                    for img_b64 in msg['image_urls']:
                        if not img_b64.startswith('data:image'):
                            img_b64 = f"data:image/jpeg;base64,{img_b64}"
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": img_b64}
                        })
                
                messages.append({"role": "user", "content": content_parts})
                first_user_msg_found = True
                
            elif msg.get('role') == 'user':
                # 其他用户消息：保持多模态格式
                content_parts = [{"type": "text", "text": msg.get('content', '')}]
                
                if msg.get('image_urls'):
                    for img_b64 in msg['image_urls']:
                        if not img_b64.startswith('data:image'):
                            img_b64 = f"data:image/jpeg;base64,{img_b64}"
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": img_b64}
                        })
                
                messages.append({"role": "user", "content": content_parts})
                
            elif msg.get('role') == 'assistant':
                # 助手消息：纯文本格式
                messages.append({"role": "assistant", "content": msg.get('content', '')})
            
            
    else:
        # 文本模型：使用传统的系统提示词方式
        logger.info("使用文本模型消息构建策略")
        
        system_message = {"role": "system", "content": system_prompt}
        messages = [system_message]
        
        # 添加历史消息（纯文本格式）
        if history_messages:
            for msg in history_messages:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    messages.append({'role': msg['role'], 'content': msg['content']})
        
    
    logger.info(f'response_stage_messages:{json.dumps(messages, ensure_ascii=False, indent=2)}')
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=30  
    )

    
    def stream_generate():
        try:
            logger.info("开始调用LLM API...")
            import time
            start_time = time.time()
            
            assert model_name is not None
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                temperature=0.8,
                stream_options={"include_usage": True}
            )
            
            logger.info(f"LLM API调用完成，耗时: {time.time() - start_time:.2f}秒")
            
            chunk_count = 0
            original_response = ""
            for chunk in response:
                if chunk_count == 0:
                    logger.info(f"收到第一个chunk，总耗时: {time.time() - start_time:.2f}秒")
                chunk_count += 1
                
                response_data = json.loads(chunk.model_dump_json())
                try:
                    content = response_data['choices'][0]['delta']['content']
                    if content:  # 确保内容不为空
                        yield f"{content}".encode('utf-8')  # 将内容逐块发送给客户端
                        # original_response += content
                except Exception as e:
                    logger.error(f"Error extracting content from chunk: {e}")
            # logger.info(f"原始响应内容,original: {original_response}")
            logger.info(f"流式响应完成，总共处理了{chunk_count}个chunks")
        except Exception as e:
            
            logger.error(f"Error: {str(e)}")
            yield json.dumps({
                "type": "error",
                "payload": f"模型调用失败: {str(e)}"
            }, ensure_ascii=False).encode('utf-8') + b'\n'

    return stream_generate()



def search_generate(query: str, search_results: Union[Dict[str, List[Dict[str, Any]]], List[Document]],search_plan_data: dict, chat_history: Optional[Dict] = None,debug: bool = False, selected_model: Optional[str] = None):
    """
    参考搜索结果回答用户问题

    param query: 用户问题
    param search_results: 召回的搜索结果
    param chat_history: 对话历史字典 {"messages": List[dict], "has_images": bool}
    param selected_model: 用户选择的模型名称
    """
    # 如果指定了模型，使用指定的；否则使用默认模型
    if selected_model:
        chat_model_config = config.get_chat_model_by_name(selected_model)
        if not chat_model_config:
            logger.warning(f"指定的模型 {selected_model} 不存在，使用默认模型")
            chat_model_config = config.get_default_chat_model()
    else:
        chat_model_config = config.get_default_chat_model()
    
    if not chat_model_config:
        logger.error("未找到默认 chat_model 配置，无法生成回答。")
        def error_stream_search():
            yield json.dumps({
                "type": "error",
                "payload": "系统默认模型未配置，无法生成回答。请联系管理员检查后台配置。"
            }, ensure_ascii=False).encode('utf-8') + b'\n'
        return error_stream_search()
    
    base_url = chat_model_config.get('base_url')
    model_name = chat_model_config.get('name')
    api_key = chat_model_config.get('api_key')
    model_type = chat_model_config.get('type', 'text-model')

    if not all([base_url, model_name, api_key]):
        logger.error("Chat model configuration is incomplete.")
        def error_stream_search():
            yield json.dumps({
                "type": "error",
                "payload": f"模型 '{model_name}' 配置不完整，无法使用。请联系管理员检查后台配置。"
            }, ensure_ascii=False).encode('utf-8') + b'\n'
        return error_stream_search()
    
    # 解析历史记录
    history_messages = []
    has_images_in_history = False
    try:
         history_messages = chat_history.get('messages', [])
         has_images_in_history = chat_history.get('has_images', False)
    except Exception as e:
        logger.error(f"解析 chat_history 出错: {e}")

    
    
    # 检查模型兼容性：历史中有图片但当前是文本模型
    if has_images_in_history and model_type != 'multi-model':
        logger.error(f"历史对话中包含图片，但当前模型 {model_name} 是文本模型")
        def error_stream_search():
            yield json.dumps({
                "type": "error",
                "payload": f"检测到历史对话中包含图片，但当前选择的 '{model_name}' 是文本模型，无法处理图片。请切换到多模态模型或创建新会话。"
            }, ensure_ascii=False).encode('utf-8') + b'\n'
        return error_stream_search()

    implicit_questions = search_plan_data.get('query_analysis', {}).get('implicit_questions', [])
    
    all_search_results = []
    if isinstance(search_results, dict):
        for results in search_results.values():
            all_search_results.extend(results)
    else:
        for item in search_results:
            if isinstance(item, Document):
                all_search_results.append({
                    'title': item.metadata.get('title', ''),
                    'content': item.page_content,
                    'link': item.metadata.get('url', '')
                })
            elif isinstance(item, dict):
                all_search_results.append(item)

    logger.info(f'retreival_context:{json.dumps(all_search_results, ensure_ascii=False, indent=2)}')
    retrieval_context = [{"Title":page.get('title', ''), "Content":page.get('content', '')[:2048]} for page in all_search_results]
    prompt = """# Role and Goal
        You are a top-tier AI Search Analyst. Your primary mission is to provide the user with a comprehensive, accurate, and critically-evaluated answer. You must synthesize and deeply analyze the provided search results, not just summarize them.
        You will be provided with the following information:
        1.  **CURRENT_DATE**: The current date,if user's question is  related to current date,you should use it.
        2.  **IMPLICIT_QUESTIONS**: The underlying, deeper questions inferred from the user's query, which reveal their true intent.
        3.  **SEARCH_RESULTS**: A list of web pages containing a `Title`, `Content`. Treat this as raw, unverified data that requires rigorous scrutiny.

        **Step 1: Deconstruct the User's Need**
        -   Thoroughly analyze the `USER_QUERY` and all `IMPLICIT_QUESTIONS`. This is the key to understanding the full scope of what the user wants to know. Your final answer must address all of these points.

        **Step 2: Critically Evaluate the Search Results**
        -   **NEVER blindly trust the search results.** Your core value lies in your ability to analyze and vet information.
        -   **Cross-Validate Information**: Compare all search sources to identify points of consensus and disagreement.
        -   **Identify Contradictions**: If different sources provide conflicting information, you MUST explicitly point out these discrepancies in your answer. If possible, offer a plausible explanation for the conflict (e.g., different timeframes, differing perspectives, or reporting errors).
        -   **Assess Information Quality**: A well-reasoned article with specific data is more credible than a simple, unsubstantiated claim. Note when a source appears to be of low quality.
        -   **Identify Information Gaps**: If the search results are incomplete or cannot fully answer the user's question, state this clearly and specify what information is missing.

        **Step 3: Synthesize a High-Value Answer**
        -   **Structure Your Answer Logically**: Begin with a direct answer, then provide a detailed explanation using headings, lists, and bold text for clarity.
        -   **Synthesize, Don't List**: Weave the validated information from multiple sources into a single, coherent, and easy-to-understand narrative. Your output should be a new piece of value-added content.
        -   **Maintain an Objective, Analytical Tone**: Clearly present facts and distinguish them from speculation or conflicting reports.
        -   Your answer must use the same language as the user's question.
        -   The final output must be a well-written, thoughtful, and comprehensive response that directly answers the user's explicit and implicit questions.
        -   The answer must be grounded in the provided search results but elevated by your critical analysis.
        -   If there is not enough information to provide a definitive answer, explain why and what information is missing.
        
        CURRENT_DATE:
        {current_date}

        IMPLICIT_QUESTIONS:
        {implicit_questions}

        SEARCH_RESULTS:
        {retrieval_context}
        
        
        
        """

    implicit_questions = json.dumps(implicit_questions, ensure_ascii=False, indent=2)
    retrieval_context = json.dumps(retrieval_context, ensure_ascii=False, indent=2)
    current_date = date.today().strftime("%Y-%m-%d")

    system_prompt_with_context = prompt.format(current_date=current_date, implicit_questions=implicit_questions, retrieval_context=retrieval_context)
    
    messages = []
    
    # 根据模型类型采用不同的消息构建策略
    if model_type == 'multi-model':
        # 多模态模型：不使用系统提示词，将提示词和搜索上下文放入第一条用户消息
        logger.info("使用多模态模型消息构建策略（带搜索）")
        
        if not history_messages:
            # 没有历史记录：构建包含系统提示词和搜索上下文的第一条消息
            user_content = [{"type": "text", "text": system_prompt_with_context + "\n\nUSER_QUERY: " + query}]
            messages.append({"role": "user", "content": user_content})
        else:
            # 有历史记录：重构消息列表
            first_user_msg_found = False
            
            for msg in history_messages:
                if msg.get('role') == 'user' and not first_user_msg_found:
                    # 第一条用户消息：在文本前插入系统提示词和搜索上下文
                    content_parts = [{"type": "text", "text": system_prompt_with_context + "\n\n" + msg.get('content', '')}]
                    
                    # 添加该消息的图片
                    if msg.get('image_urls'):
                        for img_b64 in msg['image_urls']:
                            if not img_b64.startswith('data:image'):
                                img_b64 = f"data:image/jpeg;base64,{img_b64}"
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {"url": img_b64}
                            })
                    
                    messages.append({"role": "user", "content": content_parts})
                    first_user_msg_found = True
                    
                elif msg.get('role') == 'user':
                    # 其他用户消息：保持多模态格式
                    content_parts = [{"type": "text", "text": msg.get('content', '')}]
                    
                    if msg.get('image_urls'):
                        for img_b64 in msg['image_urls']:
                            if not img_b64.startswith('data:image'):
                                img_b64 = f"data:image/jpeg;base64,{img_b64}"
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {"url": img_b64}
                            })
                    
                    messages.append({"role": "user", "content": content_parts})
                    
                elif msg.get('role') == 'assistant':
                    # 助手消息：纯文本格式
                    messages.append({"role": "assistant", "content": msg.get('content', '')})
            
            # 添加当前用户消息
            current_content = [{"type": "text", "text": query}]
            messages.append({"role": "user", "content": current_content})
    
    else:
        # 文本模型：使用传统的系统提示词方式
        logger.info("使用文本模型消息构建策略（带搜索）")
        
        system_message = {"role": "system", "content": system_prompt_with_context}
        messages = [system_message]
        
        # 添加历史消息（纯文本格式）
        if history_messages:
            for msg in history_messages:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    messages.append({'role': msg['role'], 'content': msg['content']})
        
        # 添加当前用户消息（纯文本）
        messages.append({"role": "user", "content": query})
    
    logger.info(f'response_stage_messages:{json.dumps(messages, ensure_ascii=False, indent=2)}')
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
    def stream_generate():
        try:
            logger.info("开始调用LLM API (search_generate)...")
            import time
            start_time = time.time()
            
            assert model_name is not None
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                temperature=0.5,
            )
            
            logger.info(f"LLM API调用完成 (search_generate)，耗时: {time.time() - start_time:.2f}秒")
            
            chunk_count = 0
            for chunk in response:
                if chunk_count == 0:
                    logger.info(f"收到第一个chunk (search_generate)，总耗时: {time.time() - start_time:.2f}秒")
                chunk_count += 1
                
                response_data = json.loads(chunk.model_dump_json())
                try:
                    content = response_data['choices'][0]['delta']['content']

                    if content:  # 确保内容不为空
                        yield f"{content}".encode('utf-8')  # 将内容逐块发送给客户端
                except (KeyError, IndexError):
                    pass # Ignore empty delta content
                except Exception as e:
                    logger.warning(f"Error extracting content from chunk: {e}")
            
            logger.info(f"流式响应完成 (search_generate)，总共处理了{chunk_count}个chunks")
        except Exception as e:
                logger.error(f"Error: {str(e)}")
                yield json.dumps({
                    "type": "error",
                    "payload": f"模型调用失败: {str(e)}"
                }, ensure_ascii=False).encode('utf-8') + b'\n'

    return stream_generate()


