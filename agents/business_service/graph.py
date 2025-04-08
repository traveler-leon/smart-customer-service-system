"""
业务办理模块的图构建
"""

from langgraph.graph import StateGraph
from agents.business_service.state import BusinessServiceState
from agents.business_service.nodes import (
    identify_business_type,
    request_business_confirmation,
    collect_business_params,
    request_missing_params,
    confirm_business_operation,
    process_confirmation_response,
    call_business_api,
    handle_business_error,
    format_business_result
)


def build_business_service_graph():
    """构建业务办理模块的图"""
    
    # 创建业务办理模块图
    business_service_graph_builder = StateGraph(BusinessServiceState)
    
    # 添加节点
    business_service_graph_builder.add_node("identify_business_type", identify_business_type)
    business_service_graph_builder.add_node("request_business_confirmation", request_business_confirmation)
    business_service_graph_builder.add_node("collect_business_params", collect_business_params)
    business_service_graph_builder.add_node("request_missing_params", request_missing_params)
    business_service_graph_builder.add_node("confirm_business_operation", confirm_business_operation)
    business_service_graph_builder.add_node("process_confirmation_response", process_confirmation_response)
    business_service_graph_builder.add_node("call_business_api", call_business_api)
    business_service_graph_builder.add_node("handle_business_error", handle_business_error)
    business_service_graph_builder.add_node("format_business_result", format_business_result)
    
    # 设置入口节点
    business_service_graph_builder.set_entry_point("identify_business_type")
    
    # 添加条件边
    # 1. 从业务类型识别节点开始
    business_service_graph_builder.add_conditional_edges(
        "identify_business_type",
        lambda x: "request_business_confirmation" if x.get("needs_confirmation", False) else "collect_business_params"
    )
    
    # 2. 业务类型确认后
    business_service_graph_builder.add_conditional_edges(
        "request_business_confirmation",
        lambda x: None  # 等待用户响应后重新进入identify_business_type
    )
    
    # 3. 收集业务参数后
    business_service_graph_builder.add_conditional_edges(
        "collect_business_params",
        lambda x: "request_missing_params" if not x.get("params_complete", False) else "confirm_business_operation"
    )
    
    # 4. 请求缺失参数后
    business_service_graph_builder.add_conditional_edges(
        "request_missing_params",
        lambda x: None  # 等待用户响应后重新进入collect_business_params
    )
    
    # 5. 确认业务操作后
    business_service_graph_builder.add_conditional_edges(
        "confirm_business_operation",
        lambda x: "process_confirmation_response"
    )
    
    # 6. 处理确认响应后
    business_service_graph_builder.add_conditional_edges(
        "process_confirmation_response",
        lambda x: "call_business_api" if x.get("confirmed", False) else None
    )
    
    # 7. 调用业务API后
    business_service_graph_builder.add_conditional_edges(
        "call_business_api",
        lambda x: "handle_business_error" if not x.get("api_success", False) else "format_business_result"
    )
    
    # 8. 处理错误后
    business_service_graph_builder.add_conditional_edges(
        "handle_business_error",
        lambda x: "collect_business_params" if not x.get("params_complete", True) else None
    )
    
    # 9. 格式化结果后
    business_service_graph_builder.add_conditional_edges(
        "format_business_result",
        lambda x: None
    )
    
    # 编译业务办理图
    return business_service_graph_builder.compile()


# 创建默认业务办理图实例
business_service_graph = build_business_service_graph() 