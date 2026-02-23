"""
PaddleOCR 解析器实现

基于 PaddleX API 的 PDF 版式解析器，实现 BaseOCRParser 接口。
"""

import asyncio
import logging
import os
import tempfile
from typing import Dict, List, Optional, Tuple

from ..base import BaseOCRParser
from ..types import SimpleBlock, DEFAULT_PDF_SIZE
from .client import PaddleOCRClient
from .converter import parse_response
from .types import API_URL, API_TOKEN, DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)


def _read_pdf_page_sizes(file_path: str) -> Optional[Dict[int, Tuple[float, float]]]:
    """
    使用 PyMuPDF 读取 PDF 每页的真实尺寸（单位：PDF 点）

    Args:
        file_path: PDF 文件路径

    Returns:
        {page_idx: (width, height)} 字典，读取失败返回 None
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        sizes = {i: (doc[i].rect.width, doc[i].rect.height) for i in range(len(doc))}
        doc.close()
        logger.info(f"读取 PDF 页面尺寸：共 {len(sizes)} 页，第 0 页={sizes.get(0)}")
        return sizes
    except ImportError:
        logger.warning("PyMuPDF 未安装，无法读取真实页面尺寸，将使用默认值")
        return None
    except Exception as e:
        logger.warning(f"读取 PDF 页面尺寸失败: {e}，将使用默认值")
        return None


def _read_pdf_page_sizes_from_bytes(
    file_bytes: bytes,
) -> Optional[Dict[int, Tuple[float, float]]]:
    """
    从 PDF 字节流读取每页真实尺寸（单位：PDF 点）

    Returns:
        {page_idx: (width, height)} 字典，读取失败返回 None
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        sizes = {i: (doc[i].rect.width, doc[i].rect.height) for i in range(len(doc))}
        doc.close()
        logger.info(f"读取 PDF 页面尺寸（字节流）：共 {len(sizes)} 页，第 0 页={sizes.get(0)}")
        return sizes
    except ImportError:
        logger.warning("PyMuPDF 未安装，无法读取真实页面尺寸，将使用默认值")
        return None
    except Exception as e:
        logger.warning(f"读取 PDF 页面尺寸（字节流）失败: {e}，将使用默认值")
        return None


class PaddleOCRParser(BaseOCRParser):
    """
    PaddleX API 解析器
    
    使用 PaddleX 版式解析 API 解析 PDF 文档，返回 SimpleBlock 格式结果。
    
    特性：
    - 支持 PDF 文件路径解析
    - 支持 PDF 字节流解析
    - 自动坐标转换为 PDF 点坐标
    - 优雅的错误处理，失败时返回 None
    
    示例:
        parser = PaddleOCRParser(api_url="...", api_token="...")
        blocks = await parser.parse("/path/to/file.pdf")
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        pdf_size: Tuple[float, float] = DEFAULT_PDF_SIZE,
    ):
        """
        初始化解析器
        
        Args:
            api_url: PaddleX API 地址，默认从环境变量或配置获取
            api_token: API 认证 Token，默认从环境变量或配置获取
            timeout: 请求超时时间（秒），默认 300
            pdf_size: PDF 页面尺寸，默认 Letter (612x792)
        """
        self._api_url = api_url or API_URL
        self._api_token = api_token or API_TOKEN
        self._timeout = timeout
        self._pdf_size = pdf_size
        
        self._client = PaddleOCRClient(
            api_url=self._api_url,
            token=self._api_token,
            timeout=self._timeout
        )
    
    @property
    def parser_name(self) -> str:
        """解析器名称"""
        return "paddle_ocr"
    
    async def parse(
        self,
        file_path: str,
        **kwargs
    ) -> Optional[List[SimpleBlock]]:
        """
        解析 PDF 文件
        
        Args:
            file_path: PDF 文件路径
            **kwargs: 额外参数
                - use_orientation_classify: 是否使用文档方向分类
                - use_unwarping: 是否使用文档矫正
                - use_chart_recognition: 是否识别图表
                - recognize_table: 是否识别表格为 HTML（默认 True）
                - pdf_size: PDF 页面尺寸
        
        Returns:
            SimpleBlock 列表或 None（解析失败时）
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 提取参数
            use_orientation_classify = kwargs.get("use_orientation_classify", False)
            use_unwarping = kwargs.get("use_unwarping", False)
            use_chart_recognition = kwargs.get("use_chart_recognition", False)
            recognize_table = kwargs.get("recognize_table", True)
            pdf_size = kwargs.get("pdf_size", self._pdf_size)
            
            logger.info(f"开始解析 PDF: {file_path}")
            
            # 读取每页真实 PDF 尺寸（用于精确坐标转换）
            page_sizes = _read_pdf_page_sizes(file_path)
            
            # 调用 API（同步 HTTP 请求，放到线程池避免阻塞事件循环）
            response = await asyncio.to_thread(
                self._client.parse_pdf,
                file_path,
                use_orientation_classify=use_orientation_classify,
                use_unwarping=use_unwarping,
                use_chart_recognition=use_chart_recognition,
            )
            
            # 解析响应
            result = parse_response(
                response,
                recognize_table=recognize_table,
                pdf_size=pdf_size,
                page_sizes=page_sizes,
            )
            
            if result["success"]:
                blocks = result["data"]
                logger.info(f"解析成功，共 {len(blocks)} 个块")
                return blocks
            else:
                logger.error(f"解析失败: {result['error']}")
                return None
                
        except FileNotFoundError as e:
            logger.error(f"文件不存在: {e}")
            return None
        except RuntimeError as e:
            logger.error(f"API 请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"PaddleOCR 解析异常: {e}")
            return None
    
    async def parse_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        **kwargs
    ) -> Optional[List[SimpleBlock]]:
        """
        解析 PDF 字节流
        
        Args:
            file_bytes: PDF 文件字节流
            file_name: 文件名（用于日志记录）
            **kwargs: 额外参数（同 parse 方法）
        
        Returns:
            SimpleBlock 列表或 None（解析失败时）
        """
        try:
            # 提取参数
            use_orientation_classify = kwargs.get("use_orientation_classify", False)
            use_unwarping = kwargs.get("use_unwarping", False)
            use_chart_recognition = kwargs.get("use_chart_recognition", False)
            recognize_table = kwargs.get("recognize_table", True)
            pdf_size = kwargs.get("pdf_size", self._pdf_size)
            
            logger.info(f"开始解析 PDF 字节流: {file_name}")
            
            # 读取每页真实 PDF 尺寸（用于精确坐标转换）
            page_sizes = _read_pdf_page_sizes_from_bytes(file_bytes)
            
            # 调用 API（同步 HTTP 请求，放到线程池避免阻塞事件循环）
            response = await asyncio.to_thread(
                self._client.parse_pdf_bytes,
                file_bytes,
                use_orientation_classify=use_orientation_classify,
                use_unwarping=use_unwarping,
                use_chart_recognition=use_chart_recognition,
            )
            
            # 解析响应
            result = parse_response(
                response,
                recognize_table=recognize_table,
                pdf_size=pdf_size,
                page_sizes=page_sizes,
            )
            
            if result["success"]:
                blocks = result["data"]
                logger.info(f"解析成功，共 {len(blocks)} 个块")
                return blocks
            else:
                logger.error(f"解析失败: {result['error']}")
                return None
                
        except RuntimeError as e:
            logger.error(f"API 请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"PaddleOCR 解析异常: {e}")
            return None
