import logging
import json
import time
import threading
from typing import List, Dict, Optional
import crud.database as db
from services.storage import minio_storage

logger = logging.getLogger(__name__)

class SessionService:
    """会话服务类"""
    
    @staticmethod
    def create_new_session(user_id: str, title: Optional[str] = None) -> dict:
        """创建新会话"""
        if not title:
            title = f"Chat {time.strftime('%Y-%m-%d %H:%M')}"
        
        session_id = db.create_session(user_id=user_id, title=title)
        if session_id:
            return {'session_id': session_id, 'title': title}
        return {"error": "创建会话失败"}

    @staticmethod
    def get_user_sessions(user_id: str) -> List[Dict]:
        """获取用户的所有会话"""
        return db.get_sessions(user_id)

    @staticmethod
    def get_session_messages(session_id: str) -> List[Dict]:
        """获取会话的所有消息（包含message_id和关联文档）"""
        from crud.document_crud import DocumentCRUD
        from crud.database import SessionLocal
        
        messages = db.get_messages(session_id)
        for msg in messages:
            if msg.get('image_url') and isinstance(msg['image_url'], str):
                try:
                    # 尝试将 image_url 从JSON字符串解析为列表
                    msg['image_url'] = json.loads(msg['image_url'])
                except json.JSONDecodeError:
                    # 如果解析失败，说明它可能是一个单独的URL字符串，将其放入列表中
                    msg['image_url'] = [msg['image_url']]
            
            # 将 MinIO URL 转换为前端可访问的代理 URL
            if msg.get('image_url') and isinstance(msg['image_url'], list) and minio_storage:
                proxy_urls = []
                for url in msg['image_url']:
                    proxy_path = minio_storage.minio_url_to_proxy_path(url)
                    proxy_urls.append(proxy_path if proxy_path else url)
                msg['image_url'] = proxy_urls
            
            # 为用户消息查询关联的文档
            if msg.get('role') == 'user' and msg.get('message_id'):
                with SessionLocal() as db_session:
                    docs = DocumentCRUD.get_documents_by_message_id(db_session, msg['message_id'])
                    msg['attached_documents'] = [
                        {
                            'doc_id': doc.id,
                            'file_name': doc.file_name,
                            'document_type': doc.document_type.value if doc.document_type else None
                        }
                        for doc in docs
                    ]
        
        logger.info(f"获取session_id:{session_id}的会话消息: {len(messages)}条")
        return messages

    @staticmethod
    def add_user_message(session_id: str, content: str, image_urls: Optional[List[str]] = None) -> Optional[str]:
        """
        添加用户消息到会话
        
        Args:
            session_id: 会话ID
            content: 消息文本内容
            image_urls: 可选，图片的MinIO URL列表
        
        Returns:
            消息ID
        """
        image_urls_json = None
        if image_urls:
            image_urls_json = json.dumps(image_urls)
            
        return db.add_message(session_id, 'user', content, image_url=image_urls_json)

    @staticmethod
    def add_assistant_message(session_id: str, content: str, thinking_content: Optional[str] = None) -> Optional[str]:
        """
        添加助手消息到会话
        
        Args:
            session_id: 会话ID
            content: 消息内容
            thinking_content: 可选，思考过程内容（推理模型）
        
        Returns:
            消息ID
        """
        return db.add_message(session_id, 'assistant', content, thinking_content=thinking_content)

    @staticmethod
    def get_and_clean_history(session_id: str) -> Dict:
        """
        获取并清理会话历史，将图片URL转换为base64
        
        处理逻辑：
        1. 加载历史消息
        2. 清理assistant消息的JSON结构
        3. 将user消息中的image_url(s)转换为base64编码
        4. 检测历史中是否包含图片
        5. 返回包含消息列表和图片标志的字典
        
        Returns:
            {
                "messages": List[dict],  # 清理后的消息列表
                "has_images": bool       # 是否包含图片
            }
        """
        history_messages = db.get_messages(session_id)
        cleaned_history = []
        has_images = False  # 标记是否有图片
        
        for msg in history_messages:
            if msg.get('role') == 'assistant':
                # 清理助手消息
                try:
                    content_data = json.loads(msg['content'])
                    cleaned_msg = {'role': 'assistant', 'content': content_data.get('text', '')}
                    cleaned_history.append(cleaned_msg)
                except (json.JSONDecodeError, TypeError):
                    cleaned_history.append(msg)
            else:
                # 处理用户消息，转换图片URL为base64
                cleaned_msg = {'role': 'user', 'content': msg.get('content', '')}
                
                # 如果有图片URL，转换为base64
                image_urls = msg.get('image_url')
                if image_urls and minio_storage:
                    # 确保 image_urls 是一个列表
                    if isinstance(image_urls, str):
                        try:
                            image_urls = json.loads(image_urls)
                        except json.JSONDecodeError:
                            image_urls = [image_urls] # 兼容旧的单个URL格式
                    
                    if isinstance(image_urls, list) and len(image_urls) > 0:
                        base64_images = []
                        for url in image_urls:
                            try:
                                base64_image = minio_storage.download_image_as_base64(url)
                                if base64_image:
                                    base64_images.append(base64_image)
                                    logger.info(f"历史消息图片已转换为base64: {url[:50]}...")
                                else:
                                    logger.warning(f"历史消息图片转换失败: {url}")
                            except Exception as e:
                                logger.error(f"处理历史消息图片时出错: {e}")
                        
                        if base64_images:
                            has_images = True  # 只有实际成功转换了图片才标记
                            cleaned_msg['image_urls'] = base64_images

                cleaned_history.append(cleaned_msg)
        
        # 返回包含消息列表和图片标志的字典
        return {
            "messages": cleaned_history,
            "has_images": has_images
        }
    
    @staticmethod
    def delete_messages_after_and_cleanup(session_id: str, message_id: str) -> int:
        """
        删除指定消息之后的所有消息，并清理相关的MinIO文件
        
        Args:
            session_id: 会话ID
            message_id: 目标消息ID
        
        Returns:
            删除的消息数量
        """
        # 删除数据库中的消息
        deleted_messages = db.delete_messages_after(session_id, message_id)
        
        if not deleted_messages:
            return 0
        
        # 清理MinIO中的图片文件
        for msg in deleted_messages:
            if msg.get('image_url'):
                SessionService._cleanup_message_images(msg['image_url'])
        
        logger.info(f"已删除并清理 {len(deleted_messages)} 条消息")
        return len(deleted_messages)
    
    @staticmethod
    def update_user_message(message_id: str, new_content: str, new_image_urls: Optional[List[str]] = None) -> bool:
        """
        更新用户消息内容
        
        Args:
            message_id: 消息ID
            new_content: 新的消息内容
            new_image_urls: 新的图片URL列表（MinIO URL格式）
        
        Returns:
            是否更新成功
        """
        # 先获取旧消息，用于清理被移除的图片
        old_message = db.get_message_by_id(message_id)
        
        # 转换为JSON字符串
        image_urls_json = None
        if new_image_urls:
            image_urls_json = json.dumps(new_image_urls)
        
        # 更新消息
        success = db.update_user_message(message_id, new_content, image_urls_json)
        
        if success and old_message and old_message.get('image_url'):
            # 只删除被移除的图片（旧的有但新的没有的），而不是全部删除
            old_urls = old_message['image_url']
            if isinstance(old_urls, str):
                try:
                    old_urls = json.loads(old_urls)
                except json.JSONDecodeError:
                    old_urls = [old_urls]
            
            # 用 object_path 做比较，避免签名参数/格式差异导致误判
            new_paths_set = set()
            if new_image_urls and minio_storage:
                for u in new_image_urls:
                    p = minio_storage.extract_object_path(u)
                    if p:
                        new_paths_set.add(p)
            
            removed_urls = []
            if minio_storage:
                for url in old_urls:
                    old_path = minio_storage.extract_object_path(url)
                    if old_path and old_path not in new_paths_set:
                        removed_urls.append(url)
            
            if removed_urls:
                logger.info(f"清理被移除的图片: {len(removed_urls)} 张")
                SessionService._cleanup_message_images(removed_urls)
        
        return success
    
    @staticmethod
    def delete_message_and_cleanup(message_id: str) -> bool:
        """
        删除单条消息并清理MinIO文件
        
        Args:
            message_id: 消息ID
        
        Returns:
            是否删除成功
        """
        deleted_message = db.delete_message(message_id)
        
        if not deleted_message:
            return False
        
        # 清理MinIO中的图片文件
        if deleted_message.get('image_url'):
            SessionService._cleanup_message_images(deleted_message['image_url'])
        
        logger.info(f"已删除并清理消息: {message_id}")
        return True
    
    @staticmethod
    def _cleanup_message_images(image_url_data):
        """
        清理消息关联的图片文件
        
        Args:
            image_url_data: 图片URL数据（可能是JSON字符串、单个URL字符串或URL列表）
        """
        if not image_url_data or not minio_storage:
            return
        
        try:
            # 解析图片URL
            image_urls = []
            if isinstance(image_url_data, list):
                image_urls = image_url_data
            elif isinstance(image_url_data, str):
                try:
                    image_urls = json.loads(image_url_data)
                except json.JSONDecodeError:
                    image_urls = [image_url_data]
            
            # 删除每个图片文件
            for url in image_urls:
                try:
                    # 统一转换为 MinIO URL 再解析
                    minio_url = minio_storage.proxy_path_to_minio_url(url) if not url.startswith('http') else url
                    if not minio_url:
                        logger.warning(f"无法解析图片URL，跳过删除: {url}")
                        continue
                    
                    from urllib.parse import urlparse
                    parsed_url = urlparse(minio_url)
                    path_parts = parsed_url.path.strip('/').split('/')
                    
                    if len(path_parts) >= 2:
                        bucket = path_parts[0]
                        object_path = '/'.join(path_parts[1:])
                        minio_storage.delete_file(bucket, object_path)
                        logger.info(f"已删除图片文件: {bucket}/{object_path}")
                except Exception as e:
                    logger.error(f"删除图片文件失败: {url}, 错误: {e}")
        
        except Exception as e:
            logger.error(f"清理图片文件时出错: {e}")

    @staticmethod
    def update_session_title(session_id: str, title: str) -> bool:
        """更新会话标题"""
        return db.update_session_title(session_id, title)

    @staticmethod
    def generate_session_title(session_id: str, user_message: str) -> Optional[str]:
        """
        使用 LLM 根据用户第一条消息生成会话标题，并更新到数据库。
        在后台线程中异步执行，不阻塞主流程。
        
        Args:
            session_id: 会话ID
            user_message: 用户的第一条消息内容
            
        Returns:
            生成的标题，失败返回 None
        """
        from services.llm_service import LLMService
        from crud.config_manager import config
        
        try:
            chat_model_config = config.get_default_chat_model()
            if not chat_model_config:
                logger.warning("未找到默认模型配置，无法生成会话标题")
                return None
            
            base_url = chat_model_config.get("base_url")
            model_name = chat_model_config.get("name")
            api_key = chat_model_config.get("api_key")
            
            if not all([base_url, model_name, api_key]):
                logger.warning("模型配置不完整，无法生成会话标题")
                return None
            
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=15)
            
            # 截取用户消息前500字符，避免过长
            truncated_message = user_message[:500] if len(user_message) > 500 else user_message
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你的任务是为一段对话生成一个简短的主题标题（不超过15个字）。\n"
                            "要求：\n"
                            "1. 标题应概括用户想做什么或想聊什么话题，例如：'Python排序算法'、'周末旅行计划'、'PDF文档总结'\n"
                            "2. 使用名词短语或动宾短语，不要使用疑问句或祈使句\n"
                            "3. 不要回答用户的问题，不要打招呼，不要解释\n"
                            "4. 如果用户只是简单打招呼（如'你好'、'hi'），标题为'闲聊'\n"
                            "5. 只输出标题本身，不加引号、标点或任何额外文字"
                        )
                    },
                    {
                        "role": "user",
                        "content": truncated_message
                    }
                ],
                stream=False,
                temperature=0.3,
                max_tokens=50,
            )
            
            title = response.choices[0].message.content.strip()
            # 清理可能的引号
            title = title.strip('"\'""''')
            # 限制长度
            if len(title) > 50:
                title = title[:50]
            if not title:
                title = user_message[:10] or "新对话"
            
            # 更新数据库
            db.update_session_title(session_id, title)
            logger.info(f"会话标题已生成: session_id={session_id}, title={title}")
            return title
            
        except Exception as e:
            logger.error(f"生成会话标题失败: {e}")
            return None

    @staticmethod
    def generate_session_title_async(session_id: str, user_message: str):
        """
        异步（后台线程）生成会话标题，不阻塞主请求。
        """
        def _run():
            try:
                SessionService.generate_session_title(session_id, user_message)
            except Exception as e:
                logger.error(f"后台生成会话标题失败: {e}")
        
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
