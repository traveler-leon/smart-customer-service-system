import asyncio
from typing import Dict, Any, Optional
from common.logging import setup_logger, get_logger
from config.factory import get_logger_config

from .base.factory import AsyncSmartSqlFactory
from .base.interfaces import AsyncPlugin

# 获取日志配置并初始化日志系统
logger_config = get_logger_config("text2sql")
setup_logger(**logger_config)

# 获取text2sql模块的日志记录器
logger = get_logger("text2sql")

async def create_text2sql(config: Optional[Dict[str, Any]] = None):
    """异步创建text2sql实例"""
    logger.info("开始创建异步text2sql实例")
    # 异步创建实例
    smart_sql = await AsyncSmartSqlFactory.create(config)
    logger.info("异步text2sql实例创建成功")
    return smart_sql

# 为了兼容性提供同步入口点
def sync_create_text2sql(config: Optional[Dict[str, Any]] = None):
    """同步创建text2sql实例（内部使用异步）"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(create_text2sql(config))
