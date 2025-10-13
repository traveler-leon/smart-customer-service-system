"""
机场客服多智能体系统
"""
from .main_graph import build_airport_service_graph
from .question_recommend_graph import build_question_recommend_graph
from .business_recommend_graph import build_business_recommend_graph
from .graph_compile import graph_manager

from config.factory import get_logger_config
from common.logging import setup_logger
# 初始化nodes模块日志
logger_config = get_logger_config("agents")
setup_logger(**logger_config)


__all__ = [
    "build_airport_service_graph",
    "build_question_recommend_graph",
    "build_business_recommend_graph",
    "graph_manager"
    ]
