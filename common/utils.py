"""
通用工具函数模块

提供项目中常用的工具函数
"""

import os
import json
import hashlib
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal


def ensure_dir(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
    """
    os.makedirs(directory, exist_ok=True)


def safe_json_serialize(obj: Any) -> str:
    """
    安全的JSON序列化，处理特殊类型
    
    Args:
        obj: 要序列化的对象
        
    Returns:
        JSON字符串
    """
    def json_serializer(obj):
        """JSON序列化器，处理特殊类型"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    return json.dumps(obj, default=json_serializer, ensure_ascii=False, indent=2)


def safe_json_deserialize(json_str: str, default: Any = None) -> Any:
    """
    安全的JSON反序列化
    
    Args:
        json_str: JSON字符串
        default: 解析失败时的默认值
        
    Returns:
        解析后的对象
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def generate_hash(data: Union[str, bytes], algorithm: str = "md5") -> str:
    """
    生成数据的哈希值
    
    Args:
        data: 要哈希的数据
        algorithm: 哈希算法 (md5, sha1, sha256)
        
    Returns:
        哈希值字符串
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    hash_func = getattr(hashlib, algorithm.lower())
    return hash_func(data).hexdigest()


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    扁平化嵌套字典
    
    Args:
        d: 嵌套字典
        parent_key: 父键名
        sep: 分隔符
        
    Returns:
        扁平化后的字典
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d: Dict[str, Any], sep: str = '.') -> Dict[str, Any]:
    """
    反扁平化字典
    
    Args:
        d: 扁平化的字典
        sep: 分隔符
        
    Returns:
        嵌套字典
    """
    result = {}
    for key, value in d.items():
        keys = key.split(sep)
        current = result
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    return result


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并多个字典
    
    Args:
        *dicts: 要合并的字典
        
    Returns:
        合并后的字典
    """
    result = {}
    for d in dicts:
        for key, value in d.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            else:
                result[key] = value
    return result


def filter_none_values(d: Dict[str, Any], recursive: bool = True) -> Dict[str, Any]:
    """
    过滤字典中的None值
    
    Args:
        d: 字典
        recursive: 是否递归处理嵌套字典
        
    Returns:
        过滤后的字典
    """
    result = {}
    for key, value in d.items():
        if value is not None:
            if recursive and isinstance(value, dict):
                filtered_value = filter_none_values(value, recursive)
                if filtered_value:  # 只添加非空字典
                    result[key] = filtered_value
            else:
                result[key] = value
    return result


def get_nested_value(d: Dict[str, Any], key_path: str, default: Any = None, sep: str = '.') -> Any:
    """
    获取嵌套字典中的值
    
    Args:
        d: 字典
        key_path: 键路径，如 'a.b.c'
        default: 默认值
        sep: 分隔符
        
    Returns:
        值或默认值
    """
    keys = key_path.split(sep)
    current = d
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default


def set_nested_value(d: Dict[str, Any], key_path: str, value: Any, sep: str = '.') -> None:
    """
    设置嵌套字典中的值
    
    Args:
        d: 字典
        key_path: 键路径，如 'a.b.c'
        value: 要设置的值
        sep: 分隔符
    """
    keys = key_path.split(sep)
    current = d
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分块
    
    Args:
        lst: 列表
        chunk_size: 块大小
        
    Returns:
        分块后的列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def remove_duplicates(lst: List[Any], key_func: Optional[callable] = None) -> List[Any]:
    """
    去除列表中的重复项
    
    Args:
        lst: 列表
        key_func: 用于比较的键函数
        
    Returns:
        去重后的列表
    """
    if key_func is None:
        return list(dict.fromkeys(lst))
    
    seen = set()
    result = []
    for item in lst:
        key = key_func(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
