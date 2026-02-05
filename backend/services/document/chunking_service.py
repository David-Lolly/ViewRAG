"""文档分块服务"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ChunkingService:
    """文档分块服务类"""
    
    def __init__(self):
        """初始化分块服务"""
        # 分块参数
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.separators = ["\n\n", "\n", ". ", "。", "!", "！", "?", "？", " ", ""]
        self.min_chunk_length = 20  # 过滤过短块，避免噪声
        
        # 标题级别配置（支持 # 到 ######）
        self.headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
            ("#####", "h5"),
            ("######", "h6"),
        ]
    
    def chunk_text(self, markdown_text: str) -> List[Dict[str, Any]]:
        """
        两阶段文本切分
        
        Stage 1: 使用 MarkdownHeaderTextSplitter 按标题切分，保留文档结构
        Stage 2: 使用 RecursiveCharacterTextSplitter 对过长块二次切分
        
        Args:
            markdown_text: Markdown 文本
            
        Returns:
            切分后的 chunks 列表，每个元素包含:
            {
                'content': str,           # 文本内容
                'heading_path': List[str] # 标题路径
            }
        """
        if not markdown_text or not markdown_text.strip():
            logger.warning("输入文本为空，返回空列表")
            return []
        
        try:
            from langchain_text_splitters import (
                MarkdownHeaderTextSplitter,
                RecursiveCharacterTextSplitter
            )
            
            text_length = len(markdown_text)
            logger.info(f"开始两阶段切分 | 文本长度={text_length}")
            
            # Stage 1: 按 Markdown 标题切分
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=self.headers_to_split_on,
                strip_headers=False
            )
            header_chunks = markdown_splitter.split_text(markdown_text)
            
            logger.info(f"Stage 1 完成 | 标题切分块数={len(header_chunks)}")
            
            # Stage 2: 对过长块进行二次切分
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=self.separators,
                length_function=len
            )
            
            final_chunks = []
            
            for doc in header_chunks:
                content = doc.page_content.strip()
                
                # 过滤过短块
                if len(content) < self.min_chunk_length:
                    continue
                
                # 构建 heading_path
                heading_path = self._build_heading_path(doc.metadata)
                
                # 如果块过长，进行二次切分
                if len(content) > self.chunk_size:
                    sub_docs = text_splitter.split_documents([doc])
                    for sub_doc in sub_docs:
                        sub_content = sub_doc.page_content.strip()
                        if len(sub_content) >= self.min_chunk_length:
                            final_chunks.append({
                                'content': sub_content,
                                'heading_path': heading_path
                            })
                else:
                    final_chunks.append({
                        'content': content,
                        'heading_path': heading_path
                    })
            
            # 统计日志
            if final_chunks:
                lengths = [len(c['content']) for c in final_chunks]
                avg_len = sum(lengths) // len(lengths)
                logger.info(f"两阶段切分完成 | 最终块数={len(final_chunks)} | 平均长度={avg_len}")
            else:
                logger.warning("切分结果为空")
            
            return final_chunks
            
        except ImportError:
            logger.error("langchain_text_splitters 未安装，使用降级方案")
            return self._simple_chunk(markdown_text)
        except Exception as e:
            logger.error(f"两阶段切分失败: {e}")
            return self._simple_chunk(markdown_text)
    
    def _build_heading_path(self, metadata: Dict[str, str]) -> List[str]:
        """
        从 metadata 构建标题路径
        
        Args:
            metadata: langchain 切分后的 metadata，如 {'h1': '第一章', 'h2': '1.1 背景'}
            
        Returns:
            标题路径列表，如 ['第一章', '1.1 背景']
        """
        heading_path = []
        for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if level in metadata and metadata[level]:
                heading_path.append(metadata[level])
        return heading_path
    
    def _simple_chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        简单的降级分块方案
        
        Args:
            text: 文本
            
        Returns:
            chunks 列表
        """
        chunks = []
        current_chunk = ""
        
        for line in text.split('\n'):
            if len(current_chunk) + len(line) > self.chunk_size:
                if current_chunk and len(current_chunk.strip()) >= self.min_chunk_length:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'heading_path': []
                    })
                current_chunk = line
            else:
                current_chunk += '\n' + line
        
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_length:
            chunks.append({
                'content': current_chunk.strip(),
                'heading_path': []
            })
        
        logger.warning(f"使用简单分块，块数: {len(chunks)}")
        return chunks





