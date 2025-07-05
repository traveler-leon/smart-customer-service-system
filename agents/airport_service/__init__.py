"""
机场客服多智能体系统
"""
from config.factory import get_logger_config
from common.logging import setup_logger, get_logger
from .main_graph import build_airport_service_graph
from .graph_compile import graph_manager

# 初始化agents模块日志
logger_config = get_logger_config("agents")
setup_logger(**logger_config)
logger = get_logger("agents.airport_service")
logger.info("机场客服多智能体系统初始化完成")


__all__ = [
    "build_airport_service_graph"
    ,"graph_manager"
    ]
