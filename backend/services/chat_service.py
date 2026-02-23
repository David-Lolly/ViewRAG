import logging
from datetime import date
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ChatService:
    """消息编排服务 - 负责构建发送给 LLM 的消息列表"""

    @staticmethod
    def get_default_system_prompt() -> str:
        """获取默认系统提示词"""
        current_date = "当前日期：" + date.today().strftime("%Y-%m-%d")
        return (
            f"你是AI搜索助手，名字叫做ViewRAG，由乐乐开发，{current_date}。"
            "请根据你和用户的聊天记录，以及当前用户的问题，充分理解用户意图，进行回答。"
        )

    @staticmethod
    def check_model_compatibility(
        has_images: bool,
        model_type: str,
        model_name: str,
    ) -> Optional[str]:
        """
        检查模型兼容性。

        Args:
            has_images: 历史对话中是否包含图片
            model_type: 模型类型，"text-model", "multi-model" 或 "reason-model"
            model_name: 模型名称（用于错误提示）

        Returns:
            None 表示兼容，否则返回错误信息字符串
        """
        if has_images and model_type not in ["multi-model"]:
            # 注意：推理模型（reason-model）通常也不支持图片，除非它是多模态推理模型（暂时视为不支持）
            return (
                f"检测到历史对话中包含图片，但当前选择的 '{model_name}' 是 {model_type}，"
                "无法处理图片。请切换到多模态模型或创建新会话。"
            )
        return None

    @staticmethod
    def build_messages(
        chat_history: Dict,
        system_prompt: Optional[str] = None,
        model_type: str = "text-model",
    ) -> List[dict]:
        """
        构建消息列表。

        Args:
            chat_history: {"messages": List[dict], "has_images": bool}
            system_prompt: 系统提示词，None 时使用默认提示词
            model_type: "text-model" 或 "multi-model"

        Returns:
            构建好的 messages list，可直接传给 LLMService.stream_chat
        """
        if system_prompt is None:
            system_prompt = ChatService.get_default_system_prompt()

        history_messages = []
        try:
            history_messages = chat_history.get("messages", [])
        except Exception as e:
            logger.error(f"解析 chat_history 出错: {e}")

        messages: List[dict] = []

        if model_type == "multi-model":
            logger.info("使用多模态模型消息构建策略")
            # ... (Existing multi-model logic)
            first_user_msg_found = False

            for msg in history_messages:
                if msg.get("role") == "user" and not first_user_msg_found:
                    # 第一条用户消息：在文本前插入系统提示词
                    content_parts: List[dict] = [
                        {
                            "type": "text",
                            "text": system_prompt + "\n\n" + "用户问题：" + msg.get("content", ""),
                        }
                    ]

                    if msg.get("image_urls"):
                        for img_b64 in msg["image_urls"]:
                            if not img_b64.startswith("data:image"):
                                img_b64 = f"data:image/jpeg;base64,{img_b64}"
                            content_parts.append(
                                {"type": "image_url", "image_url": {"url": img_b64}}
                            )

                    messages.append({"role": "user", "content": content_parts})
                    first_user_msg_found = True

                elif msg.get("role") == "user":
                    content_parts = [{"type": "text", "text": msg.get("content", "")}]

                    if msg.get("image_urls"):
                        for img_b64 in msg["image_urls"]:
                            if not img_b64.startswith("data:image"):
                                img_b64 = f"data:image/jpeg;base64,{img_b64}"
                            content_parts.append(
                                {"type": "image_url", "image_url": {"url": img_b64}}
                            )

                    messages.append({"role": "user", "content": content_parts})

                elif msg.get("role") == "assistant":
                    messages.append({"role": "assistant", "content": msg.get("content", "")})
        elif model_type == "reason-model":
             logger.info("使用推理模型消息构建策略 (无系统提示词)")
             # 推理模型通常不支持 system role 或者对 system prompt 比较敏感，
             # 有些甚至建议将 system prompt 合并到 user prompt 中，或者完全不使用 system prompt。
             # 这里我们采用保守策略： 
             # 1. 忽略 system_prompt (或将其追加到第一条用户消息)
             # 2. 仅保留 user 和 assistant 消息
             # 3. 确保第一条消息是 user

             if history_messages:
                  first_msg = True
                  for msg in history_messages:
                       role = msg.get("role")
                       content = msg.get("content", "")
                       
                       # 将 system prompt 合并到第一个用户问题中 (可选，取决于模型特性，这里暂且合并以保持指令跟随)
                       if first_msg and role == "user" and system_prompt:
                            content = f"{system_prompt}\n\n{content}"
                            first_msg = False
                       
                       # 过滤非法角色，DeepSeek 等其实主要支持 user/assistant
                       if role in ["user", "assistant"]:
                            messages.append({"role": role, "content": content})
             else:
                  # 无历史记录，仅包含当前(隐式)或空，这里逻辑上 history_messages 应该包含所有上下文
                  pass
             
             # 如果完全没有消息，兜底
             if not messages and system_prompt:
                  messages.append({"role": "user", "content": system_prompt})

        else:
            logger.info("使用文本模型消息构建策略")
            messages = [{"role": "system", "content": system_prompt}]

            if history_messages:
                for msg in history_messages:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        messages.append({"role": msg["role"], "content": msg["content"]})

        return messages
