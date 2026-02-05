import logging
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
                success_msg = "多模态模型连接成功" if model_type == "multi-model" else "文本模型连接成功"
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
        """测试Rerank模型连接（阿里云格式）"""
        if not base_url or not api_key or not model_name:
            return {"success": False, "message": "Rerank模型配置不完整"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    base_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "input": {
                            "query": "什么是文本排序模型",
                            "documents": [
                                "文本排序模型广泛用于搜索引擎和推荐系统中",
                                "量子计算是计算科学的一个前沿领域"
                            ]
                        },
                        "parameters": {
                            "return_documents": True,
                            "top_n": 2
                        }
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                if "output" in data or "results" in data:
                    return {"success": True, "message": "Rerank模型连接成功"}
                else:
                    return {"success": False, "message": f"API响应异常: {data}"}
        except Exception as e:
            logger.error(f"Rerank连接测试失败: {e}")
            return {"success": False, "message": f"连接失败: {str(e)}"}

    @staticmethod
    async def test_google_connection(api_key: str, cse_id: str) -> Dict[str, Any]:
        """测试Google Search连接"""
        if not api_key or not cse_id:
            return {"success": False, "message": "API Key和CSE ID不能为空"}
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "q": "daily news",
                "key": api_key,
                "cx": cse_id,
                "num": 5
            }
            # 设置代理
            os.environ['HTTP_PROXY'] = 'http://localhost:7890'
            os.environ['HTTPS_PROXY'] = 'http://localhost:7890'
            os.environ['http_proxy'] = 'http://localhost:7890'
            os.environ['https_proxy'] = 'http://localhost:7890'
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                logger.info(f"Google Search连接成功。")
                return {"success": True, "message": "Google Search连接成功"}
            else:
                return {"success": False, "message": "Google Search连接失败"}
                
        except Exception as e:
            logger.error(f"Google Search连接测试失败: {e}")
            return {"success": False, "message": f"连接失败: {str(e)}"}
