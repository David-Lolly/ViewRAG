from fastapi import APIRouter, HTTPException
from schemas.request import TestRequest
from services.test_connection import TestConnectionService
from crud.config_manager import config

router = APIRouter()


def _resolve(primary: str | None, secondary: str | None = None) -> str:
    """返回第一个非空字符串值。"""
    if primary:
        return primary
    if secondary:
        return secondary
    return ""


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)

@router.get("/api/status")
async def get_status():
    """获取系统配置状态"""
    is_active = config.is_active()  # 使用新的 is_active() 方法检查 IS_ACTIVE 字段
    return {"configured": is_active}

@router.get("/api/settings")
async def get_settings_api():
    """获取所有设置（返回完整的 config.yaml 结构）"""
    return config.get_all()

@router.get("/api/settings/chat-models")
async def get_chat_models():
    """获取所有可用的对话模型列表"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        chat_models = config.get_chat_models()
        if not chat_models:
            return {"success": False, "message": "未配置对话模型", "models": []}
        
        # 返回模型列表，标记默认模型和模型类型
        models_info = []
        for model in chat_models:
            models_info.append({
                "name": model.get("name"),
                "description": model.get("description", ""),
                "type": model.get("type", "text-model"),
                "is_default": model.get("is_default", False),
                "temperature": model.get("temperature", 0.5)
            })
        
        logger.info(f"返回 {len(models_info)} 个对话模型")
        return {
            "success": True,
            "models": models_info
        }
    except Exception as e:
        logger.error(f"获取对话模型列表失败: {e}")
        return {"success": False, "message": str(e), "models": []}

@router.post("/api/settings")
async def save_settings_api(payload: dict):
    """
    保存设置（接收完整的配置结构）
    前端应该在所有模型测试通过后，发送完整的配置对象，并请求激活系统
    """
    new_config = payload.get("config")
    if not isinstance(new_config, dict) or not new_config:
        raise HTTPException(status_code=400, detail="未提供有效的配置数据。")

    # 检查是否请求激活系统
    should_activate = _to_bool(payload.get("activate", False))
    
    try:
        # 保存配置
        updated = config.save_config(new_config)
        
        # 如果请求激活且配置完整，则激活系统
        if should_activate:
            config.activate_system()
        
        return {
            "status": "success",
            "message": "设置保存成功。" + (" 系统已激活。" if should_activate else ""),
            "configured": config.is_active(),
            "config": updated,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")

@router.post("/api/test/model")
async def test_model_connection(req: TestRequest):
    """
    通用模型连接测试端点
    前端发送完整的模型配置进行测试
    """
    if not req.model_name or not req.api_key or not req.base_url:
        raise HTTPException(status_code=400, detail="缺少必要的配置参数：model_name, api_key, base_url")
    
    # 根据模型类型调用不同的测试方法
    model_type = req.model_type or "chat"  # 默认为 chat 类型
    
    if model_type in ["chat", "summary", "vision"]:
        # 对于聊天模型，检查是否有 chat_model_type 字段来区分文本/多模态
        # chat_model_type 可能的值: "text-model" 或 "multi-model"
        chat_model_type = getattr(req, 'chat_model_type', 'text-model')
        return await TestConnectionService.test_llm_connection(
            req.api_key,
            req.base_url,
            req.model_name,
            model_type=chat_model_type  # 传递具体的模型类型
        )
    elif model_type == "embedding":
        return await TestConnectionService.test_embedding_connection(
            req.api_key,
            req.base_url,
            req.model_name,
        )
    elif model_type == "rerank":
        return await TestConnectionService.test_rerank_connection(
            req.api_key,
            req.base_url,
            req.model_name,
        )
    else:
        raise HTTPException(status_code=400, detail=f"不支持的模型类型: {model_type}")

@router.post("/api/test/llm")
async def test_llm_connection(req: TestRequest):
    """测试LLM连接（兼容旧接口）"""
    default_chat = config.get_default_chat_model() or {}
    return await TestConnectionService.test_llm_connection(
        _resolve(req.api_key, default_chat.get("api_key")),
        _resolve(req.base_url, default_chat.get("base_url")),
        _resolve(req.model_name, default_chat.get("name")),
    )

@router.post("/api/test/embedding")
async def test_embedding_connection(req: TestRequest):
    """测试Embedding模型连接（兼容旧接口）"""
    embedding_cfg = config.get_embedding_model() or {}
    return await TestConnectionService.test_embedding_connection(
        _resolve(req.api_key, embedding_cfg.get("api_key")),
        _resolve(req.base_url, embedding_cfg.get("base_url")),
        _resolve(req.model_name, embedding_cfg.get("name")),
    )

@router.post("/api/test/rerank")
async def test_rerank_connection(req: TestRequest):
    """测试Rerank模型连接（兼容旧接口）"""
    rerank_cfg = config.get_rerank_model() or {}
    return await TestConnectionService.test_rerank_connection(
        _resolve(req.api_key, rerank_cfg.get("api_key")),
        _resolve(req.base_url, rerank_cfg.get("base_url")),
        _resolve(req.model_name, rerank_cfg.get("name")),
    )

@router.post("/api/test/google")
async def test_google_connection(req: TestRequest):
    """测试Google Search连接"""
    # Google Search 配置暂时保持在 Basic_Config 或单独区域
    return await TestConnectionService.test_google_connection(
        _resolve(req.api_key, str(config.get("google_api_key", ""))),
        _resolve(req.cse_id, str(config.get("google_cse_id", ""))),
    )
