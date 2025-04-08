"""
航班信息查询模块的状态定义
"""

from typing import Annotated, Dict, List, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class FlightInfoState(TypedDict):
    """航班信息查询模块的状态"""
    # 消息历史
    messages: Annotated[List, add_messages]
    
    # 航班参数相关状态
    flight_params: Dict[str, Any]  # 提取的航班查询参数
    params_complete: bool  # 参数是否完整
    missing_params: List[str]  # 缺失的参数
    
    # 数据库查询相关状态
    sql_query: str  # 生成的SQL查询
    query_results: List[Dict]  # 查询结果
    query_success: bool  # 查询是否成功
    
    # 错误处理状态
    error_message: Optional[str]  # 错误信息
    retry_count: int  # 重试次数
    
    # 结果格式化相关状态
    formatted_result: str  # 格式化后的结果
    simplified_result: bool  # 是否已简化
    
    # 最终回复
    final_response: str  # 最终回复 