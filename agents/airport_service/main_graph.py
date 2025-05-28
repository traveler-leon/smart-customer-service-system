"""
客服主图构建模块
"""
from langgraph.graph import StateGraph, START, END
from .state import AirportMainServiceState
from .nodes import airport,router, flight, chitchat, translator
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
    # 翻译节点
    graph.add_node("translate_input_node", translator.translate_input, retry=RetryPolicy(max_attempts=3))
    graph.add_node("translate_output_node", translator.translate_output, retry=RetryPolicy(max_attempts=3))
    
    # 核心处理节点
    graph.add_node("router", router.identify_intent, retry=RetryPolicy(max_attempts=5))
    graph.add_node("flight_tool_node", flight.flight_tool_node, retry=RetryPolicy(max_attempts=5))
    graph.add_node("flight_assistant_node", flight.provide_flight_info, retry=RetryPolicy(max_attempts=5))
    graph.add_node("airport_tool_node", airport.airport_tool_node, retry=RetryPolicy(max_attempts=5))
    graph.add_node("airport_assistant_node", airport.provide_airport_knowledge, retry=RetryPolicy(max_attempts=5))
    # graph.add_node("sql2bi_node", flight.sql2bi,retry=RetryPolicy(max_attempts=5))
    # graph.add_node("filter_chatbot_message", flight.filter_chatbot_message,retry=RetryPolicy(max_attempts=5))
    graph.add_node("chitchat_tool_node", chitchat.chitchat_tool_node, retry=RetryPolicy(max_attempts=5))
    graph.add_node("chitchat_node", chitchat.handle_chitchat, retry=RetryPolicy(max_attempts=5))
    
    # 添加边 - 首先进行输入翻译
    graph.add_edge(START, "translate_input_node")
    
    # 从输入翻译到路由
    graph.add_edge("translate_input_node", "router")
    
    # 路由到具体工具节点
    graph.add_conditional_edges(
        "router",
        router.route_to_next_node,
        {
            "flight_tool_node": "flight_tool_node",
            "airport_tool_node": "airport_tool_node",
            "chitchat_tool_node": "chitchat_tool_node"
            # "end": "__end__"
        }
    )
    graph.add_edge("airport_tool_node", "airport_assistant_node")
    graph.add_edge("airport_assistant_node", "translate_output_node")


    graph.add_edge("flight_tool_node", "flight_assistant_node")
    graph.add_edge("flight_assistant_node", "translate_output_node")

    graph.add_edge("chitchat_tool_node", "chitchat_node")
    graph.add_edge("chitchat_node", "translate_output_node")

    graph.add_edge("translate_output_node", END)

    # 返回未编译的图对象
    return graph


# if __name__ == "__main__":
#     graph = build_airport_service_graph()
#     graph_image = graph.compile().get_graph(xray=True).draw_mermaid_png()
#     with open("main_graph.png", "wb") as f:
#         f.write(graph_image)
