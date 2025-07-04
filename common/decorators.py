"""
通用装饰器模块

提供项目中常用的装饰器
"""

import time
import asyncio
import functools
from typing import Any, Callable, Optional, Union
from common.logging import get_logger

logger = get_logger("common.decorators")


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
          exceptions: tuple = (Exception,)) -> Callable:
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}, "
                                     f"{current_delay:.2f}秒后重试")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"函数 {func.__name__} 在 {max_attempts} 次尝试后仍然失败")
            
            raise last_exception
        
        return wrapper
    return decorator


def async_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0,
                exceptions: tuple = (Exception,)) -> Callable:
    """
    异步重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"异步函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}, "
                                     f"{current_delay:.2f}秒后重试")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"异步函数 {func.__name__} 在 {max_attempts} 次尝试后仍然失败")
            
            raise last_exception
        
        return wrapper
    return decorator


def timing(func: Callable) -> Callable:
    """
    计时装饰器
    
    Args:
        func: 要计时的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"函数 {func.__name__} 执行时间: {execution_time:.4f}秒")
    
    return wrapper


def async_timing(func: Callable) -> Callable:
    """
    异步计时装饰器
    
    Args:
        func: 要计时的异步函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"异步函数 {func.__name__} 执行时间: {execution_time:.4f}秒")
    
    return wrapper


def cache_result(ttl: Optional[float] = None) -> Callable:
    """
    结果缓存装饰器
    
    Args:
        ttl: 缓存生存时间（秒），None表示永久缓存
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 创建缓存键
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()
            
            # 检查缓存
            if key in cache:
                cached_result, cached_time = cache[key]
                if ttl is None or (current_time - cached_time) < ttl:
                    logger.debug(f"函数 {func.__name__} 使用缓存结果")
                    return cached_result
                else:
                    # 缓存过期，删除
                    del cache[key]
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            logger.debug(f"函数 {func.__name__} 结果已缓存")
            return result
        
        # 添加清除缓存的方法
        wrapper.clear_cache = lambda: cache.clear()
        wrapper.cache_info = lambda: {"size": len(cache), "keys": list(cache.keys())}
        
        return wrapper
    return decorator


def validate_types(**type_hints) -> Callable:
    """
    类型验证装饰器
    
    Args:
        **type_hints: 参数类型提示
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数参数名
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # 验证类型
            for param_name, expected_type in type_hints.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if value is not None and not isinstance(value, expected_type):
                        raise TypeError(f"参数 {param_name} 期望类型 {expected_type.__name__}, "
                                      f"实际类型 {type(value).__name__}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def deprecated(reason: str = "此函数已废弃") -> Callable:
    """
    废弃警告装饰器
    
    Args:
        reason: 废弃原因
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import warnings
            warnings.warn(f"{func.__name__} 已废弃: {reason}", 
                         DeprecationWarning, stacklevel=2)
            logger.warning(f"使用了废弃函数 {func.__name__}: {reason}")
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
