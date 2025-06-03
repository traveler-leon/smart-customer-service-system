import asyncio
import hashlib
import os
from typing import Union, Callable, Any
import json
import uuid

def deterministic_uuid(content: str) -> str:
    """生成基于内容的确定性UUID"""
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    elif isinstance(content, bytes):
        content_bytes = content
    else:
        raise ValueError(f"不支持的内容类型: {type(content)}")
    
    # 计算SHA-256哈希
    hash_object = hashlib.sha256(content_bytes)
    hash_hex = hash_object.hexdigest()
    
    # 使用UUID5基于哈希生成确定性UUID
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000000")
    content_uuid = str(uuid.uuid5(namespace, hash_hex))
    
    return content_uuid

async def async_validate_config_path(path: str) -> None:
    """异步验证配置文件路径"""
    loop = asyncio.get_event_loop()
    
    # 检查路径是否存在
    exists = await loop.run_in_executor(
        None,
        lambda: os.path.exists(path)
    )
    if not exists:
        raise ValueError(f'配置文件不存在: {path}')
    
    # 检查是否是文件
    is_file = await loop.run_in_executor(
        None,
        lambda: os.path.isfile(path)
    )
    if not is_file:
        raise ValueError(f'配置路径应该是文件: {path}')
    
    # 检查是否可读
    is_readable = await loop.run_in_executor(
        None,
        lambda: os.access(path, os.R_OK)
    )
    if not is_readable:
        raise ValueError(f'无法读取配置文件，请检查权限: {path}')

class AsyncRetry:
    """异步重试装饰器"""
    
    def __init__(self, max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            retry_count = 0
            current_delay = self.delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except self.exceptions as e:
                    retry_count += 1
                    
                    if retry_count > self.max_retries:
                        raise
                    
                    # 等待一段时间后重试
                    await asyncio.sleep(current_delay)
                    current_delay *= self.backoff
        
        return wrapper

class AsyncLazy:
    """异步延迟加载装饰器"""
    
    def __init__(self, func):
        self.func = func
        self.value = None
        self.initialized = False
    
    async def __call__(self, *args, **kwargs):
        if not self.initialized:
            self.value = await self.func(*args, **kwargs)
            self.initialized = True
        return self.value

async def async_json_dump(data: Any, file_path: str) -> None:
    """异步将数据写入JSON文件"""
    loop = asyncio.get_event_loop()
    
    # 在线程池中序列化JSON
    json_str = await loop.run_in_executor(
        None,
        lambda: json.dumps(data, ensure_ascii=False, indent=2)
    )
    
    # 异步写入文件
    async with open(file_path, 'w', encoding='utf-8') as f:
        await f.write(json_str)

async def async_json_load(file_path: str) -> Any:
    """异步从JSON文件加载数据"""
    # 异步读取文件
    async with open(file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
    
    # 在线程池中解析JSON
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(
        None,
        lambda: json.loads(content)
    )
    
    return data
