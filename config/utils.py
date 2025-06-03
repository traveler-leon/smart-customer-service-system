"""
配置工具模块

提供便捷的配置获取功能
"""

import os
from typing import Dict, Any, Optional
from . import load_config

class ConfigManager:
    """配置管理器类，提供便捷的配置访问方式"""
    
    _instance = None
    _cache = {}
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._init_env_vars()
        return cls._instance
    
    def _init_env_vars(self):
        """初始化环境变量"""
        # 环境变量优先级高于配置文件，可以在这里处理特定的环境变量
        pass
    
    def get_text2sql_config(self) -> Dict[str, Any]:
        """获取Text2SQL模块配置"""
        if "text2sql" not in self._cache:
            # 从text2sql模块配置中加载
            self._cache["text2sql"] = load_config("text2sql")
        
        return self._cache["text2sql"]
    
    def get_text2kb_config(self) -> Dict[str, Any]:
        """获取Text2KB模块配置"""
        if "text2kb" not in self._cache:
            self._cache["text2kb"] = load_config("text2kb")
        
        return self._cache["text2kb"]
    
    def get_agents_config(self) -> Dict[str, Any]:
        """获取agents模块配置"""
        if "agents" not in self._cache:
            self._cache["agents"] = load_config("agents")
        
        return self._cache["agents"]
    
    def get_model_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        if "model" not in self._cache:
            # 从通用配置中获取模型配置
            config = load_config()
            # 如果通用配置中没有llm配置，尝试从text2sql模块获取
            if "llm" not in config:
                text2sql_config = self.get_text2sql_config()
                llm_config = text2sql_config.get("llm", {})
            else:
                llm_config = config.get("llm", {})
                
            self._cache["model"] = {
                "base_url": llm_config.get("base_url"),
                "api_key": llm_config.get("api_key"),
                "model": llm_config.get("model"),
                "temperature": llm_config.get("temperature", 0.5)
            }
        
        return self._cache["model"]
    
    def clear_cache(self):
        """清除配置缓存"""
        self._cache.clear()

# 创建全局配置管理器实例
config_manager = ConfigManager() 