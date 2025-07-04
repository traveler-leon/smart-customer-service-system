"""
Common 通用模块

提供项目中常用的工具、装饰器、验证器等功能
"""

from .logging import setup_logger, get_logger
from .utils import (
    ensure_dir, safe_json_serialize, safe_json_deserialize,
    generate_hash, flatten_dict, unflatten_dict, merge_dicts,
    filter_none_values, get_nested_value, set_nested_value,
    chunk_list, remove_duplicates
)
from .decorators import (
    retry, async_retry, timing, async_timing, cache_result,
    validate_types, deprecated
)
from .validators import Validator, ValidationError

__all__ = [
    # 日志
    'setup_logger', 'get_logger',
    
    # 工具函数
    'ensure_dir', 'safe_json_serialize', 'safe_json_deserialize',
    'generate_hash', 'flatten_dict', 'unflatten_dict', 'merge_dicts',
    'filter_none_values', 'get_nested_value', 'set_nested_value',
    'chunk_list', 'remove_duplicates',
    
    # 装饰器
    'retry', 'async_retry', 'timing', 'async_timing', 'cache_result',
    'validate_types', 'deprecated',
    
    # 验证器
    'Validator', 'ValidationError'
]
