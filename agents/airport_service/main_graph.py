"""
客服主图构建模块
"""
from langgraph.graph import StateGraph, START, END
from .state import AirportMainServiceState
from .nodes import router, flight, airport
from langgraph.pregel import RetryPolicy

def build_airport_service_graph():
    """
    构建机场客服系统图，但不编译
    
    Returns:
        未编译的图对象
    """
    # 创建图
    graph = StateGraph(AirportMainServiceState)
    
    # 添加节点
    graph.add_node("router", router.identify_intent,retry=RetryPolicy(max_attempts=5))
    graph.add_node("flight_tool_node", flight.flight_tool_node,retry=RetryPolicy(max_attempts=5))
    graph.add_node("flight_assistant_node", flight.provide_flight_info,retry=RetryPolicy(max_attempts=5))
    graph.add_node("airport_tool_node", airport.airport_tool_node,retry=RetryPolicy(max_attempts=5))
    graph.add_node("airport_assistant_node", airport.provide_airport_knowledge,retry=RetryPolicy(max_attempts=5))
    
    # 添加边
    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        router.route_to_next_node,
        {
            "flight_tool_node": "flight_tool_node",
            "airport_tool_node": "airport_tool_node",
            "end": "__end__"
        }
    )
    graph.add_edge("airport_tool_node", "airport_assistant_node")
    graph.add_edge("airport_assistant_node", END)
    graph.add_edge("flight_tool_node", "flight_assistant_node")
    graph.add_edge("flight_assistant_node", END)
    
    # 返回未编译的图对象
    return graph
