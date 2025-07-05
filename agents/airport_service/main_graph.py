"""
客服主图构建模块
"""
from langgraph.graph import StateGraph, START, END
from .state import AirportMainServiceState
from .nodes import airport, router, flight, chitchat, translator, artificial, business,images_thinking
from langgraph.pregel import RetryPolicy

def build_airport_service_graph():
    """
    构建机场客服系统图，但不编译
    
    Returns:
        未编译的图对象
    """
    # 创建图
    graph = StateGraph(AirportMainServiceState)
    # 翻译节点
    graph.add_node("translate_input_node", translator.translate_input, retry=RetryPolicy(max_attempts=3))
    graph.add_node("translate_output_node", translator.translate_output, retry=RetryPolicy(max_attempts=3))
    # 情感识别节点
    graph.add_node("emotion_node", artificial.detect_emotion, retry=RetryPolicy(max_attempts=3))
    graph.add_node("images_thinking_node", images_thinking.images_thinking, retry=RetryPolicy(max_attempts=3))
    
    # 核心处理节点
    graph.add_node("router", router.identify_intent, retry=RetryPolicy(max_attempts=5))
    graph.add_node("flight_tool_node", flight.flight_tool_node, retry=RetryPolicy(max_attempts=5))
    graph.add_node("flight_assistant_node", flight.provide_flight_info, retry=RetryPolicy(max_attempts=5))
    graph.add_node("airport_tool_node", airport.airport_tool_node, retry=RetryPolicy(max_attempts=5))
    graph.add_node("airport_assistant_node", airport.provide_airport_knowledge, retry=RetryPolicy(max_attempts=5))
    # graph.add_node("chitchat_tool_node", chitchat.chitchat_tool_node, retry=RetryPolicy(max_attempts=5))
    graph.add_node("chitchat_node", chitchat.handle_chitchat, retry=RetryPolicy(max_attempts=5))
    graph.add_node("business_tool_node", business.router_bussiness_tools, retry=RetryPolicy(max_attempts=5))
    graph.add_node("business_assistant_node", business.business_agent, retry=RetryPolicy(max_attempts=5))
    
    # 添加边 - 首先进行输入翻译
    graph.add_edge(START, "emotion_node")
    graph.add_edge("emotion_node", "translate_input_node")
    graph.add_edge("translate_input_node", "images_thinking_node")
    # 从输入翻译到路由
    graph.add_edge("images_thinking_node", "router")
    
    # 路由到具体工具节点
    graph.add_conditional_edges(
        "router",
        router.route_to_next_node,
        {
            "flight_tool_node": "flight_tool_node",
            "airport_tool_node": "airport_tool_node",
            "business_tool_node": "business_tool_node",
            # "chitchat_tool_node": "chitchat_tool_node"
        }
    )
    graph.add_edge("airport_tool_node", "airport_assistant_node")
    graph.add_edge("airport_assistant_node", "translate_output_node")
    graph.add_edge("flight_tool_node", "flight_assistant_node")
    graph.add_edge("flight_assistant_node", "translate_output_node")
    # graph.add_edge("chitchat_tool_node", "chitchat_node")
    graph.add_edge("chitchat_node", "translate_output_node")
    graph.add_edge("business_tool_node", "business_assistant_node")
    graph.add_edge("business_assistant_node", "translate_output_node")
    graph.add_edge("translate_output_node", END)

    # 返回未编译的图对象
    return graph


if __name__ == "__main__":
    graph = build_airport_service_graph()
    graph_image = graph.compile().get_graph(xray=True).draw_mermaid_png()
    with open("main_graph1.png", "wb") as f:
        f.write(graph_image)
