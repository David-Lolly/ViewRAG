import json
import logging
import time
from typing import Any, Dict, Generator, List, Optional

from openai import OpenAI

from crud.config_manager import config

logger = logging.getLogger(__name__)


class LLMService:
    """LLM API 调用服务 - 职责单一，只负责调用 LLM 并返回流式响应"""

    @staticmethod
    async def stream_json(data_type: str, content: Any) -> str:
        """生成流式 JSON 响应（从 SearchService.stream_json 迁移）"""
        message = {
            "type": data_type,
            "data": content,
        }
        return json.dumps(message, ensure_ascii=False) + "\n"

    @staticmethod
    def stream_chat(
        messages: List[dict],
        model_name: Optional[str] = None,
    ) -> Generator[bytes, None, None]:
        """
        流式调用 LLM API。

        Args:
            messages: 已构建好的消息列表（由 ChatService 构建）
            model_name: 模型名称，None 时使用默认模型

        Returns:
            Generator，yield bytes 格式的内容块（SSE 事件 JSON 字符串）
        """
        # 模型配置查找
        if model_name:
            chat_model_config = config.get_chat_model_by_name(model_name)
            if not chat_model_config:
                logger.warning(f"指定的模型 {model_name} 不存在，使用默认模型")
                chat_model_config = config.get_default_chat_model()
        else:
            chat_model_config = config.get_default_chat_model()

        if not chat_model_config:
            logger.error("未找到默认 chat_model 配置，无法生成回答。")
            yield json.dumps(
                {
                    "type": "error",
                    "data": "系统默认模型未配置，无法生成回答。请联系管理员检查后台配置。",
                },
                ensure_ascii=False,
            ).encode("utf-8") + b"\n"
            return

        base_url = chat_model_config.get("base_url")
        resolved_model_name = chat_model_config.get("name")
        api_key = chat_model_config.get("api_key")
        model_type = chat_model_config.get("type", "text-model")

        if not all([base_url, resolved_model_name, api_key]):
            logger.error("Chat model configuration is incomplete.")
            yield json.dumps(
                {
                    "type": "error",
                    "data": f"模型 '{resolved_model_name}' 配置不完整，无法使用。请联系管理员检查后台配置。",
                },
                ensure_ascii=False,
            ).encode("utf-8") + b"\n"
            return

        logger.info(
            f"response_stage_messages:{json.dumps(messages, ensure_ascii=False, indent=2)}"
        )

        client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)

        try:
            logger.info("开始调用LLM API...")
            start_time = time.time()

            assert resolved_model_name is not None
            
            # 推理模型自动开启思考模式
            extra_body = {}
            if model_type == "reason-model":
                extra_body["enable_thinking"] = True
                logger.info(f"推理模型 {resolved_model_name} 已开启思考模式")
            
            response = client.chat.completions.create(
                model=resolved_model_name,
                messages=messages,
                stream=True,
                temperature=0.8,
                stream_options={"include_usage": True},
                extra_body=extra_body if extra_body else None,
            )

            logger.info(
                f"LLM API调用完成，耗时: {time.time() - start_time:.2f}秒"
            )

            chunk_count = 0
            had_thinking = False
            thinking_done_sent = False
            
            for chunk in response:
                if chunk_count == 0:
                    logger.info(
                        f"收到第一个chunk，总耗时: {time.time() - start_time:.2f}秒"
                    )
                chunk_count += 1

                # 检查是否有 choices
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                # 处理思考过程（reasoning_content）
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    had_thinking = True
                    yield json.dumps(
                        {"type": "thinking_chunk", "data": delta.reasoning_content},
                        ensure_ascii=False,
                    ).encode("utf-8") + b"\n"
                
                # 处理正式回答（content）
                if hasattr(delta, "content") and delta.content:
                    # 如果有过思考，先发送 thinking_done
                    if had_thinking and not thinking_done_sent:
                        yield json.dumps(
                            {"type": "thinking_done", "data": None},
                            ensure_ascii=False,
                        ).encode("utf-8") + b"\n"
                        thinking_done_sent = True
                    
                    yield json.dumps(
                        {"type": "answer_chunk", "data": delta.content},
                        ensure_ascii=False,
                    ).encode("utf-8") + b"\n"

            logger.info(f"流式响应完成，总共处理了{chunk_count}个chunks")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            yield json.dumps(
                {"type": "error", "data": f"模型调用失败: {str(e)}"},
                ensure_ascii=False,
            ).encode("utf-8") + b"\n"

    @staticmethod
    def _resolve_model_config(model_name: Optional[str] = None) -> Optional[Dict]:
        """解析模型配置，返回 chat_model_config 或 None"""
        if model_name:
            chat_model_config = config.get_chat_model_by_name(model_name)
            if not chat_model_config:
                logger.warning(f"指定的模型 {model_name} 不存在，使用默认模型")
                chat_model_config = config.get_default_chat_model()
        else:
            chat_model_config = config.get_default_chat_model()
        return chat_model_config

    @staticmethod
    def call_with_tools(
        messages: List[dict],
        tools: List[dict],
        model_name: Optional[str] = None,
    ) -> Dict:
        """
        非流式调用 LLM API（带工具定义）。

        用于 Agent 循环的工具调用阶段，LLM 决定是否调用工具。

        Args:
            messages: 消息列表
            tools: OpenAI Function Calling 格式的工具定义列表
            model_name: 模型名称，None 时使用默认模型

        Returns:
            {
                "finish_reason": "tool_calls" | "stop",
                "content": str | None,          # finish_reason=stop 时的文本内容
                "tool_calls": list | None,       # finish_reason=tool_calls 时的工具调用列表
            }

        Raises:
            RuntimeError: 模型配置缺失或 API 调用失败时抛出
        """
        chat_model_config = LLMService._resolve_model_config(model_name)
        if not chat_model_config:
            raise RuntimeError("未找到默认 chat_model 配置，无法调用 LLM。")

        base_url = chat_model_config.get("base_url")
        resolved_model_name = chat_model_config.get("name")
        api_key = chat_model_config.get("api_key")

        if not all([base_url, resolved_model_name, api_key]):
            raise RuntimeError(f"模型 '{resolved_model_name}' 配置不完整。")

        logger.info(
            f"[call_with_tools] messages count={len(messages)}, tools count={len(tools)}"
        )

        client = OpenAI(api_key=api_key, base_url=base_url, timeout=60)

        try:
            start_time = time.time()
            assert resolved_model_name is not None
            response = client.chat.completions.create(
                model=resolved_model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=False,
                temperature=0.8,
            )
            elapsed = time.time() - start_time
            logger.info(f"[call_with_tools] 调用完成，耗时: {elapsed:.2f}秒")

            choice = response.choices[0]
            finish_reason = choice.finish_reason

            if finish_reason == "tool_calls" and choice.message.tool_calls:
                tool_calls = []
                for tc in choice.message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })
                return {
                    "finish_reason": "tool_calls",
                    "content": choice.message.content,
                    "tool_calls": tool_calls,
                    "raw_message": choice.message,
                }

            # finish_reason == "stop" 或其他情况，视为最终回答
            return {
                "finish_reason": "stop",
                "content": choice.message.content or "",
                "tool_calls": None,
                "raw_message": choice.message,
            }

        except Exception as e:
            logger.error(f"[call_with_tools] 调用失败: {e}")
            raise RuntimeError(f"LLM 工具调用失败: {e}") from e
