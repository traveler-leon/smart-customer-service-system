"""
API 模块

提供 FastAPI 路由和接口
"""

from config.factory import get_logger_config
from common.logging import setup_logger, get_logger
from .router import api_router

# 初始化API模块日志
logger_config = get_logger_config("api")
setup_logger(**logger_config)
logger = get_logger("api")

logger.info("API模块初始化完成")

__all__ = ["api_router"]