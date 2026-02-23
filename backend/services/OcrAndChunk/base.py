"""
OCR 解析器抽象基类

定义所有 OCR 解析器必须实现的接口。
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .types import SimpleBlock


class BaseOCRParser(ABC):
    """
    OCR 解析器抽象基类
    
    所有 OCR 解析器实现必须继承此类并实现以下方法：
    - parse(): 解析文件路径
    - parse_bytes(): 解析文件字节流
    - parser_name: 解析器名称属性
    """
    
    @abstractmethod
    async def parse(
        self,
        file_path: str,
        **kwargs
    ) -> Optional[List[SimpleBlock]]:
        """
        解析文档，返回 SimpleBlock 列表
        
        Args:
            file_path: 文件路径（本地或 MinIO）
            **kwargs: 解析器特定参数
            
        Returns:
            SimpleBlock 列表或 None（解析失败时）
        """
        pass
    
    @abstractmethod
    async def parse_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        **kwargs
    ) -> Optional[List[SimpleBlock]]:
        """
        解析文件字节流
        
        Args:
            file_bytes: 文件字节流
            file_name: 文件名（用于确定文件类型）
            **kwargs: 解析器特定参数
            
        Returns:
            SimpleBlock 列表或 None（解析失败时）
        """
        pass
    
    @property
    @abstractmethod
    def parser_name(self) -> str:
        """
        解析器名称
        
        Returns:
            解析器的唯一标识名称（如 'paddle_ocr'）
        """
        pass
