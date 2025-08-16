"""
机场服务智能体系统的提示词管理模块

这个模块提供了统一的提示词字符串管理，按graph分类：
- main_graph_prompts: 主服务图的提示词
- business_recommend_prompts: 业务推荐图的提示词  
- question_recommend_prompts: 问题推荐图的提示词

使用方式：
from agents.airport_service.prompts import main_graph_prompts
prompt_text = main_graph_prompts.AIRPORT_KNOWLEDGE_SYSTEM_PROMPT
"""

from . import main_graph_prompts
from . import business_recommend_prompts  
from . import question_recommend_prompts
from . import query_transform_prompts

__all__ = [
    'main_graph_prompts',
    'business_recommend_prompts',
    'question_recommend_prompts',
    'query_transform_prompts'
] 