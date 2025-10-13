"""
工具集模块

提供机场客服系统的各种工具函数
"""

from config.factory import get_logger_config
from common.logging import setup_logger, get_logger

# 初始化tools模块日志
logger_config = get_logger_config("agents")
setup_logger(**logger_config)
logger = get_logger("agents.tools")

from .airport import airport_knowledge_query2docs,airport_knowledge_query2docs_main
from .flight import flight_info_query2docs,get_text2sql_instance
from .business import wheelchair_rental

logger.info("工具集模块初始化完成")

__all__ = [
    "airport_knowledge_query2docs"
    , "airport_knowledge_query2docs_main"
    , "get_text2sql_instance"
    , "flight_info_query2docs"
    , "wheelchair_rental"
]