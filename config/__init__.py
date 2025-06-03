"""
配置管理模块

提供统一的配置加载和管理功能
"""

import os
import importlib
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 环境变量名
ENV_VAR_NAME = "HZ_FUTURE_SMART_BRAIN_ENV"

# 默认环境
DEFAULT_ENV = "dev"

def get_current_env() -> str:
    """获取当前环境名称"""
    env = os.environ.get(ENV_VAR_NAME, DEFAULT_ENV)
    
    # 加载对应环境的.env文件
    env_file = ROOT_DIR / f".env{f'.{env}' if env != 'dev' else ''}"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # 如果特定环境的.env文件不存在，尝试加载默认的.env文件
        default_env_file = ROOT_DIR / ".env"
        if default_env_file.exists():
            load_dotenv(default_env_file)
    
    return env

def load_config(module_name: Optional[str] = None, env: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置
    
    Args:
        module_name: 模块名称，如果为None则加载基础配置
        env: 环境名称，如果为None则使用当前环境
        
    Returns:
        配置字典
    """
    if env is None:
        env = get_current_env()
    
    # 加载基础配置
    try:
        base_module = importlib.import_module(f"config.{env}")
        config = getattr(base_module, "CONFIG", {})
    except (ImportError, AttributeError):
        print(f"警告: 未找到环境配置 {env}，使用空配置")
        config = {}
    
    # 如果指定了模块，加载模块特定配置
    if module_name:
        try:
            module = importlib.import_module(f"config.modules.{module_name}")
            module_config = getattr(module, f"{module_name.upper()}_CONFIG", {})
            # 合并配置
            config = {**config, **module_config}
        except (ImportError, AttributeError) as e:
            print(f"警告: 加载模块配置 {module_name} 失败: {e}")
    
    return config