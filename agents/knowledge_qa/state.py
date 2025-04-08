"""
知识问答模块的状态定义
"""

from typing import Annotated, Dict, List, Optional, Any, Union, float
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class KnowledgeQAState(TypedDict):
    """知识问答模块的状态"""
    # 消息历史
    messages: Annotated[List, add_messages]
    
    # 查询分析相关状态
    query_complete: bool  # 查询是否完整
    missing_info: List[str]  # 缺失的信息
    needs_clarification: bool  # 是否需要澄清
    clarification_round: int  # 澄清轮次
    
    # 知识检索相关状态
    context_retrieved: List[Dict]  # 检索到的上下文
    relevance_score: float  # 相关性分数
    
    # 粒度匹配相关状态
    granularity_match: bool  # 粒度是否匹配
    sub_categories: List[str]  # 子类别
    refinement_question: str  # 细化问题
    
    # 回答生成相关状态
    current_answer: str  # 当前生成的回答
    needs_simplification: bool  # 是否需要简化
    simplified_answer: bool  # 是否已简化
    response_style: str  # 回答风格
    
    # 结果状态
    final_response: str  # 最终回答 