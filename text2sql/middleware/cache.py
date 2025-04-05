import hashlib
import json
import asyncio
import time  # 使用time而不是asyncio.get_event_loop().time()
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
        self.hits = 0
        self.misses = 0
        logger.info(f"初始化缓存中间件，max_size={self.max_size}, ttl={self.ttl}")
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """异步处理请求，检查缓存"""
        # 生成缓存键
        question = request['question']
        kwargs = request.get('kwargs', {})
        
        # 详细日志
        logger.debug(f"处理请求：question={question}, kwargs={kwargs}")
        
        cache_key = await self._generate_cache_key(question, kwargs)
        
        # 异步检查缓存（使用锁确保线程安全）
        async with self.lock:
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                timestamp, result = entry
                
                # 检查是否过期
                current_time = time.time()  # 使用time.time()替代asyncio.get_event_loop().time()
                if self.ttl is None or (current_time - timestamp) < self.ttl:
                    # 缓存命中，修改请求
                    self.hits += 1
                    logger.info(f"缓存命中 [{self.hits}/{self.hits+self.misses}]: key={cache_key[:8]}..., age={int(current_time-timestamp)}秒")
                    request['__cached_result'] = result
                else:
                    # 缓存过期，删除
                    self.misses += 1
                    logger.info(f"缓存过期 [{self.misses}/{self.hits+self.misses}]: key={cache_key[:8]}..., age={int(current_time-timestamp)}秒 > ttl={self.ttl}秒")
                    del self.cache[cache_key]
            else:
                self.misses += 1
                logger.info(f"缓存未命中 [{self.misses}/{self.hits+self.misses}]: key={cache_key[:8]}...")
        
        return request
    
    async def process_response(self, response: Any) -> Any:
        """异步处理响应，更新缓存"""
        # 检查response是否是字典并包含__cached_result标记
        if isinstance(response, dict) and '__cached_result' in response:
            logger.debug(f"返回缓存结果: {response['__cached_result']}")
            return response['__cached_result']
        
        # 获取原始问题和参数
        if isinstance(response, dict):
            question = response.get('__original_question')
            kwargs = response.get('__original_kwargs', {})
        else:
            # 从当前上下文中获取（这可能在某些实现中不可用）
            question = getattr(self, '__current_question', None)
            kwargs = getattr(self, '__current_kwargs', {})
            
            # 日志
            if question is None:
                logger.warning("无法从响应中提取原始问题，缓存可能无法正常工作")
                return response
        
        # 存储当前问题和参数以便下次使用
        self.__current_question = question
        self.__current_kwargs = kwargs
        
        if question:
            cache_key = await self._generate_cache_key(question, kwargs)
            
            # 异步更新缓存（使用锁确保线程安全）
            async with self.lock:
                # 限制缓存大小
                if len(self.cache) >= self.max_size:
                    # LRU策略：删除最旧的项
                    oldest_key = min(self.cache.items(), key=lambda x: x[1][0])[0]
                    logger.debug(f"缓存已满，删除最旧项: {oldest_key[:8]}...")
                    del self.cache[oldest_key]
                
                # 添加到缓存 - 使用time.time()
                self.cache[cache_key] = (time.time(), response)
                logger.info(f"添加缓存: key={cache_key[:8]}, 缓存项总数={len(self.cache)}")
        
        return response
    
    async def _generate_cache_key(self, question, kwargs):
        """异步生成缓存键"""
        # 简化kwargs，只保留基本类型
        simple_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, (str, int, float, bool)):
                simple_kwargs[k] = v
            elif isinstance(v, (list, tuple)) and all(isinstance(x, (str, int, float, bool)) for x in v):
                simple_kwargs[k] = list(v)
        
        key_data = {
            'question': question,
            'kwargs': simple_kwargs
        }
        
        # 序列化和哈希计算
        key_str = json.dumps(key_data, sort_keys=True)
        hash_obj = hashlib.md5(key_str.encode()).hexdigest()
        
        logger.debug(f"生成缓存键: question='{question}', key={hash_obj}")
        return hash_obj

    async def clear_cache(self, question: str, kwargs: dict = None):
        """清除指定问题的缓存"""
        if kwargs is None:
            kwargs = {}
        
        # 生成缓存键
        cache_key = await self._generate_cache_key(question, kwargs)
        
        # 使用锁保护缓存操作
        async with self.lock:
            if cache_key in self.cache:
                del self.cache[cache_key]
                logger.info(f"已清除问题缓存: key={cache_key[:8]}, question='{question}'")
                return True
            else:
                logger.info(f"未找到需要清除的缓存: key={cache_key[:8]}, question='{question}'")
                return False
