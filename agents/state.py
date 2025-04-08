"""
机场智能客服系统的状态定义
"""

from typing import Annotated, Dict, List, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AirportServiceState(TypedDict):
    """机场客服系统的主状态"""
    # 消息历史
    messages: Annotated[List, add_messages]
    # 当前意图
    intent: str
    # 查询结果
    results: Dict[str, Any]
    # 是否需要数据库查询
    needs_db_query: bool
    # 是否需要API调用
    needs_api_call: bool
    # 是否需要人工干预
    needs_human: bool
    # 会话上下文
    context: Dict[str, Any]
    # 用户ID
    user_id: Optional[str]
    # 当前模块
    current_module: str 