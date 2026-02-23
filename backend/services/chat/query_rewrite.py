"""QueryRewriteService — 问题重写服务

根据最近对话历史，将用户的简短/指代性问题重写为完整、独立的查询。
用于提升 RAG 检索的召回效果。
"""

import logging
from typing import List, Optional

from openai import OpenAI
from crud.config_manager import config

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """你是一个问题重写助手。根据对话历史，将用户的最新问题重写为一个完整、独立的查询。

规则：
1. 如果问题已经完整清晰，直接返回原问题
2. 如果问题包含指代词（如"它"、"这个"、"那个"）或省略了主语，根据历史补全
3. 只返回重写后的问题，不要任何解释

对话历史：
{history}

用户最新问题：{query}

重写后的问题："""


class QueryRewriteService:
    """问题重写服务"""

    @staticmethod
    def rewrite(
        query: str,
        history_messages: List[dict],
        max_rounds: int = 3,
    ) -> str:
        """
        根据历史对话重写用户问题。

        Args:
            query: 用户当前问题
            history_messages: 历史消息列表 [{"role": "user/assistant", "content": "..."}]
            max_rounds: 使用最近几轮对话（1轮 = 1个user + 1个assistant）

        Returns:
            重写后的问题（如果无需重写则返回原问题）
        """
        # 获取最近 N 轮对话
        recent_history = QueryRewriteService._get_recent_rounds(
            history_messages, max_rounds
        )

        # 如果没有历史，直接返回原问题
        if not recent_history:
            logger.info("[QueryRewrite] 无历史记录，跳过重写")
            return query

        # 格式化历史
        history_text = QueryRewriteService._format_history(recent_history)

        # 调用 LLM 重写
        rewritten = QueryRewriteService._call_llm(query, history_text)

        if rewritten and rewritten != query:
            logger.info(f"[QueryRewrite] 原问题: {query} -> 重写后: {rewritten}")
        else:
            logger.info(f"[QueryRewrite] 问题无需重写: {query}")

        return rewritten or query

    @staticmethod
    def _get_recent_rounds(
        messages: List[dict], max_rounds: int
    ) -> List[dict]:
        """获取最近 N 轮对话（不包含当前用户问题）"""
        if not messages:
            return []

        # 排除最后一条（当前用户问题）
        history = messages[:-1] if messages else []

        # 计算需要保留的消息数量（每轮2条：user + assistant）
        max_messages = max_rounds * 2
        return history[-max_messages:] if len(history) > max_messages else history

    @staticmethod
    def _format_history(messages: List[dict]) -> str:
        """格式化历史消息为文本"""
        lines = []
        for msg in messages:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            # 截断过长的内容
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _call_llm(query: str, history_text: str) -> Optional[str]:
        """调用 LLM 进行问题重写"""
        # 使用 summary_model（快速模型）
        model_config = config.get_summary_model()
        if not model_config:
            logger.warning("[QueryRewrite] 未配置 summary_model，跳过重写")
            return None

        base_url = model_config.get("base_url")
        model_name = model_config.get("name")
        api_key = model_config.get("api_key")

        if not all([base_url, model_name, api_key]):
            logger.warning("[QueryRewrite] summary_model 配置不完整，跳过重写")
            return None

        prompt = REWRITE_PROMPT.format(history=history_text, query=query)

        try:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=10)
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=256,
            )
            result = response.choices[0].message.content
            return result.strip() if result else None
        except Exception as e:
            logger.error(f"[QueryRewrite] LLM 调用失败: {e}")
            return None
