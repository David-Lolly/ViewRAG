import logging
import base64
import os
import httpx
import requests
from openai import AsyncOpenAI
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TestConnectionService:
    """连接测试服务"""
    
    @staticmethod
    async def test_llm_connection(api_key: str, base_url: str, model_name: str, model_type: str = "text-model") -> Dict[str, Any]:
        """测试LLM连接
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model_name: 模型名称
            model_type: 模型类型 ("text-model" 或 "multi-model")
        """
        if not api_key or not base_url or not model_name:
            return {"success": False, "message": "LLM配置不完整"}
        
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        try:
            # 根据模型类型构建不同的测试消息
            if model_type == "multi-model":
                # 多模态模型：使用图片测试
                # 使用一个简单的base64编码的小图片（1x1像素的透明PNG）
                test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请简单描述这张图片"},
                        {"type": "image_url", "image_url": {"url": "https://img.alicdn.com/imgextra/i1/O1CN01gDEY8M1W114Hi3XcN_!!6000000002727-0-tps-1024-406.jpg"}}
                    ]
                }]
                logger.info(f"测试多模态模型: {model_name}")
            elif model_type == "reason-model":
                 # 推理模型测试
                messages = [{"role": "user", "content": "9.11和9.8哪个大"}]
                logger.info(f"测试推理模型: {model_name}")
            else:
                # 文本模型：使用纯文本测试
                messages = [{"role": "user", "content": "Hi"}]
                logger.info(f"测试文本模型: {model_name}")
            
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=10
            )
            
            # 检查响应
            if response and response.choices:
                msg_map = {
                    "multi-model": "多模态模型连接成功",
                     "reason-model": "推理模型连接成功",
                    "text-model": "文本模型连接成功"
                }
                success_msg = msg_map.get(model_type, "模型连接成功")
                return {"success": True, "message": success_msg}
            else:
                return {"success": False, "message": "模型响应异常"}
                
        except Exception as e:
            logger.error(f"LLM连接测试失败 ({model_type}): {e}")
            error_msg = str(e)
            
            # 如果是多模态模型测试失败，给出更详细的提示
            if model_type == "multi-model" and "image" in error_msg.lower():
                return {"success": False, "message": f"多模态测试失败: 该模型可能不支持图片输入。错误: {error_msg}"}
            
            return {"success": False, "message": f"连接失败: {error_msg}"}

    @staticmethod
    async def test_embedding_connection(api_key: str, base_url: str, model_name: str) -> Dict[str, Any]:
        """测试Embedding模型连接"""
        if not api_key or not base_url or not model_name:
            return {"success": False, "message": "Embedding模型配置不完整"}
        
        payload = {
            "model": model_name,
            "input": ["test"],
            "encoding_format": "float"
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(base_url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                if "data" in data:
                    return {"success": True, "message": "Embedding模型连接成功"}
                else:
                    return {"success": False, "message": f"API响应异常: {data}"}
        except Exception as e:
            logger.error(f"Embedding连接测试失败: {e}")
            return {"success": False, "message": f"连接失败: {str(e)}"}

    @staticmethod
    async def test_rerank_connection(api_key: str, base_url: str, model_name: str) -> Dict[str, Any]:
        """测试Rerank模型连接"""
        if not base_url or not api_key or not model_name:
            return {"success": False, "message": "Rerank模型配置不完整"}
        
        try:
            # 构造请求数据
            query = "什么是文本排序模型"
            documents = [
                "文本排序模型广泛用于搜索引擎和推荐系统中",
                "量子计算是计算科学的一个前沿领域"
            ]

            # 根据URL判断服务商格式
            # 阿里云 DashScope 格式
            if "dashscope.aliyuncs.com" in base_url:
                payload = {
                    "model": model_name,
                    "input": {
                        "query": query,
                        "documents": documents
                    },
                    "parameters": {
                        "return_documents": True,
                        "top_n": 2
                    }
                }
            # 硅基流动/默认 OpenAI 兼容格式
            else:
                payload = {
                    "model": model_name,
                    "query": query,
                    "documents": documents,
                    "return_documents": True,
                    "top_n": 2
                }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    base_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                # 检查响应 (兼容两种格式的响应判断)
                if "output" in data or "results" in data or "data" in data or ("usage" in data and "id" in data):
                    return {"success": True, "message": "Rerank模型连接成功"}
                else:
                    return {"success": False, "message": f"API响应异常: {data}"}
        except Exception as e:
            logger.error(f"Rerank连接测试失败: {e}")
            return {"success": False, "message": f"连接失败: {str(e)}"}



    # 新增 OCR 服务连接测试 (PaddleOCR)
    @staticmethod
    async def test_ocr_connection(api_url: str, api_token: str) -> Dict[str, Any]:
        """测试OCR连接 (PaddleOCR)"""
        if not api_url or not api_token:
            return {"success": False, "message": "OCR配置不完整"}
        
        # 使用本地测试文件
        # 路径: docs/PDF/attention is all you need.pdf
        # 注意：这里需要确定相对路径的基准，通常是 backend/ 目录或者项目根目录
        # 假设 backend 是工作目录，则路径为 ../docs/PDF/...
        # 或者我们使用更稳妥的绝对路径查找方式，或者使用一个极小的内存 PDF
        
        # 尝试查找测试文件
        # 当前文件: backend/services/test_connection.py
        # backend 目录: code_root/backend
        # PDF 位置: backend/PDF/attention is all you need.pdf
        
        current_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/services
        backend_dir = os.path.dirname(current_dir) # .../backend
        
        # 优先查找 backend/PDF 目录 (用户指定的新位置)
        test_file_path = os.path.join(backend_dir, "PDF", "attention is all you need.pdf")
        
        
        try:
            # 读取文件并进行 base64 编码
            with open(test_file_path, "rb") as file:
                file_bytes = file.read()
                # 仅读取前 50KB 用于测试，避免大文件上传超时 (PaddleOCR API 可能不接受损坏的 PDF，所以最好还是传整文件)
                # 考虑到这是测试，我们传整个文件，但设置较长的超时时间
                file_data = base64.b64encode(file_bytes).decode("ascii")

            headers = {
                "Authorization": f"token {api_token}",
                "Content-Type": "application/json"
            }

            # 构造 PaddleOCR 官方要求的 payload
            payload = {
                "file": file_data,
                "fileType": 0,  # 0 for PDF
                "useDocOrientationClassify": False,
                "useDocUnwarping": False,
                "useChartRecognition": False,
            }
            
            logger.info(f"开始测试 PaddleOCR 连接: {api_url}")

            async with httpx.AsyncClient(timeout=120.0) as client: # 设置120秒超时
                response = await client.post(api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    # 检查 result 字段是否存在
                    if "result" in data:
                        return {"success": True, "message": "OCR服务连接成功 (PaddleOCR)"}
                    else:
                        return {"success": False, "message": f"API返回了200但格式未能解析: {str(data)[:100]}..."}
                else:
                    return {"success": False, "message": f"OCR服务返回错误: {response.status_code} - {response.text[:200]}"}

        except httpx.TimeoutException:
             return {"success": False, "message": "OCR服务连接超时 (超过120秒)，请检查网络或文件大小"}
        except Exception as e:
            logger.error(f"OCR连接测试失败: {e}")
            return {"success": False, "message": f"连接失败: {str(e)}"}
