"""
业务办理模块的状态定义
"""

from typing import Annotated, Dict, List, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class BusinessServiceState(TypedDict):
    """业务办理模块的状态"""
    # 消息历史
    messages: Annotated[List, add_messages]
    
    # 业务类型识别
    business_type: str  # 识别的业务类型
    business_params: Dict[str, Any]  # 业务参数
    
    # 参数收集
    params_complete: bool  # 参数是否完整
    missing_params: List[str]  # 缺失的参数
    
    # 确认相关
    needs_confirmation: bool  # 是否需要确认
    confirmed: bool  # 是否已确认
    
    # API调用相关
    api_response: Dict[str, Any]  # API响应
    api_success: bool  # API调用是否成功
    
    # 错误处理
    error_message: Optional[str]  # 错误信息
    alternative_options: List[str]  # 替代选项
    
    # 结果
    formatted_result: str  # 格式化的结果
    final_response: str  # 最终回复 