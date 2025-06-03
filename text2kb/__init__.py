"""
text2kb - 知识库检索模块
"""

from .retrieval import retrieve_from_kb,retrieve_from_kb_by_agent

# 确保导入时不会引起循环导入
try:
    from common.logging import setup_logger, get_logger
    
    # 初始化日志系统
    setup_logger(
        log_dir="logs/text2kb",
        log_level="INFO",
        max_bytes=10 * 1024 * 1024,  # 10MB
        backup_count=5
    )
    
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