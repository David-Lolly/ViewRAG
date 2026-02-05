import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from collections import OrderedDict

logger = logging.getLogger(__name__)


# 自定义 YAML Dumper 保持字段顺序
class OrderedDumper(yaml.SafeDumper):
    pass

def _dict_representer(dumper, data):
    return dumper.represent_mapping(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        data.items())

OrderedDumper.add_representer(OrderedDict, _dict_representer)
OrderedDumper.add_representer(dict, _dict_representer)


class ConfigManager:
    """
    基于 YAML 文件的配置管理器，支持新的 config.yaml 结构
    """
    _instance = None
    _lock = threading.Lock()
    _config: Dict[str, Any] = {}
    _is_initialized = False
    _CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def initialize_config(self):
        """
        加载 YAML 配置文件，仅执行一次。
        """
        if not self._is_initialized:
            with self._lock:
                if not self._is_initialized:
                    logger.info("正在初始化配置...")
                    self.load_config()
                    self.validate_config()
                    self._is_initialized = True
        else:
            logger.info("ConfigManager 已经初始化。")

    def load_config(self):
        """
        从 YAML 文件加载配置。
        """
        logger.info(f"正在从 {self._CONFIG_PATH} 加载配置...")
        try:
            if not self._CONFIG_PATH.exists():
                logger.warning(f"配置文件 {self._CONFIG_PATH} 不存在，使用默认空配置。")
                self._config = {"Basic_Config": {}, "Model_Config": {}}
                return
            
            with open(self._CONFIG_PATH, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            logger.info("配置已成功加载。")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}", exc_info=True)
            raise RuntimeError(f"无法加载或解析 config.yaml: {e}")

    def validate_config(self):
        """
        验证关键模型配置是否存在。如果系统未激活，仅警告而不抛出异常。
        """
        errors = []
        model_config = self._config.get('Model_Config', {})
        
        # 检查 LLM 相关配置
        if not model_config.get('LLM', {}).get('summary_model'):
            errors.append("缺少 'summary_model' 配置")
        if not model_config.get('LLM', {}).get('vision_model'):
            errors.append("缺少 'vision_model' 配置")
        if not model_config.get('LLM', {}).get('chat_model'):
            errors.append("缺少 'chat_model' 配置")
        
        # 检查 Embedding 配置
        if not model_config.get('Embedding', {}).get('embedding_model'):
            errors.append("缺少 'embedding_model' 配置")
        
        # 检查 Rerank 配置
        if not model_config.get('Rerank', {}).get('rerank_model'):
            errors.append("缺少 'rerank_model' 配置")
        
        if errors:
            if self.is_active():
                # 如果系统已激活但配置不全，这是严重错误
                raise ValueError(f"配置验证失败: {', '.join(errors)}")
            else:
                # 如果未激活，仅警告
                logger.warning(f"配置不完整: {', '.join(errors)}. 等待前端配置激活。")
    
    def _order_model_fields(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        对模型配置字段按指定顺序排序: name, base_url, api_key, description
        """
        if not isinstance(model_config, dict):
            return model_config
        
        ordered = OrderedDict()
        # 定义字段顺序
        field_order = ['name', 'base_url', 'api_key', 'temperature', 'description', 'is_default']
        
        # 按顺序添加存在的字段
        for field in field_order:
            if field in model_config:
                ordered[field] = model_config[field]
        
        # 添加其他未列出的字段
        for key, value in model_config.items():
            if key not in ordered:
                ordered[key] = value
        
        return ordered
    
    def _order_config_structure(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        对整个配置结构进行字段排序
        """
        ordered_config = OrderedDict()
        
        # 基础配置
        if 'Basic_Config' in config:
            ordered_config['Basic_Config'] = config['Basic_Config']
        
        # 模型配置
        if 'Model_Config' in config:
            model_config = OrderedDict()
            
            # LLM 配置
            if 'LLM' in config['Model_Config']:
                llm = OrderedDict()
                llm_src = config['Model_Config']['LLM']
                
                # 处理每个模型配置
                for key in ['summary_model', 'vision_model', 'chat_model']:
                    if key in llm_src:
                        if key == 'chat_model' and isinstance(llm_src[key], list):
                            # chat_model 是数组，需要对每个元素排序
                            llm[key] = [self._order_model_fields(m) for m in llm_src[key]]
                        else:
                            llm[key] = self._order_model_fields(llm_src[key])
                
                model_config['LLM'] = llm
            
            # Embedding 配置
            if 'Embedding' in config['Model_Config']:
                embedding = OrderedDict()
                if 'embedding_model' in config['Model_Config']['Embedding']:
                    embedding['embedding_model'] = self._order_model_fields(
                        config['Model_Config']['Embedding']['embedding_model']
                    )
                model_config['Embedding'] = embedding
            
            # Rerank 配置
            if 'Rerank' in config['Model_Config']:
                rerank = OrderedDict()
                if 'rerank_model' in config['Model_Config']['Rerank']:
                    rerank['rerank_model'] = self._order_model_fields(
                        config['Model_Config']['Rerank']['rerank_model']
                    )
                model_config['Rerank'] = rerank
            
            ordered_config['Model_Config'] = model_config
        
        return ordered_config

    def save_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存配置到 YAML 文件并重新加载。
        
        Args:
            new_config: 新的完整配置字典
            
        Returns:
            更新后的配置字典
        """
        with self._lock:
            try:
                # 备份现有配置
                backup_path = self._CONFIG_PATH.with_suffix('.yaml.bak')
                if self._CONFIG_PATH.exists():
                    import shutil
                    shutil.copy2(self._CONFIG_PATH, backup_path)
                    logger.info(f"已备份现有配置到 {backup_path}")
                
                # 对配置字段排序
                ordered_config = self._order_config_structure(new_config)
                
                # 写入新配置，使用 OrderedDumper 保持顺序
                with open(self._CONFIG_PATH, 'w', encoding='utf-8') as f:
                    yaml.dump(ordered_config, f, Dumper=OrderedDumper, 
                            allow_unicode=True, default_flow_style=False, sort_keys=False)
                
                # 重新加载
                self.load_config()
                logger.info("配置已成功保存并重新加载。")
                return self._config
            except Exception as e:
                logger.error(f"保存配置失败: {e}", exc_info=True)
                raise RuntimeError(f"无法保存配置到 config.yaml: {e}")

    # === 基本配置访问方法 ===
    
    def get_retrieval_version(self) -> str:
        """获取召回版本 (v1 或 v2)"""
        return self._config.get('Basic_Config', {}).get('RETRIEVAL_VERSION', 'v2')
    
    def get_retrieval_quality(self) -> str:
        """获取召回质量 (high, medium, low)"""
        return self._config.get('Basic_Config', {}).get('RETRIEVAL_QUALITY', 'high')
    
    def is_active(self) -> bool:
        """检查系统是否已通过前端配置激活"""
        return self._config.get('Basic_Config', {}).get('IS_ACTIVE', False)
    
    def activate_system(self):
        """将 IS_ACTIVE 字段设置为 True 并写回文件"""
        with self._lock:
            if 'Basic_Config' not in self._config:
                self._config['Basic_Config'] = {}
            self._config['Basic_Config']['IS_ACTIVE'] = True
            
            try:
                # 对配置排序
                ordered_config = self._order_config_structure(self._config)
                
                with open(self._CONFIG_PATH, 'w', encoding='utf-8') as f:
                    yaml.dump(ordered_config, f, Dumper=OrderedDumper,
                            allow_unicode=True, default_flow_style=False, sort_keys=False)
                logger.info("系统已成功激活 (IS_ACTIVE = True)。")
            except Exception as e:
                logger.error(f"激活系统失败: {e}", exc_info=True)
                raise RuntimeError(f"无法更新 config.yaml: {e}")

    # === 模型配置访问方法 ===
    
    def get_summary_model(self) -> Optional[Dict[str, Any]]:
        """获取摘要模型配置"""
        return self._config.get('Model_Config', {}).get('LLM', {}).get('summary_model')
    
    def get_vision_model(self) -> Optional[Dict[str, Any]]:
        """获取视觉模型配置"""
        return self._config.get('Model_Config', {}).get('LLM', {}).get('vision_model')
    
    def get_chat_models(self) -> List[Dict[str, Any]]:
        """获取所有对话模型配置列表"""
        return self._config.get('Model_Config', {}).get('LLM', {}).get('chat_model', [])
    
    def get_default_chat_model(self) -> Optional[Dict[str, Any]]:
        """获取默认对话模型配置"""
        chat_models = self.get_chat_models()
        for model in chat_models:
            if model.get('is_default'):
                return model
        return chat_models[0] if chat_models else None
    
    def get_chat_model_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取指定的对话模型配置"""
        chat_models = self.get_chat_models()
        for model in chat_models:
            if model.get('name') == name:
                return model
        return None
    
    def get_embedding_model(self) -> Optional[Dict[str, Any]]:
        """获取嵌入模型配置"""
        return self._config.get('Model_Config', {}).get('Embedding', {}).get('embedding_model')
    
    def get_rerank_model(self) -> Optional[Dict[str, Any]]:
        """获取重排序模型配置"""
        return self._config.get('Model_Config', {}).get('Rerank', {}).get('rerank_model')
    
    # === 兼容旧接口的方法 ===
    
    def get(self, key: str, default=None):
        """
        兼容旧代码的通用获取方法。
        警告: 建议使用具体的 get_xxx_model() 方法。
        """
        # 尝试从不同位置获取配置
        if key == 'retrieval_version':
            return self.get_retrieval_version()
        elif key == 'retrieval_quality':
            return self.get_retrieval_quality()
        elif key == 'active':
            return self.is_active()
        
        # 尝试从模型配置中查找
        model_config = self._config.get('Model_Config', {})
        
        # Embedding 相关
        if key == 'embedding_model_name':
            emb = self.get_embedding_model()
            return emb.get('name') if emb else default
        elif key == 'embedding_api_key':
            emb = self.get_embedding_model()
            return emb.get('api_key') if emb else default
        elif key == 'embedding_base_url':
            emb = self.get_embedding_model()
            return emb.get('base_url') if emb else default
        
        # Rerank 相关
        elif key == 'rerank_model_name':
            rerank = self.get_rerank_model()
            return rerank.get('name') if rerank else default
        elif key == 'rerank_api_key':
            rerank = self.get_rerank_model()
            return rerank.get('api_key') if rerank else default
        elif key == 'rerank_base_url':
            rerank = self.get_rerank_model()
            return rerank.get('base_url') if rerank else default
        
        # LLM 相关 (使用默认 chat 模型)
        elif key == 'llm_model_name':
            chat = self.get_default_chat_model()
            return chat.get('name') if chat else default
        elif key == 'llm_api_key':
            chat = self.get_default_chat_model()
            return chat.get('api_key') if chat else default
        elif key == 'llm_base_url':
            chat = self.get_default_chat_model()
            return chat.get('base_url') if chat else default
        
        return default
    
    def get_all(self) -> Dict[str, Any]:
        """获取完整配置字典"""
        return self._config
    
    def is_configured(self) -> bool:
        """
        兼容旧接口：检查系统是否已配置完成。
        新逻辑：检查 IS_ACTIVE 状态。
        """
        return self.is_active()


# 创建全局单例
config = ConfigManager()
