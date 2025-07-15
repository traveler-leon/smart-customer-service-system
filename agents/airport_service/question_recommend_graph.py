"""
客服主图构建模块
"""
from langgraph.graph import StateGraph, START, END
from .state import QuestionRecommendState
from .problems_recommend_nodes import translator, artificial,images_thinking,question_recommend
from langgraph.pregel import RetryPolicy

def build_question_recommend_graph():
    """
    构建机场客服系统图，但不编译
    
    Returns:
        未编译的图对象
    """
    # 创建图
    graph = StateGraph(QuestionRecommendState)
    # 翻译节点
    graph.add_node("translate_input_node", translator.translate_input, retry=RetryPolicy(max_attempts=3))
    graph.add_node("translate_output_node", translator.translate_output, retry=RetryPolicy(max_attempts=3))
    # 情感识别节点
    graph.add_node("emotion_node", artificial.detect_emotion, retry=RetryPolicy(max_attempts=3))
    graph.add_node("images_thinking_node", images_thinking.images_thinking, retry=RetryPolicy(max_attempts=3))
    # 核心处理节点
    graph.add_node("question_recommend_node", question_recommend.provide_question_recommend, retry=RetryPolicy(max_attempts=5))
    # 添加边 - 首先进行输入翻译
    graph.add_edge(START, "translate_input_node")
    graph.add_edge("translate_input_node", "emotion_node")
    graph.add_edge("emotion_node", "images_thinking_node")
    # 从输入翻译到路由
    graph.add_edge("images_thinking_node", "question_recommend_node")
    graph.add_edge("question_recommend_node", "translate_output_node")
    graph.add_edge("translate_output_node", END)

    # 返回未编译的图对象
    return graph


# if __name__ == "__main__":
#     graph = build_question_recommend_graph()
#     graph_image = graph.compile().get_graph(xray=True).draw_mermaid_png()
#     with open("question_recommend_graph.png", "wb") as f:
#         f.write(graph_image)
