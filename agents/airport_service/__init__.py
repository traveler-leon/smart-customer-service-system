"""
机场客服多智能体系统
"""
from config.factory import get_logger_config
from common.logging import setup_logger, get_logger
from langchain_openai import ChatOpenAI
from config.utils import config_manager
from typing import Dict,List
from langmem import create_memory_store_manager,ReflectionExecutor
from agents.airport_service.state import UserProfile,Episode,BusinessRecommendState,QuestionRecommendState

from .main_graph import build_airport_service_graph
from .question_recommend_graph import build_question_recommend_graph
from .business_recommend_graph import build_business_recommend_graph
from .graph_compile import graph_manager

from config.factory import get_logger_config
from common.logging import setup_logger
# 初始化nodes模块日志
logger_config = get_logger_config("agents")
setup_logger(**logger_config)

# 从 core 模块导入共用组件
from .core import (
    content_model, base_model, structed_model,
    filter_messages_for_agent, filter_messages_for_llm, 
    max_msg_len, max_tokens, memery_delay,
    KB_SIMILARITY_THRESHOLD, emotion
)
try:
    from .core import image_model
except ImportError:
    image_model = None


# 知识抽取
## 用户画像
# profile_manager = create_memory_store_manager(
#     base_model,
#     namespace=("users", "{passenger_id}", "profile"),  # Isolate profiles by user
#     schemas=[UserProfile],
#     instructions="根据用户对话内容，提取用户画像信息",
#     enable_inserts=False,  # Update existing profile only
# )
# profile_executor = ReflectionExecutor(profile_manager)

# ##历史事件
# episode_manager = create_memory_store_manager(
#     base_model,
#     namespace=("memories", "episodes"),
#     schemas=[Episode],
#     instructions="提取具有代表性的卓越问题解决案例，包括其为何有效的原因。",
#     enable_inserts=True,  
# )
# episode_executor = ReflectionExecutor(episode_manager)


__all__ = [
    "build_airport_service_graph",
    "build_question_recommend_graph",
    "build_business_recommend_graph",
    "graph_manager"
    ]
