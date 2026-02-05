"""内容增强服务（LLM）"""

import asyncio
import logging
from typing import Optional, List

from schemas.prompts import get_prompt

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

        # Prompt templates
        self.image_prompt_template = self._require_prompt("image_prompt")
        self.table_prompt_template = self._require_prompt("table_prompt")
        self.doc_summary_prompt_template = self._get_prompt_with_fallback(
            "document_summary_prompt",
            """请基于以下章节摘要生成一份200-300字的中文文档摘要，概括主题、关键论点和结论，并给出整体评价：\n\n{doc_info}\n{summaries_text}\n\n文档摘要："""
        )
        self.l1_summary_prompt_template = self._get_prompt_with_fallback(
            "l1_text_summary_prompt",
            "请为以下文本生成一个100-250字的浓缩摘要，精准概括其核心论点：\n\n---\n{text}\n---\n\n摘要："
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
                temperature=self.temperature
            )
            
            logger.debug(f"LLM配置 | 模型={self.vision_model_name} | 温度={self.temperature}")
            
            # 构建消息
            prompt_parts = []
            if caption:
                prompt_parts.append(
                    f"The image has a caption: '{caption}'. Use this as additional context for your analysis."
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
                temperature=self.temperature
            )
            
            logger.debug(f"LLM配置 | 模型={self.summary_model_name} | 温度={self.temperature}")
            
            # 构建提示词
            prompt_segments = []
            if caption:
                prompt_segments.append(
                    f"The table's original caption is: '{caption}'. Use this to guide your analysis."
                )
            prompt_segments.append(self.table_prompt_template)
            prompt_segments.append("Table content:")
            prompt_segments.append(table_markdown or "（表格内容为空）")
            prompt_segments.append("Your analysis summary:")
            prompt = "\n\n".join(prompt_segments)
            
            # 调用LLM
            response = await summary_llm.ainvoke(prompt)
            result_text = response.content
            duration = time.time() - start_time
            
            logger.info(f"表格理解完成 | 耗时={duration:.2f}s | 摘要长度={len(result_text)}")
            logger.debug(f"表格摘要预览 | {result_text[:100]}...")
            return result_text
            
        except Exception as e:
            logger.error(f"表格理解失败 | 错误={str(e)}")
            fallback = f"表格: {caption}" if caption else "表格内容"
            logger.warning(f"使用默认表格摘要 | {fallback}")
            return fallback
    
    async def summarize_document(self, l1_summaries: List[str], doc_name: str = "") -> str:
        """
        生成文档级摘要
        
        Args:
            l1_summaries: L1单元的摘要列表（图、表、章节）
            doc_name: 文档名称
            
        Returns:
            文档摘要文本
        """
        import time
        
        try:
            from langchain_openai import ChatOpenAI
            
            logger.info(f"开始生成文档摘要 | L1单元数={len(l1_summaries)} | 文档名={doc_name[:50] if doc_name else 'N/A'}")
            
            start_time = time.time()
            
            # 初始化文本模型
            summary_llm = ChatOpenAI(
                api_key=self.summary_api_key,
                base_url=self.summary_model_base_url,
                model=self.summary_model_name,
                temperature=self.temperature
            )
            
            logger.debug(f"LLM配置 | 模型={self.summary_model_name} | 温度={self.temperature}")
            
            # 构建提示词
            doc_info = f"文档名称: {doc_name}\n" if doc_name else ""
            summaries_text = "\n".join(
                [f"{i+1}. {s}" for i, s in enumerate(l1_summaries)]
            ) or "暂无章节摘要"
            
            prompt = self.doc_summary_prompt_template.format(
                doc_info=doc_info,
                summaries_text=summaries_text
            )
            
            # 调用LLM
            input_length = len(prompt)
            logger.debug(f"LLM输入 | 长度={input_length}")
            
            response = await summary_llm.ainvoke(prompt)
            doc_summary = response.content.strip()
            duration = time.time() - start_time
            
            logger.info(f"文档摘要生成完成 | 耗时={duration:.2f}s | 长度={len(doc_summary)}")
            logger.debug(f"文档摘要预览 | {doc_summary[:150]}...")
            return doc_summary
            
        except Exception as e:
            logger.error(f"文档摘要生成失败 | 错误={str(e)}")
            default_summary = f"文档包含{len(l1_summaries)}个主要章节和图表。"
            logger.warning(f"使用默认文档摘要 | {default_summary}")
            return default_summary

    async def summarize_l1_text(self, text: str) -> str:
        """
        针对L1文本块生成浓缩摘要
        """
        import time

        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return ""

        try:
            from langchain_openai import ChatOpenAI

            start_time = time.time()
            summary_llm = ChatOpenAI(
                api_key=self.summary_api_key,
                base_url=self.summary_model_base_url,
                model=self.summary_model_name,
                temperature=self.temperature
            )

            prompt = self.l1_summary_prompt_template.format(text=cleaned_text[:4000])
            response = await summary_llm.ainvoke(prompt)
            summary_text = response.content.strip()
            duration = time.time() - start_time

            logger.info(f"L1文本摘要生成完成 | 文本长度={len(cleaned_text)} | 摘要长度={len(summary_text)} | 耗时={duration:.2f}s")
            return summary_text
        except Exception as e:
            logger.error(f"L1文本摘要生成失败: {e}")
            fallback = cleaned_text[:250]
            logger.warning("使用默认L1摘要片段")
            return fallback
    
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

