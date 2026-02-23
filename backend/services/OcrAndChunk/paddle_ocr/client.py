"""
PaddleX 版式解析 API 客户端

提供与 PaddleX API 的通信功能，支持 PDF 和图片的版式解析。
"""

import base64
import logging
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


class PaddleOCRClient:
    """
    PaddleX 版式解析 API 客户端
    
    封装与 PaddleX API 的通信，支持：
    - PDF 文件解析
    - 图片文件解析
    - 字节流解析
    
    示例:
        client = PaddleOCRClient(api_url="...", token="...")
        response = client.parse_pdf("/path/to/file.pdf")
    """
    
    def __init__(
        self,
        api_url: str,
        token: str,
        timeout: int = 300
    ):
        """
        初始化客户端
        
        Args:
            api_url: PaddleX API 地址
            token: API 认证 Token
            timeout: 请求超时时间（秒），默认 300
        """
        self.api_url = api_url
        self.token = token
        self.timeout = timeout
    
    def parse_pdf(
        self,
        pdf_path: str,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
        use_chart_recognition: bool = False,
    ) -> Dict[str, Any]:
        """
        解析 PDF 文件
        
        Args:
            pdf_path: PDF 文件路径
            use_orientation_classify: 是否使用文档方向分类
            use_unwarping: 是否使用文档矫正
            use_chart_recognition: 是否识别图表
        
        Returns:
            API 返回的完整响应
            
        Raises:
            FileNotFoundError: 文件不存在
            RuntimeError: API 请求失败
        """
        with open(pdf_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("ascii")
        
        return self._request(
            file_data,
            file_type=0,  # 0 表示 PDF
            use_orientation_classify=use_orientation_classify,
            use_unwarping=use_unwarping,
            use_chart_recognition=use_chart_recognition
        )
    
    def parse_pdf_bytes(
        self,
        pdf_bytes: bytes,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
        use_chart_recognition: bool = False,
    ) -> Dict[str, Any]:
        """
        解析 PDF 字节流
        
        Args:
            pdf_bytes: PDF 文件字节流
            use_orientation_classify: 是否使用文档方向分类
            use_unwarping: 是否使用文档矫正
            use_chart_recognition: 是否识别图表
        
        Returns:
            API 返回的完整响应
            
        Raises:
            RuntimeError: API 请求失败
        """
        file_data = base64.b64encode(pdf_bytes).decode("ascii")
        
        return self._request(
            file_data,
            file_type=0,
            use_orientation_classify=use_orientation_classify,
            use_unwarping=use_unwarping,
            use_chart_recognition=use_chart_recognition
        )
    
    def parse_image(
        self,
        image_path: str,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
        use_chart_recognition: bool = False,
    ) -> Dict[str, Any]:
        """
        解析图片文件
        
        Args:
            image_path: 图片文件路径
            use_orientation_classify: 是否使用文档方向分类
            use_unwarping: 是否使用文档矫正
            use_chart_recognition: 是否识别图表
        
        Returns:
            API 返回的完整响应
            
        Raises:
            FileNotFoundError: 文件不存在
            RuntimeError: API 请求失败
        """
        with open(image_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("ascii")
        
        return self._request(
            file_data,
            file_type=1,  # 1 表示图片
            use_orientation_classify=use_orientation_classify,
            use_unwarping=use_unwarping,
            use_chart_recognition=use_chart_recognition
        )
    
    def parse_image_bytes(
        self,
        image_bytes: bytes,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
        use_chart_recognition: bool = False,
    ) -> Dict[str, Any]:
        """
        解析图片字节流
        
        Args:
            image_bytes: 图片文件字节流
            use_orientation_classify: 是否使用文档方向分类
            use_unwarping: 是否使用文档矫正
            use_chart_recognition: 是否识别图表
        
        Returns:
            API 返回的完整响应
            
        Raises:
            RuntimeError: API 请求失败
        """
        file_data = base64.b64encode(image_bytes).decode("ascii")
        
        return self._request(
            file_data,
            file_type=1,
            use_orientation_classify=use_orientation_classify,
            use_unwarping=use_unwarping,
            use_chart_recognition=use_chart_recognition
        )
    
    def _request(
        self,
        file_data: str,
        file_type: int,
        use_orientation_classify: bool,
        use_unwarping: bool,
        use_chart_recognition: bool,
    ) -> Dict[str, Any]:
        """
        发送 API 请求
        
        Args:
            file_data: Base64 编码的文件数据
            file_type: 文件类型（0=PDF, 1=图片）
            use_orientation_classify: 是否使用文档方向分类
            use_unwarping: 是否使用文档矫正
            use_chart_recognition: 是否识别图表
        
        Returns:
            API 响应 JSON
            
        Raises:
            RuntimeError: API 请求失败
        """
        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "file": file_data,
            "fileType": file_type,
            "useDocOrientationClassify": use_orientation_classify,
            "useDocUnwarping": use_unwarping,
            "useChartRecognition": use_chart_recognition,
        }
        
        response = requests.post(
            self.api_url,
            json=payload,
            headers=headers,
            timeout=self.timeout
        )
        
        if response.status_code != 200:
            error_msg = f"PaddleX API 请求失败: status={response.status_code}, url={self.api_url}, response={response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.debug("PaddleX API 请求成功")
        return response.json()
