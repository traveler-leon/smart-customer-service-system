"""
text2kb - 知识库检索模块
"""

from .retrieval import retrieve_from_kb,retrieve_from_kb_by_agent

# 确保导入时不会引起循环导入
try:
    from common.logging import setup_logger, get_logger
    from config.factory import get_logger_config

    # 获取日志配置并初始化日志系统
    logger_config = get_logger_config("text2kb")
    setup_logger(**logger_config)

    # 获取模块的主日志记录器
    logger = get_logger("text2kb")
    logger.debug("text2kb模块初始化")
except ImportError:
    # 如果日志模块未安装或未配置，忽略错误
    pass

__all__ = [
    'retrieve_from_kb',
    'retrieve_from_kb_by_agent'
] 