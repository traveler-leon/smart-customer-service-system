"""
航班信息查询模块的图构建
"""

from langgraph.graph import StateGraph
from agents.flight_info.state import FlightInfoState
from agents.flight_info.nodes import (
    extract_flight_params,
    request_flight_params,
    generate_sql_query,
    execute_database_query,
    handle_query_error,
    format_flight_result,
    simplify_flight_info
)


def build_flight_info_graph():
    """构建航班信息查询模块的图"""
    
    # 创建航班信息查询模块图
    flight_info_graph_builder = StateGraph(FlightInfoState)
    
    # 添加节点
    flight_info_graph_builder.add_node("extract_flight_params", extract_flight_params)
    flight_info_graph_builder.add_node("request_flight_params", request_flight_params)
    flight_info_graph_builder.add_node("generate_sql_query", generate_sql_query)
    flight_info_graph_builder.add_node("execute_database_query", execute_database_query)
    flight_info_graph_builder.add_node("handle_query_error", handle_query_error)
    flight_info_graph_builder.add_node("format_flight_result", format_flight_result)
    flight_info_graph_builder.add_node("simplify_flight_info", simplify_flight_info)
    
    # 设置入口节点
    flight_info_graph_builder.set_entry_point("extract_flight_params")
    
    # 添加条件边
    flight_info_graph_builder.add_conditional_edges(
        "extract_flight_params",
        lambda x: "request_flight_params" if not x.get("params_complete", False) else "generate_sql_query"
    )
    
    flight_info_graph_builder.add_conditional_edges(
        "request_flight_params",
        lambda x: None  # 等待用户响应后重新进入extract_flight_params
    )
    
    flight_info_graph_builder.add_edge("generate_sql_query", "execute_database_query")
    
    flight_info_graph_builder.add_conditional_edges(
        "execute_database_query",
        lambda x: "handle_query_error" if not x.get("query_success", False) else "format_flight_result"
    )
    
    flight_info_graph_builder.add_edge("handle_query_error", "execute_database_query")
    
    flight_info_graph_builder.add_conditional_edges(
        "format_flight_result",
        lambda x: "simplify_flight_info" if len(x.get("formatted_result", "")) > 100 else None
    )
    
    flight_info_graph_builder.add_conditional_edges(
        "simplify_flight_info",
        lambda x: None
    )
    
    # 编译航班信息查询图
    return flight_info_graph_builder.compile()


# 创建默认航班信息查询图实例
flight_info_graph = build_flight_info_graph() 