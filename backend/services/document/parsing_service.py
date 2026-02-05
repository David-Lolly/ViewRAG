"""文档解析服务"""
# problem： 119行解析服务的压缩文档下载地址不应使用硬编码方式

import logging
import httpx
import zipfile
import io
import os
from typing import Optional
from pathlib import Path

from utils.text_cleaner import clean_markdown, is_text_empty

logger = logging.getLogger(__name__)


class ParsingService:
    """文档解析服务类"""
    
    def __init__(self):
        """初始化解析服务"""
        # 高质量解析微服务地址
        self.quality_parse_url = "http://127.0.0.1:8011/parse"
        self.timeout = 300  # 5分钟超时
    
    async def parse_document_fast(self, file_path: str, doc_type: str, minio_client) -> Optional[str]:
        """
        使用pymupdf4llm进行快速本地解析
        
        Args:
            file_path: MinIO文件路径
            doc_type: 文档类型
            minio_client: MinIO客户端实例
            
        Returns:
            Markdown文本或None
        """
        import tempfile
        import time
        
        try:
            # 动态导入pymupdf4llm
            import pymupdf4llm
            
            # 从MinIO下载文件到临时文件
            file_bytes = await minio_client.download_file_as_bytes(file_path)
            file_size = len(file_bytes)
            
            logger.info(f"开始快速解析 | 文件={file_path} | 大小={file_size}bytes")
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_path)[1]) as temp_file:
                temp_file.write(file_bytes)
                temp_file_path = temp_file.name
            
            try:
                # 使用pymupdf4llm解析
                start_time = time.time()
                md_text = pymupdf4llm.to_markdown(temp_file_path)
                duration = time.time() - start_time
                
                if md_text:
                    logger.info(f"快速解析成功 | 耗时={duration:.2f}s | Markdown长度={len(md_text)}")
                    logger.debug(f"Markdown预览 | 前500字={md_text[:500]}")
                    return md_text
                else:
                    logger.warning(f"快速解析返回空内容 | 文件={file_path}")
                    return None
            finally:
                # 删除临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
        except ImportError:
            logger.error(f"pymupdf4llm未安装，无法使用快速解析 | 文件={file_path}")
            return None
        except Exception as e:
            logger.error(f"快速解析失败 | 文件={file_path} | 错误={str(e)}")
            return None
    
    async def parse_document_quality_get_zip(
        self, 
        file_path: str, 
        doc_type: str,
        minio_client
    ) -> Optional[bytes]:
        """
        调用高质量解析微服务，返回ZIP内容（知识库轨道专用）
        
        Args:
            file_path: MinIO文件路径
            doc_type: 文档类型
            minio_client: MinIO客户端实例
            
        Returns:
            ZIP文件的二进制内容或None
        """
        import time
        
        try:
            # 从MinIO下载文件
            file_bytes = await minio_client.download_file_as_bytes(file_path)
            file_size = len(file_bytes)
            
            logger.info(f"开始高质量解析 | 文件={file_path} | 大小={file_size}bytes")
            
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 准备文件上传
                files = {'file': (os.path.basename(file_path), io.BytesIO(file_bytes), 'application/pdf')}
                
                # 调用解析服务
                logger.debug(f"调用解析微服务 | URL={self.quality_parse_url} | 超时={self.timeout}s")
                response = await client.post(
                    self.quality_parse_url,
                    files=files
                )
                response.raise_for_status()
                
                result = response.json()
                download_url = result.get('download_url')
                
                if not download_url:
                    logger.error(f"解析服务未返回下载URL | 文件={file_path}")
                    return None
                
                # 下载ZIP文件
                zip_url = f"http://127.0.0.1:8011{download_url}"
                logger.debug(f"下载ZIP | URL={zip_url}")
                zip_response = await client.get(zip_url)
                zip_response.raise_for_status()
                
                duration = time.time() - start_time
                zip_size = len(zip_response.content)
                
                logger.info(f"高质量解析成功 | 耗时={duration:.2f}s | ZIP大小={zip_size}bytes")
                return zip_response.content
                    
        except httpx.TimeoutException:
            logger.error(f"高质量解析超时 | 文件={file_path} | 超时限制={self.timeout}s")
            return None
        except Exception as e:
            logger.error(f"高质量解析失败 | 文件={file_path} | 错误={str(e)}")
            return None
    
    async def parse_document_quality(
        self, 
        file_path: str, 
        doc_type: str,
        minio_client
    ) -> Optional[str]:
        """
        调用高质量解析微服务（简化版，仅返回Markdown）
        用于会话轨道兜底
        
        Args:
            file_path: MinIO文件路径
            doc_type: 文档类型
            minio_client: MinIO客户端实例
            
        Returns:
            Markdown文本或None
        """
        try:
            # 获取ZIP内容
            zip_content = await self.parse_document_quality_get_zip(file_path, doc_type, minio_client)
            if not zip_content:
                return None
            
            # 只提取Markdown，不处理图片
            markdown_text = self._extract_markdown_from_zip(zip_content)
            
            if markdown_text:
                logger.info(f"Markdown提取成功，长度: {len(markdown_text)}")
            return markdown_text
                    
        except Exception as e:
            logger.error(f"高质量解析失败: {e}")
            return None
    
    def _extract_markdown_from_zip(self, zip_content: bytes) -> Optional[str]:
        """
        从ZIP内容中提取Markdown文本
        
        Args:
            zip_content: ZIP文件的二进制内容
            
        Returns:
            Markdown文本或None
        """
        try:
            zip_file = zipfile.ZipFile(io.BytesIO(zip_content))
            
            # 查找.md文件
            for file_path in zip_file.namelist():
                if file_path.endswith('.md'):
                    with zip_file.open(file_path) as md_file:
                        markdown_text = md_file.read().decode('utf-8')
                        return markdown_text
            
            logger.warning("ZIP文件中未找到Markdown文件")
            return None
            
        except Exception as e:
            logger.error(f"提取Markdown失败: {e}")
            return None
    
    async def parse_document(
        self, 
        file_path: str, 
        doc_type: str,
        minio_client,
        track: str = 'session',
        kb_id: Optional[str] = None,
        doc_id: Optional[str] = None
    ) -> Optional[str]:
        """
        统一文档解析入口（带兜底逻辑）
        
        Args:
            file_path: MinIO文件路径
            doc_type: 文档类型
            minio_client: MinIO客户端实例
            track: 轨道类型 ('session' 或 'kb')
            kb_id: 知识库ID（仅kb轨道需要）
            doc_id: 文档ID（仅kb轨道需要）
            
        Returns:
            Markdown文本或None
        """
        if track == 'kb':
            if not kb_id or not doc_id:
                logger.error("知识库轨道解析缺少kb_id或doc_id参数")
                return None
            return await self._parse_kb_document(
                file_path,
                doc_type,
                minio_client,
                kb_id=kb_id,
                doc_id=doc_id
            )
        
        # 会话轨道：快速解析 + 清洗 + 兜底
        logger.info(f"使用会话轨道解析策略 | 文件={file_path}")
        
        # 1. 快速解析
        md_text = await self.parse_document_fast(file_path, doc_type, minio_client)
        
        if md_text:
            # 2. 清洗文本
            raw_length = len(md_text)
            cleaned_text = clean_markdown(md_text)
            cleaned_length = len(cleaned_text)
            remove_rate = ((raw_length - cleaned_length) / raw_length * 100) if raw_length > 0 else 0
            
            logger.debug(f"清洗统计 | 原始长度={raw_length} | 清洗后长度={cleaned_length} | 删除率={remove_rate:.1f}%")
            
            # 3. 检查清洗后是否为空
            if not is_text_empty(cleaned_text):
                logger.info(f"快速解析+清洗成功 | 最终长度={cleaned_length}")
                return cleaned_text
            else:
                logger.warning(f"触发兜底机制 | 原因=清洗后内容为空 | 文件={file_path}")
        
        # 4. 兜底：使用高质量解析
        logger.info(f"使用高质量解析兜底 | 文件={file_path}")
        return await self.parse_document_quality(file_path, doc_type, minio_client)
    
    async def _parse_kb_document(
        self,
        file_path: str,
        doc_type: str,
        minio_client,
        kb_id: str,
        doc_id: str
    ) -> Optional[str]:
        """
        知识库轨道解析流程：高质量解析 + 图片处理
        """
        zip_content = await self.parse_document_quality_get_zip(
            file_path,
            doc_type,
            minio_client
        )
        
        if not zip_content:
            return None
        
        markdown_text = await self.process_zip_and_upload_images(
            zip_content,
            kb_id,
            doc_id,
            minio_client
        )
        return markdown_text
    
    async def process_zip_and_upload_images(
        self,
        zip_content: bytes,
        kb_id: str,
        doc_id: str,
        minio_client
    ) -> Optional[str]:
        """
        处理解析服务返回的ZIP包（知识库轨道专用）
        
        功能：
        1. 提取Markdown文件
        2. 提取所有图片
        3. 将图片上传到MinIO
        4. 重写Markdown中的图片路径为MinIO URL
        
        Args:
            zip_content: ZIP文件的二进制内容
            kb_id: 知识库ID
            doc_id: 文档ID
            minio_client: MinIO客户端实例
            
        Returns:
            处理后的Markdown文本
        """
        try:
            zip_file = zipfile.ZipFile(io.BytesIO(zip_content))
            
            markdown_text = None
            path_mappings = {}
            
            # 1. 找到Markdown文件
            markdown_file_path = None
            image_paths = []
            
            for file_path in zip_file.namelist():
                if file_path.endswith('.md'):
                    markdown_file_path = file_path
                elif file_path.startswith('images/') and not file_path.endswith('/'):
                    image_paths.append(file_path)
            
            if not markdown_file_path:
                logger.error("ZIP中未找到Markdown文件")
                return None
            
            # 2. 上传图片到MinIO
            logger.info(f"开始上传图片 | 数量={len(image_paths)} | kb_id={kb_id} | doc_id={doc_id}")
            
            for idx, image_path in enumerate(image_paths):
                with zip_file.open(image_path) as image_file:
                    image_bytes = image_file.read()
                
                image_filename = os.path.basename(image_path)
                image_size = len(image_bytes)
                minio_object_name = f"kbs/{kb_id}/{doc_id}/images/{image_filename}"
                
                # 使用MinIOStorage的upload_file_bytes方法上传
                minio_url = await minio_client.upload_file_bytes(
                    bucket_name=minio_client.doc_bucket,
                    object_name=minio_object_name,
                    file_bytes=image_bytes,
                    content_type=self._get_image_content_type(image_filename)
                )
                
                path_mappings[image_path] = minio_url
                logger.info(f"图片已上传 | 索引={idx+1}/{len(image_paths)} | 文件={image_filename} | 大小={image_size}bytes")
                logger.debug(f"图片URL | {minio_url}")
            
            # 3. 提取Markdown并替换路径
            with zip_file.open(markdown_file_path) as md_file:
                markdown_text = md_file.read().decode('utf-8')
            
            # 4. 替换所有图片路径
            for original_path, new_url in path_mappings.items():
                markdown_text = markdown_text.replace(original_path, new_url)
            
            # 5. 保存处理后的Markdown到MinIO（便于调试和恢复）
            processed_md_object_name = f"kbs/{kb_id}/{doc_id}/processed/final.md"
            await minio_client.upload_file_bytes(
                bucket_name=minio_client.doc_bucket,
                object_name=processed_md_object_name,
                file_bytes=markdown_text.encode('utf-8'),
                content_type='text/markdown; charset=utf-8'
            )
            logger.info(f"处理后的Markdown已保存: {processed_md_object_name}")
            
            logger.info(f"ZIP处理完成 | 图片数={len(path_mappings)} | Markdown长度={len(markdown_text)}")
            logger.debug(f"处理后的Markdown已保存 | 路径={processed_md_object_name}")
            return markdown_text
            
        except Exception as e:
            logger.error(f"处理ZIP失败: {e}")
            return None
    
    @staticmethod
    def _get_image_content_type(filename: str) -> str:
        """根据文件名获取Content-Type"""
        ext = filename.lower().split('.')[-1]
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'bmp': 'image/bmp'
        }
        return content_types.get(ext, 'application/octet-stream')

