"""
MinIO文件存储服务

提供图片和文档文件的上传、下载、删除等功能
"""

import logging
import hashlib
import os
import json
import yaml
import base64
from pathlib import Path
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, Optional, Any
from urllib.parse import urlparse
from minio import Minio
from minio.error import S3Error
from PIL import Image

logger = logging.getLogger(__name__)


class MinIOStorage:
    """MinIO存储服务类"""
    
    def __init__(self):
        """初始化MinIO客户端"""
        # 从config.yaml加载配置
        config_path = Path(__file__).parent.parent / "config.yaml"
        minio_config = {}
        
        try:
            if config_path.is_file():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    minio_config = config.get('MinIO_Config', {})
            # 如果是目录或不存在，则跳过文件读取，直接使用空配置（后续会回退到环境变量）
        except Exception as e:
            logger.warning(f"无法加载config.yaml中的MinIO配置: {e}")
        
        # 优先使用环境变量，否则使用config.yaml
        # V2性能优化：显式使用127.0.0.1替代localhost，避免IPv6/IPv4解析延迟
        self.endpoint = os.getenv("MINIO_ENDPOINT", minio_config.get("ENDPOINT", "127.0.0.1:9000"))
        self.access_key = os.getenv("MINIO_ROOT_USER", minio_config.get("ACCESS_KEY", "minioadmin"))
        self.secret_key = os.getenv("MINIO_ROOT_PASSWORD", minio_config.get("SECRET_KEY", "minioadmin"))
        self.secure = os.getenv("MINIO_SECURE", str(minio_config.get("SECURE", False))).lower() == "true"
        
        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            logger.info(f"MinIO客户端初始化成功: {self.endpoint}")
        except Exception as e:
            logger.error(f"MinIO客户端初始化失败: {e}")
            raise
        
        # 存储桶名称
        self.image_bucket = "viewrag-chat-images"
        self.doc_bucket = "viewrag-documents"
        self.thumb_bucket = "viewrag-thumbnails"
        
        # 确保存储桶存在
        self._ensure_buckets()
    
    def _ensure_buckets(self):
        """确保所有必需的存储桶存在"""
        buckets = [self.image_bucket, self.doc_bucket, self.thumb_bucket]
        
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info(f"创建MinIO存储桶: {bucket}")
                    
                    # 设置公开读权限策略
                    policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"AWS": "*"},
                                "Action": ["s3:GetObject"],
                                "Resource": [f"arn:aws:s3:::{bucket}/*"]
                            }
                        ]
                    }
                    self.client.set_bucket_policy(bucket, json.dumps(policy))
                    logger.info(f"设置存储桶 {bucket} 为公开读")
                else:
                    logger.info(f"存储桶已存在: {bucket}")
            except S3Error as e:
                logger.error(f"创建/检查存储桶失败 {bucket}: {e}")
                # 不抛出异常，允许继续运行
    
    def upload_image(
        self, 
        upload_file: 'UploadFile',  # Use forward reference for UploadFile
        user_id: str, 
        session_id: str
    ) -> Dict[str, Any]:
        """
        上传聊天图片到MinIO (V2流式版本)
        
        Args:
            upload_file: FastAPI的UploadFile对象 (包含文件流)
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            包含文件ID、存储路径、URL等信息的字典
        """
        try:
            import time
            start_time = time.time()
            
            # 从UploadFile对象获取信息
            filename = upload_file.filename or 'image.webp'
            content_type = upload_file.content_type or 'image/webp'
            file_stream = upload_file.file
            
            # 需要先读取流来计算哈希和大小，这是MinIO的限制
            # 为了避免将大文件完全读入内存，可以分块读取
            md5_hash = hashlib.md5()
            file_size = 0
            # 将文件指针移到开头
            file_stream.seek(0)
            while chunk := file_stream.read(8192):
                md5_hash.update(chunk)
                file_size += len(chunk)
            # 再次将文件指针移到开头以供上传
            file_stream.seek(0)
            
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_hash_hex = md5_hash.hexdigest()[:8]
            ext = os.path.splitext(filename)[1] or '.webp'
            storage_filename = f"{timestamp}_{file_hash_hex}{ext}"
            
            # 存储路径: user_id/session_id/filename
            storage_path = f"{user_id}/{session_id}/{storage_filename}"
            
            # 流式上传到MinIO
            upload_start = time.time()
            self.client.put_object(
                bucket_name=self.image_bucket,
                object_name=storage_path,
                data=file_stream, # 直接传递文件流
                length=file_size, # 必须提供文件大小
                content_type=content_type
            )
            logger.info(f"MinIO流式上传耗时: {time.time() - upload_start:.2f}s")
            
            # 生成访问URL
            url = self.get_file_url(self.image_bucket, storage_path)
            
            total_time = time.time() - start_time
            logger.info(f"图片流式上传成功: {storage_path}, 总耗时: {total_time:.2f}s, 大小: {file_size / 1024:.1f}KB")
            
            return {
                'file_id': f"{session_id}_{storage_filename}",
                'storage_path': storage_path,
                'url': url,
                'file_size': file_size,
                'thumbnail_url': None,
                'content_type': content_type
            }
            
        except S3Error as e:
            logger.error(f"流式上传图片到MinIO失败: {e}")
            raise
        except Exception as e:
            logger.error(f"流式上传图片时发生错误: {e}")
            raise
    
    
    
    def upload_document(
        self, 
        file_data: bytes, 
        user_id: str, 
        session_id: str,
        filename: str, 
        content_type: str
    ) -> Dict[str, str]:
        """
        上传文档文件到MinIO
        
        Args:
            file_data: 文件二进制数据
            user_id: 用户ID
            session_id: 会话ID
            filename: 原始文件名
            content_type: MIME类型
        
        Returns:
            包含文件ID、存储路径、URL等信息的字典
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_hash = hashlib.md5(file_data).hexdigest()[:8]
            
            # 保留原始文件名（进行安全处理）
            safe_filename = self._sanitize_filename(filename)
            storage_filename = f"{timestamp}_{file_hash}_{safe_filename}"
            
            # 存储路径
            storage_path = f"{user_id}/{session_id}/{storage_filename}"
            
            # 上传到MinIO
            self.client.put_object(
                bucket_name=self.doc_bucket,
                object_name=storage_path,
                data=BytesIO(file_data),
                length=len(file_data),
                content_type=content_type
            )
            
            logger.info(f"文档上传成功: {storage_path}")
            
            url = self.get_file_url(self.doc_bucket, storage_path)
            
            return {
                'file_id': f"{session_id}_{storage_filename}",
                'storage_path': storage_path,
                'url': url,
                'file_size': len(file_data),
                'content_type': content_type
            }
            
        except S3Error as e:
            logger.error(f"上传文档到MinIO失败: {e}")
            raise
        except Exception as e:
            logger.error(f"上传文档时发生错误: {e}")
            raise
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除不安全字符
        
        Args:
            filename: 原始文件名
        
        Returns:
            安全的文件名
        """
        # 移除路径分隔符和其他不安全字符
        unsafe_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
        safe_name = filename
        
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')
        
        # 限制文件名长度
        if len(safe_name) > 200:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:200-len(ext)] + ext
        
        return safe_name
    
    def get_file_url(self, bucket: str, object_name: str, expires: int = 3600) -> str:
        """
        获取文件访问URL
        
        Args:
            bucket: 存储桶名称
            object_name: 对象名称
            expires: URL过期时间（秒），默认1小时
        
        Returns:
            文件访问URL
        """
        try:
            # 如果配置了公开访问，使用直接URL
            if not self.secure and self.endpoint == "localhost:9000":
                # 开发环境使用直接URL
                return f"http://{self.endpoint}/{bucket}/{object_name}"
            else:
                # 生产环境使用预签名URL
                url = self.client.presigned_get_object(
                    bucket_name=bucket,
                    object_name=object_name,
                    expires=timedelta(seconds=expires)
                )
                return url
        except S3Error as e:
            logger.error(f"生成文件URL失败: {e}")
            # 回退到直接URL
            return f"http://{self.endpoint}/{bucket}/{object_name}"
    
    def delete_file(self, bucket: str, object_name: str):
        """
        删除MinIO中的文件
        
        Args:
            bucket: 存储桶名称
            object_name: 对象名称
        """
        try:
            self.client.remove_object(bucket, object_name)
            logger.info(f"删除文件成功: {bucket}/{object_name}")
        except S3Error as e:
            logger.error(f"删除文件失败 {bucket}/{object_name}: {e}")
            raise
    
    def delete_session_files(self, user_id: str, session_id: str):
        """
        删除会话的所有文件
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
        """
        prefix = f"{user_id}/{session_id}/"
        
        for bucket in [self.image_bucket, self.doc_bucket, self.thumb_bucket]:
            try:
                objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
                deleted_count = 0
                
                for obj in objects:
                    self.client.remove_object(bucket, obj.object_name)
                    deleted_count += 1
                
                if deleted_count > 0:
                    logger.info(f"删除会话文件: {bucket}/{prefix}, 共 {deleted_count} 个文件")
                    
            except S3Error as e:
                logger.error(f"删除会话文件失败 {bucket}/{prefix}: {e}")
    
    def get_storage_stats(self, user_id: Optional[str] = None) -> Dict:
        """
        获取存储使用统计
        
        Args:
            user_id: 可选，指定用户ID
        
        Returns:
            存储统计信息
        """
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'images_count': 0,
                'images_size': 0,
                'docs_count': 0,
                'docs_size': 0
            }
            
            prefix = f"{user_id}/" if user_id else ""
            
            # 统计图片
            for obj in self.client.list_objects(self.image_bucket, prefix=prefix, recursive=True):
                stats['images_count'] += 1
                stats['images_size'] += obj.size
            
            # 统计文档
            for obj in self.client.list_objects(self.doc_bucket, prefix=prefix, recursive=True):
                stats['docs_count'] += 1
                stats['docs_size'] += obj.size
            
            stats['total_files'] = stats['images_count'] + stats['docs_count']
            stats['total_size'] = stats['images_size'] + stats['docs_size']
            
            return stats
            
        except S3Error as e:
            logger.error(f"获取存储统计失败: {e}")
            return {}
    
    def minio_url_to_proxy_path(self, image_url: str) -> Optional[str]:
        """
        将 MinIO 图片 URL 转换为后端代理路径，供前端通过 /api/images/chat/... 访问。
        
        Args:
            image_url: MinIO 图片 URL，如 http://127.0.0.1:9000/viewrag-chat-images/user/session/file.webp
        
        Returns:
            代理路径，如 /api/images/chat/user/session/file.webp；无法解析时返回 None
        """
        try:
            if not image_url:
                return None
            
            parsed_url = urlparse(image_url)
            path_parts = parsed_url.path.strip('/').split('/', 1)
            
            if len(path_parts) < 2:
                logger.warning(f"无法解析 MinIO URL: {image_url}")
                return None
            
            bucket = path_parts[0]
            object_path = path_parts[1]
            
            if bucket == self.image_bucket:
                return f"/api/images/chat/{object_path}"
            elif bucket == self.doc_bucket:
                return f"/api/images/{object_path}"
            else:
                logger.warning(f"未知的 bucket: {bucket}, URL: {image_url}")
                return None
        except Exception as e:
            logger.error(f"转换 MinIO URL 为代理路径失败: {image_url}, 错误: {e}")
            return None

    def proxy_path_to_minio_url(self, proxy_path: str) -> Optional[str]:
        """
        将前端代理路径反向转换为 MinIO 原始 URL。
        
        Args:
            proxy_path: 代理路径，如 /api/images/chat/user/session/file.webp
        
        Returns:
            MinIO URL，如 http://127.0.0.1:9000/viewrag-chat-images/user/session/file.webp
            无法解析时返回 None
        """
        try:
            if not proxy_path:
                return None
            
            # 已经是 MinIO URL，直接返回
            if proxy_path.startswith('http'):
                return proxy_path
            
            if proxy_path.startswith('/api/images/chat/'):
                object_path = proxy_path[len('/api/images/chat/'):]
                bucket = self.image_bucket
            elif proxy_path.startswith('/api/images/'):
                object_path = proxy_path[len('/api/images/'):]
                bucket = self.doc_bucket
            else:
                logger.warning(f"无法识别的代理路径格式: {proxy_path}")
                return None
            
            protocol = "https" if self.secure else "http"
            return f"{protocol}://{self.endpoint}/{bucket}/{object_path}"
        except Exception as e:
            logger.error(f"代理路径转换为MinIO URL失败: {proxy_path}, 错误: {e}")
            return None

    def extract_object_path(self, url: str) -> Optional[str]:
        """
        从任意格式的图片URL中提取 object_path（不含bucket），用于唯一标识比较。
        
        支持格式：
        - MinIO URL: http://127.0.0.1:9000/viewrag-chat-images/user/session/file.webp?签名参数
        - 预签名URL: 同上（带查询参数）
        - 代理路径: /api/images/chat/user/session/file.webp
        
        Returns:
            object_path，如 user/session/file.webp；无法解析返回 None
        """
        try:
            if not url:
                return None
            
            if url.startswith('/api/images/chat/'):
                return url[len('/api/images/chat/'):]
            elif url.startswith('/api/images/'):
                return url[len('/api/images/'):]
            elif url.startswith('http'):
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.strip('/').split('/', 1)
                if len(path_parts) >= 2:
                    return path_parts[1]
            return None
        except Exception:
            return None

    def download_image_as_base64(self, image_url: str) -> Optional[str]:
        """
        从MinIO下载图片并转换为base64编码
        
        Args:
            image_url: 图片的MinIO URL或存储路径
        
        Returns:
            base64编码的图片字符串（带data URL前缀），失败返回None
        """
        try:
            bucket = self.image_bucket # 默认bucket
            object_path = ""
            
            # V2-Fix: 正确解析URL，去除查询参数
            if image_url.startswith('http'):
                parsed_url = urlparse(image_url)
                # 路径通常是 /<bucket_name>/<object_path>
                path_parts = parsed_url.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    bucket = path_parts[0]
                    object_path = '/'.join(path_parts[1:])
                else:
                    raise ValueError(f"无法从URL解析bucket和object path: {image_url}")
            else:
                # 兼容直接传递对象路径的情况
                object_path = image_url
            
            # 从MinIO下载文件
            response = self.client.get_object(bucket, object_path)
            image_data = response.read()
            response.close()
            response.release_conn()
            
            # 检测图片类型
            mime_type = 'image/jpeg'
            if object_path.lower().endswith('.png'):
                mime_type = 'image/png'
            elif object_path.lower().endswith('.gif'):
                mime_type = 'image/gif'
            elif object_path.lower().endswith('.webp'):
                mime_type = 'image/webp'
            
            # 转换为base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            # 返回完整的data URL
            data_url = f"data:{mime_type};base64,{base64_data}"
            
            logger.info(f"图片转换为base64成功: {object_path}, 大小: {len(image_data)} bytes")
            return data_url
            
        except S3Error as e:
            logger.error(f"从MinIO下载图片失败: {image_url}, 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"图片转base64失败: {image_url}, 错误: {e}")
            return None
    
    # ==================== RAG文档存储方法 ====================
    
    async def upload_document_stream(
        self,
        file_stream,
        file_size: int,
        filename: str,
        content_type: str,
        owner_id: str,
        owner_type: str  # 'session' or 'kb'
    ) -> Dict[str, Any]:
        """
        流式上传文档文件到MinIO（RAG系统专用）
        
        Args:
            file_stream: 文件流对象
            file_size: 文件大小
            filename: 原始文件名
            content_type: MIME类型
            owner_id: 所有者ID（session_id 或 kb_id）
            owner_type: 所有者类型（'session' 或 'kb'）
        
        Returns:
            包含文件信息的字典
        """
        try:
            import time
            start_time = time.time()
            
            # 生成唯一的文档ID
            doc_id = hashlib.md5(f"{owner_id}{filename}{time.time()}".encode()).hexdigest()
            
            # 根据所有者类型构建存储路径
            if owner_type == 'session':
                # 会话轨道: sessions/{session_id}/{doc_id}/original.ext
                storage_path = f"sessions/{owner_id}/{doc_id}/original{os.path.splitext(filename)[1]}"
            elif owner_type == 'kb':
                # 知识库轨道: kbs/{kb_id}/{doc_id}/original.ext
                storage_path = f"kbs/{owner_id}/{doc_id}/original{os.path.splitext(filename)[1]}"
            else:
                raise ValueError(f"不支持的owner_type: {owner_type}")
            
            # 流式上传到MinIO
            self.client.put_object(
                bucket_name=self.doc_bucket,
                object_name=storage_path,
                data=file_stream,
                length=file_size,
                content_type=content_type
            )
            
            # 生成访问URL
            url = self.get_file_url(self.doc_bucket, storage_path)
            
            total_time = time.time() - start_time
            logger.info(f"文档流式上传成功: {storage_path}, 耗时: {total_time:.2f}s, 大小: {file_size / 1024:.1f}KB")
            
            return {
                'doc_id': doc_id,
                'storage_path': storage_path,
                'url': url,
                'file_size': file_size,
                'content_type': content_type,
                'owner_type': owner_type
            }
            
        except S3Error as e:
            logger.error(f"流式上传文档到MinIO失败: {e}")
            raise
        except Exception as e:
            logger.error(f"流式上传文档时发生错误: {e}")
            raise
    
    async def download_file_as_bytes(self, storage_path: str, bucket: Optional[str] = None) -> bytes:
        """
        从MinIO下载文件为字节流（供解析服务使用）
        
        Args:
            storage_path: MinIO中的存储路径
            bucket: 存储桶名称，默认为doc_bucket
        
        Returns:
            文件的二进制内容
        """
        try:
            if bucket is None:
                bucket = self.doc_bucket
            
            logger.info(f"开始从MinIO下载文件: {bucket}/{storage_path}")
            
            response = self.client.get_object(bucket, storage_path)
            file_data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"文件下载成功: {storage_path}, 大小: {len(file_data)} bytes")
            return file_data
            
        except S3Error as e:
            logger.error(f"从MinIO下载文件失败: {bucket}/{storage_path}, 错误: {e}")
            raise
        except Exception as e:
            logger.error(f"下载文件时发生错误: {e}")
            raise
    
    async def upload_file_bytes(
        self,
        bucket_name: str,
        object_name: str,
        file_bytes: bytes,
        content_type: str = 'application/octet-stream'
    ) -> str:
        """
        上传字节流到MinIO（供知识库图片/处理后文件上传使用）
        
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称（完整路径）
            file_bytes: 文件字节流
            content_type: MIME类型
        
        Returns:
            文件的访问URL
        """
        try:
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=BytesIO(file_bytes),
                length=len(file_bytes),
                content_type=content_type
            )
            
            url = self.get_file_url(bucket_name, object_name)
            logger.info(f"字节流上传成功: {bucket_name}/{object_name}, 大小: {len(file_bytes)} bytes")
            
            return url
            
        except S3Error as e:
            logger.error(f"上传字节流到MinIO失败: {e}")
            raise
        except Exception as e:
            logger.error(f"上传字节流时发生错误: {e}")
            raise
    
    def delete_document_files(self, owner_id: str, owner_type: str, doc_id: Optional[str] = None):
        """
        删除文档相关的所有文件（包括原始文件、处理后文件、图片等）
        
        Args:
            owner_id: 所有者ID（session_id 或 kb_id）
            owner_type: 所有者类型（'session' 或 'kb'）
            doc_id: 文档ID，如果为None则删除该所有者的所有文档
        """
        try:
            if owner_type == 'session':
                prefix = f"sessions/{owner_id}/"
                if doc_id:
                    prefix += f"{doc_id}/"
            elif owner_type == 'kb':
                prefix = f"kbs/{owner_id}/"
                if doc_id:
                    prefix += f"{doc_id}/"
            else:
                logger.error(f"不支持的owner_type: {owner_type}")
                return
            
            objects = self.client.list_objects(self.doc_bucket, prefix=prefix, recursive=True)
            deleted_count = 0
            
            for obj in objects:
                self.client.remove_object(self.doc_bucket, obj.object_name)
                deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"删除文档文件: {self.doc_bucket}/{prefix}, 共 {deleted_count} 个文件")
            
        except S3Error as e:
            logger.error(f"删除文档文件失败 {prefix}: {e}")
        except Exception as e:
            logger.error(f"删除文档文件时发生错误: {e}")


# 创建单例实例
try:
    minio_storage = MinIOStorage()
    logger.info("MinIO存储服务初始化成功")
except Exception as e:
    logger.error(f"MinIO存储服务初始化失败: {e}")
    minio_storage = None
