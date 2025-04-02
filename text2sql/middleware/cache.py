import hashlib
import json
import asyncio
from typing import Dict, Any
from ..base.interfaces import AsyncMiddleware
from common.logging import get_logger

# 获取日志记录器
logger = get_logger("text2sql.middleware.cache")

class CacheMiddleware(AsyncMiddleware):
    """异步缓存中间件"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.cache = {}
        self.max_size = self.config.get("max_size", 100)
        self.ttl = self.config.get("ttl", 3600)  # 缓存过期时间（秒）
        self.lock = asyncio.Lock()  # 用于保护缓存访问的锁
        logger.info(f"初始化缓存中间件，max_size={self.max_size}, ttl={self.ttl}")
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """异步处理请求，检查缓存"""
        # 生成缓存键
        question = request['question']
        kwargs = request['kwargs']
        
        cache_key = await self._generate_cache_key(question, kwargs)
        
        # 异步检查缓存（使用锁确保线程安全）
        async with self.lock:
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                timestamp, result = entry
                
                # 检查是否过期
                if self.ttl is None or (asyncio.get_event_loop().time() - timestamp) < self.ttl:
                    # 缓存命中，修改请求
                    logger.info(f"缓存命中: {cache_key[:8]}...")
                    request['__cached_result'] = result
                else:
                    # 缓存过期，删除
                    logger.info(f"缓存过期: {cache_key[:8]}...")
                    del self.cache[cache_key]
            else:
                logger.debug(f"缓存未命中: {cache_key[:8]}...")
        
        return request
    
    async def process_response(self, response: Any) -> Any:
        """异步处理响应，更新缓存"""
        # 如果是缓存结果，直接返回
        if hasattr(response, '__cached_result'):
            return response['__cached_result']
        
        # 更新缓存
        question = response.get('__original_question')
        kwargs = response.get('__original_kwargs')
        
        if question and kwargs:
            cache_key = await self._generate_cache_key(question, kwargs)
            
            # 异步更新缓存（使用锁确保线程安全）
            async with self.lock:
                # 限制缓存大小
                if len(self.cache) >= self.max_size:
                    # LRU策略：删除最旧的项
                    oldest_key = min(self.cache.items(), key=lambda x: x[1][0])[0]
                    del self.cache[oldest_key]
                
                # 添加到缓存
                self.cache[cache_key] = (asyncio.get_event_loop().time(), response)
        
        return response
    
    async def _generate_cache_key(self, question, kwargs):
        """异步生成缓存键"""
        key_data = {
            'question': question,
            'kwargs': {k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool, list, dict))}
        }
        
        # 异步序列化和哈希计算
        loop = asyncio.get_event_loop()
        key_str = await loop.run_in_executor(
            None, lambda: json.dumps(key_data, sort_keys=True)
        )
        
        # 异步计算哈希值
        hash_obj = await loop.run_in_executor(
            None, lambda: hashlib.md5(key_str.encode()).hexdigest()
        )
        
        return hash_obj
