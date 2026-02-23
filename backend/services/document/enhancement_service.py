"""内容增强服务（LLM）"""

import asyncio
import logging
from typing import Optional, List

from schemas.prompts import get_prompt, SUMMARY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class EnhancementService:
    """LLM内容增强服务类"""
    
    def __init__(self, minio_service=None):
        """初始化增强服务"""
        # 从config加载LLM配置
        from crud.config_manager import config
        config.initialize_config()
        
        summary_model_cfg = config.get_summary_model() or {}
        vision_model_cfg = config.get_vision_model() or {}
        
        # 图片理解模型
        self.vision_model_name = vision_model_cfg.get('name', 'qwen-vl-plus')
        self.vision_model_base_url = vision_model_cfg.get(
            'base_url',
            'https://dashscope.aliyuncs.com/compatible-mode/v1'
        )
        self.vision_api_key = vision_model_cfg.get('api_key', '')
        
        # 文本摘要模型  
        self.summary_model_name = summary_model_cfg.get('name', 'qwen-flash')
        self.summary_model_base_url = summary_model_cfg.get(
            'base_url',
            'https://dashscope.aliyuncs.com/compatible-mode/v1'
        )
        self.summary_api_key = summary_model_cfg.get('api_key', '')
        
        self.temperature = summary_model_cfg.get('temperature', 0.3)
        self.minio = minio_service
        
        # 各场景 max_tokens 硬编码限制
        self.figure_max_tokens = 256       # 图片理解：精简描述
        self.table_max_tokens = 350        # 表格理解：结构化摘要
        self.doc_summary_max_tokens = 512  # 文档摘要：全局概括

        # Prompt templates
        self.image_prompt_template = self._require_prompt("image_prompt")
        self.table_prompt_template = self._require_prompt("table_prompt")
        self.doc_summary_prompt_template = self._get_prompt_with_fallback(
            "document_summary_prompt",
            "{doc_info}\n{summaries_text}"
        )
    
    async def enhance_figure(self, image_url: str, caption: str = "") -> str:
        """
        图片理解，返回描述文本
        
        Args:
            image_url: 图片的MinIO URL
            caption: 图片标题（可选）
            
        Returns:
            LLM 生成的图片描述文本
        """
        import time
        
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage
            
            logger.info(f"开始图片理解 | URL={image_url[:80]}... | caption={caption[:50] if caption else 'N/A'}")
            
            start_time = time.time()
            
            # 初始化视觉模型
            vision_llm = ChatOpenAI(
                api_key=self.vision_api_key,
                base_url=self.vision_model_base_url,
                model=self.vision_model_name,
                temperature=self.temperature,
                max_tokens=self.figure_max_tokens
            )
            
            logger.debug(f"LLM配置 | 模型={self.vision_model_name} | 温度={self.temperature} | max_tokens={self.figure_max_tokens}")
            
            # 构建消息
            prompt_parts = []
            if caption:
                prompt_parts.append(
                    f"该图片的标题为：'{caption}'，请以此作为分析的补充上下文。"
                )
            prompt_parts.append(self.image_prompt_template)
            prompt = "\n\n".join(prompt_parts)

            image_data_url = await self._get_image_data_url(image_url)
            if not image_data_url:
                logger.warning("图片Base64转换失败，回退使用原始URL")
                image_data_url = image_url
            
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}}
                ]
            )
            
            # 调用LLM
            response = await vision_llm.ainvoke([message])
            result_text = response.content
            duration = time.time() - start_time
            
            # 检测 [SKIP] 标记，过滤无意义图片
            if result_text.strip().startswith("[SKIP]"):
                skip_reason = result_text.strip()
                logger.info(f"图片被跳过 | 耗时={duration:.2f}s | 原因={skip_reason}")
                return ""
            
            # 清理LLM可能自行添加的非预期标记
            result_text = self._clean_llm_tags(result_text)
            
            logger.info(f"图片理解完成 | 耗时={duration:.2f}s | 描述长度={len(result_text)}")
            logger.debug(f"图片描述预览 | {result_text[:100]}...")
            return result_text
            
        except Exception as e:
            logger.error(f"图片理解失败 | URL={image_url[:80]}... | 错误={str(e)}")
            fallback = f"图片: {caption}" if caption else "图片内容"
            logger.warning(f"使用默认图片描述 | {fallback}")
            return fallback
    
    async def enhance_table(self, table_markdown: str, caption: str = "") -> str:
        """
        表格理解，返回摘要文本
        
        Args:
            table_markdown: 表格的Markdown文本
            caption: 表格标题（可选）
            
        Returns:
            LLM 生成的表格摘要文本
        """
        import time
        
        try:
            from langchain_openai import ChatOpenAI
            
            # 统计表格信息
            rows = table_markdown.count('\n') if table_markdown else 0
            logger.info(f"开始表格理解 | 行数≈{rows} | caption={caption[:50] if caption else 'N/A'}")
            
            start_time = time.time()
            
            # 初始化文本模型
            summary_llm = ChatOpenAI(
                api_key=self.summary_api_key,
                base_url=self.summary_model_base_url,
                model=self.summary_model_name,
                temperature=self.temperature,
                max_tokens=self.table_max_tokens
            )
            
            logger.debug(f"LLM配置 | 模型={self.summary_model_name} | 温度={self.temperature} | max_tokens={self.table_max_tokens}")
            
            # 构建提示词
            prompt_segments = []
            if caption:
                prompt_segments.append(
                    f"该表格的原始标题为：'{caption}'，请以此作为分析参考。"
                )
            prompt_segments.append(self.table_prompt_template)
            prompt_segments.append("表格内容：")
            prompt_segments.append(table_markdown or "（表格内容为空）")
            prompt_segments.append("请输出分析摘要：")
            prompt = "\n\n".join(prompt_segments)
            
            # 调用LLM
            response = await summary_llm.ainvoke(prompt)
            result_text = response.content
            result_text = self._clean_llm_tags(result_text)
            duration = time.time() - start_time
            
            logger.info(f"表格理解完成 | 耗时={duration:.2f}s | 摘要长度={len(result_text)}")
            logger.debug(f"表格摘要预览 | {result_text[:100]}...")
            return result_text
            
        except Exception as e:
            logger.error(f"表格理解失败 | 错误={str(e)}")
            fallback = f"表格: {caption}" if caption else "表格内容"
            logger.warning(f"使用默认表格摘要 | {fallback}")
            return fallback
    
    async def summarize_document(self, blocks: list, doc_name: str = "") -> str:
        """
        基于解析后的 blocks 生成文档级摘要

        逻辑：
        1. 筛选 Title/Text 类型 block，拼接文本，截取前 2048 字符
        2. 拼接结果 ≤ 512 字符时直接作为摘要，不调用 LLM
        3. 超过 512 字符时调用 LLM 生成摘要

        Args:
            blocks: SimpleBlock 列表（需有 type 和 content 属性或对应 key）
            doc_name: 文档名称

        Returns:
            文档摘要文本
        """
        import time

        try:
            # 1. 筛选文本类 block 并拼接
            text_parts = []
            for b in blocks:
                btype = getattr(b, "type", None) or (
                    b.get("type") or b.get("chunk_type") if isinstance(b, dict) else None
                )
                content = getattr(b, "content", None) or (b.get("content", "") if isinstance(b, dict) else "")
                if btype in ("Title", "Text") and content:
                    text_parts.append(content.strip())

            raw_text = "\n".join(text_parts)[:2048]

            if not raw_text.strip():
                default = f"文档 {doc_name}" if doc_name else "文档内容"
                logger.info(f"文档无有效文本 block，使用默认摘要")
                return default

            # 2. 短文本快速路径
            if len(raw_text) <= 512:
                logger.info(f"文档文本 ≤512 字符，直接作为摘要 | 长度={len(raw_text)}")
                return raw_text

            # 3. 调用 LLM 生成摘要
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage

            logger.info(f"开始生成文档摘要 | 文本长度={len(raw_text)} | 文档名={doc_name[:50] if doc_name else 'N/A'}")
            start_time = time.time()

            summary_llm = ChatOpenAI(
                api_key=self.summary_api_key,
                base_url=self.summary_model_base_url,
                model=self.summary_model_name,
                temperature=self.temperature,
                max_tokens=self.doc_summary_max_tokens,
            )

            doc_info = f"文档名称: {doc_name}\n" if doc_name else ""
            user_content = self.doc_summary_prompt_template.format(
                doc_info=doc_info,
                summaries_text=raw_text,
            )

            messages = [
                SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
                HumanMessage(content=user_content),
            ]

            response = await summary_llm.ainvoke(messages)
            doc_summary = response.content.strip()
            duration = time.time() - start_time

            logger.info(f"文档摘要生成完成 | 耗时={duration:.2f}s | 长度={len(doc_summary)}")
            return doc_summary

        except Exception as e:
            logger.error(f"文档摘要生成失败 | 错误={str(e)}")
            return f"文档包含 {len(blocks)} 个内容块。"

    @staticmethod
    def _clean_llm_tags(text: str) -> str:
        """清理LLM自行添加的非预期方括号标记，如[END]、[ANALYZE]等"""
        import re
        # 移除独立成行或出现在文本首尾的方括号标记（保留[SKIP]由上游处理）
        cleaned = re.sub(r'\[(?!SKIP\b)[A-Z_]+\]', '', text)
        # 清理多余空行
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    @staticmethod
    def _require_prompt(name: str) -> str:
        prompt = get_prompt(name)
        if not prompt:
            raise ValueError(f"Prompt '{name}' is not configured.")
        return prompt
    
    @staticmethod
    def _get_prompt_with_fallback(name: str, fallback: str) -> str:
        return get_prompt(name) or fallback
    
    async def _get_image_data_url(self, image_url: str) -> Optional[str]:
        # 已经是 base64 data URL，无需再通过 MinIO 转换
        if image_url.startswith("data:"):
            return image_url
        if not self.minio:
            logger.warning("未配置MinIO服务，无法获取图片Base64")
            return None
        try:
            return await asyncio.to_thread(
                self.minio.download_image_as_base64,
                image_url
            )
        except Exception as e:
            logger.error(f"图片Base64转换失败: {image_url}, 错误: {e}")
            return None

