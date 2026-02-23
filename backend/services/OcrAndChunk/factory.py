"""
OCR 解析器工厂

提供解析器的注册、创建和获取功能，支持通过配置切换不同的解析器实现。
"""

import logging
from typing import Dict, Type, Optional, List

from .base import BaseOCRParser

logger = logging.getLogger(__name__)


class OCRParserFactory:
    """
    OCR 解析器工厂
    
    使用工厂模式管理解析器的注册和创建，支持：
    - 注册新的解析器实现
    - 根据名称创建解析器实例
    - 获取默认解析器
    - 列出所有可用解析器
    
    示例:
        # 注册解析器
        OCRParserFactory.register("paddle_ocr", PaddleOCRParser)
        
        # 创建解析器
        parser = OCRParserFactory.create("paddle_ocr", api_url="...", api_token="...")
        
        # 获取默认解析器
        parser = OCRParserFactory.get_default()
    """
    
    _parsers: Dict[str, Type[BaseOCRParser]] = {}
    _default_parser: str = "paddle_ocr"
    
    @classmethod
    def register(cls, name: str, parser_class: Type[BaseOCRParser]) -> None:
        """
        注册解析器
        
        Args:
            name: 解析器名称（如 'paddle_ocr'、'monkey_ocr'）
            parser_class: 解析器类（必须继承 BaseOCRParser）
            
        Raises:
            TypeError: 如果 parser_class 不是 BaseOCRParser 的子类
        """
        if not isinstance(parser_class, type) or not issubclass(parser_class, BaseOCRParser):
            raise TypeError(
                f"parser_class 必须是 BaseOCRParser 的子类，"
                f"实际类型: {type(parser_class)}"
            )
        
        cls._parsers[name] = parser_class
        logger.debug(f"注册解析器: {name} -> {parser_class.__name__}")
    
    @classmethod
    def create(cls, name: str, **kwargs) -> BaseOCRParser:
        """
        创建解析器实例
        
        Args:
            name: 解析器名称（如 'paddle_ocr'）
            **kwargs: 解析器初始化参数
            
        Returns:
            解析器实例
            
        Raises:
            ValueError: 未知的解析器名称
        """
        if name not in cls._parsers:
            available = list(cls._parsers.keys())
            raise ValueError(
                f"未知的解析器: {name}，可用解析器: {available}"
            )
        
        parser_class = cls._parsers[name]
        logger.debug(f"创建解析器: {name}")
        return parser_class(**kwargs)
    
    @classmethod
    def get_default(cls, **kwargs) -> BaseOCRParser:
        """
        获取默认解析器（PaddleOCR）
        
        Args:
            **kwargs: 解析器初始化参数
            
        Returns:
            默认解析器实例
            
        Raises:
            ValueError: 默认解析器未注册
        """
        return cls.create(cls._default_parser, **kwargs)
    
    @classmethod
    def set_default(cls, name: str) -> None:
        """
        设置默认解析器
        
        Args:
            name: 解析器名称
            
        Raises:
            ValueError: 解析器未注册
        """
        if name not in cls._parsers:
            available = list(cls._parsers.keys())
            raise ValueError(
                f"无法设置默认解析器: {name} 未注册，可用解析器: {available}"
            )
        cls._default_parser = name
        logger.debug(f"设置默认解析器: {name}")
    
    @classmethod
    def list_parsers(cls) -> List[str]:
        """
        列出所有已注册的解析器名称
        
        Returns:
            解析器名称列表
        """
        return list(cls._parsers.keys())
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        检查解析器是否已注册
        
        Args:
            name: 解析器名称
            
        Returns:
            是否已注册
        """
        return name in cls._parsers
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        注销解析器
        
        Args:
            name: 解析器名称
            
        Returns:
            是否成功注销（如果解析器不存在返回 False）
        """
        if name in cls._parsers:
            del cls._parsers[name]
            logger.debug(f"注销解析器: {name}")
            return True
        return False
    
    @classmethod
    def clear(cls) -> None:
        """
        清空所有已注册的解析器（主要用于测试）
        """
        cls._parsers.clear()
        cls._default_parser = "paddle_ocr"
        logger.debug("清空所有解析器注册")
    
    @classmethod
    def create_from_config(cls) -> BaseOCRParser:
        """
        根据配置文件创建解析器实例
        
        从 ConfigManager 读取 OCR 配置，自动选择解析器并传入配置参数。
        
        Returns:
            配置的解析器实例
            
        Raises:
            ValueError: 配置的解析器未注册
        """
        from crud.config_manager import config
        
        # 确保配置已加载
        config.initialize_config()
        
        # 获取配置的解析器名称
        parser_name = config.get_ocr_parser()
        
        # 获取解析器配置
        parser_config = config.get_ocr_config(parser_name)
        
        logger.info(f"从配置创建解析器: {parser_name}")
        return cls.create(parser_name, **parser_config)
