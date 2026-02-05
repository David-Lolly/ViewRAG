import logging
import json
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional, Union
from fastapi.responses import StreamingResponse
from langchain_core.documents import Document

from utils.search import Search, Crawl, Retrieval_v2, generate, search_generate, Retrieval_v1
from crud.config_manager import config

logger = logging.getLogger(__name__)

class SearchService:
    """搜索服务类"""
    
    @staticmethod
    async def stream_json(data_type: str, content: Any) -> str:
        """生成流式JSON响应"""
        message = {
            "type": data_type,
            "payload": content
        }
        return json.dumps(message, ensure_ascii=False) + '\n'

    @staticmethod
    async def direct_llm_response(
        query: str, 
        chat_history: Union[Dict, List[dict]],  # 支持新的Dict格式和旧的List格式
        selected_model: Optional[str] = None, 
    ) -> AsyncGenerator[str, None]:
        """直接LLM回答，不进行联网搜索
        
        Args:
            query: 用户问题
            chat_history: 对话历史，支持两种格式：
                - Dict: {"messages": List[dict], "has_images": bool}
                - List[dict]: 旧格式，向后兼容
            selected_model: 选择的模型名称
            has_images: 是否包含图片
        """
        try:
            # 优先使用多图列表
            # images_to_pass = images if images else ([image_url] if image_url else None)
            
            response_generator = generate(
                chat_history=chat_history,  # 传递原始格式，generate函数内部会处理
                selected_model=selected_model, 
            )
            if response_generator:
                for chunk in response_generator:
                    chunk_str = chunk.decode('utf-8', errors='ignore')
                    # 重要：不要对整个chunk_str使用.strip()，会导致Markdown格式丢失换行符
                    if not chunk_str:
                        continue
                    
                    try:
                        # 尝试解析为JSON，检查是否是预定义的错误格式
                        # 只在解析JSON时对副本使用strip
                        chunk_data = json.loads(chunk_str.strip())
                        if isinstance(chunk_data, dict) and chunk_data.get("type") == "error":
                            yield chunk.decode('utf-8')  # 直接转发错误信息的原始字符串
                            continue
                    except (json.JSONDecodeError, AttributeError):
                        # 不是JSON格式或没有type字段，视为正常内容块
                        pass
                    
                    # 传递原始chunk_str（保留换行符）
                    yield await SearchService.stream_json("answer_chunk", chunk_str)
                    await asyncio.sleep(0)
        except Exception as e:
            logger.error(f"直接LLM搜索出错: {e}")
            yield await SearchService.stream_json("error", f"发生错误: {e}")

    @staticmethod
    async def web_search(query: str, chat_history: Union[Dict, List[dict]], selected_model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """联网搜索
        
        Args:
            query: 用户问题
            chat_history: 对话历史，支持两种格式：
                - Dict: {"messages": List[dict], "has_images": bool}
                - List[dict]: 旧格式，向后兼容
            selected_model: 选择的模型名称
        """
        try:
            yield await SearchService.stream_json("process", "正在分析问题...")
            await asyncio.sleep(0)

            search_instance = Search()
            search_plan_data, search_results = await search_instance.search(query, chat_history=chat_history)

            if not search_plan_data:
                yield await SearchService.stream_json("process", "搜索计划生成失败，直接回答...")
                await asyncio.sleep(0)
                async for chunk in SearchService.direct_llm_response(query, chat_history, selected_model):
                    yield chunk
                return

            plan = search_plan_data.get('search_plan', {})
            foundational_queries = plan.get('foundational_queries', [])
            expansion_queries = plan.get('expansion_deep_dive_queries', [])

            if not (foundational_queries or expansion_queries):
                yield await SearchService.stream_json("process", "查询生成失败直接回答，直接回答...")
                await asyncio.sleep(0)
                async for chunk in SearchService.direct_llm_response(query, chat_history, selected_model, image_url=None):
                    yield chunk
                return

            key_entities = search_plan_data.get('query_analysis', {}).get('key_entities', [])
            yield await SearchService.stream_json("process", f"搜索关键词: {key_entities}")
            await asyncio.sleep(0)

            crawler = Crawl()
            web_pages = crawler.crawl(search_results)
            crawler.close()

            yield await SearchService.stream_json("process", f"搜索完成. 找到 {sum(len(v) for v in web_pages.values())} 个网页.")
            await asyncio.sleep(0)

            retrieval_version = config.get("retrieval_version", "v2").lower()
            logger.info(f"检索版本: {retrieval_version}")
            
            if retrieval_version == "v2":
                retrieval_v2 = Retrieval_v2()
                context = retrieval_v2.retrieve(search_plan_data, web_pages)
            else:
                retrieval_v1 = Retrieval_v1()
                all_web_pages = [page for pages in web_pages.values() for page in pages]
                context = retrieval_v1.retrieve(queries=[query], search_plan_data=search_plan_data, web_pages=all_web_pages)

            # search_generate函数内部会处理chat_history的格式转换
            response_generator = search_generate(query, context, search_plan_data, chat_history=chat_history, selected_model=selected_model)
            assistant_response_text = ""
            
            if response_generator:
                for chunk in response_generator:
                    chunk_str = ""
                    if isinstance(chunk, bytes):
                        chunk_str = chunk.decode('utf-8', errors='ignore')
                    else:
                        chunk_str = str(chunk)
                    
                    # 尝试解析，判断是否为错误信息
                    try:
                        chunk_data = json.loads(chunk_str.strip())
                        if isinstance(chunk_data, dict) and chunk_data.get("type") == "error":
                            yield chunk_str  # 直接转发错误信息
                            continue
                    except (json.JSONDecodeError, AttributeError):
                        # 不是可解析的错误JSON，则视为正常内容
                        pass
                    
                    assistant_response_text += chunk_str
                    yield await SearchService.stream_json("answer_chunk", chunk_str)
                    await asyncio.sleep(0)

            # 处理参考来源
            all_pages = []
            if isinstance(context, dict):
                for results in context.values():
                    all_pages.extend(results)
            else:
                for item in context:
                    if isinstance(item, Document):
                        all_pages.append({
                            'title': item.metadata.get('title', ''),
                            'link': item.metadata.get('url', '')
                        })
                    elif isinstance(item, dict):
                        all_pages.append(item)

            unique_refs = {
                (page.get('title'), page.get('link')): {page.get('title'): page.get('link')}
                for page in all_pages if page.get('title') and page.get('link')
            }
            references = list(unique_refs.values())
            logger.info(f"参考来源: {json.dumps(references, ensure_ascii=False, indent=2)}")
            
            if references:
                yield await SearchService.stream_json("reference", references)
                await asyncio.sleep(0)

            # 返回最终结果数据以供保存
            final_db_content = {"text": assistant_response_text, "references": references}
            yield await SearchService.stream_json("final_content", final_db_content)

        except Exception as e:
            logger.error(f"搜索处理过程中出错: {e}", exc_info=True)
            yield await SearchService.stream_json("error", f"发生错误: {e}")
