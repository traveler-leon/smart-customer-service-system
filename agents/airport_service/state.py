"""
状态定义模块
"""

from typing import Dict, List, TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState

def dict_merge(old_dict, new_dict):
    """合并字典，处理状态更新"""
    if not old_dict:
        return new_dict
    if not new_dict:
        return old_dict
    return {**old_dict, **new_dict}

class AirportMainServiceState(MessagesState):
    """机场客服系统状态定义"""
    # 用户信息
    user_base_info: Annotated[Dict, dict_merge] = {}
    user_profile_info: Annotated[Dict, dict_merge] = {}
    # 当前查询
    current_query: Optional[str] = None
    # 上下文信息
    kb_context_docs: str = ""
    db_context_docs: Dict = {}
    chart_config: Dict = {}