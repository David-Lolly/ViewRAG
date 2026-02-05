from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ModelConfigBase(BaseModel):
    """模型配置基类"""
    name: str
    base_url: str
    api_key: str
    temperature: Optional[float] = 0.5
    description: Optional[str] = None


class ChatModelConfig(ModelConfigBase):
    """对话模型配置"""
    type: Optional[str] = "text-model"  # text-model 或 multi-model
    is_default: Optional[bool] = False


class BasicConfig(BaseModel):
    """基础配置"""
    RETRIEVAL_VERSION: Optional[str] = "v2"
    RETRIEVAL_QUALITY: Optional[str] = "high"
    IS_ACTIVE: Optional[bool] = False


class LLMConfig(BaseModel):
    """LLM 配置"""
    summary_model: Optional[ModelConfigBase] = None
    vision_model: Optional[ModelConfigBase] = None
    chat_model: Optional[List[ChatModelConfig]] = None


class EmbeddingConfig(BaseModel):
    """嵌入模型配置"""
    embedding_model: Optional[ModelConfigBase] = None


class RerankConfig(BaseModel):
    """重排序模型配置"""
    rerank_model: Optional[ModelConfigBase] = None


class ModelConfig(BaseModel):
    """模型配置集合"""
    LLM: Optional[LLMConfig] = None
    Embedding: Optional[EmbeddingConfig] = None
    Rerank: Optional[RerankConfig] = None


class SystemConfig(BaseModel):
    """完整系统配置"""
    Basic_Config: Optional[BasicConfig] = None
    Model_Config: Optional[ModelConfig] = None


class ConfigSaveRequest(BaseModel):
    """配置保存请求"""
    config: Dict[str, Any]  # 接收完整的配置字典
    activate: Optional[bool] = False  # 是否激活系统
