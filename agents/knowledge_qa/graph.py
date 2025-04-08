"""
知识问答模块的图构建
"""

from langgraph.graph import StateGraph
from agents.knowledge_qa.state import KnowledgeQAState
from agents.knowledge_qa.nodes import (
    query_analysis,
    clarification_node,
    knowledge_retrieval,
    check_granularity,
    request_refinement,
    ask_for_specifics,
    generate_final_answer,
    simplify_answer,
    select_response_style,
    format_with_style
)


def build_knowledge_qa_graph():
    """构建知识问答模块的图"""
    
    # 创建知识问答模块图
    knowledge_qa_graph_builder = StateGraph(KnowledgeQAState)
    
    # 添加节点
    knowledge_qa_graph_builder.add_node("query_analysis", query_analysis)
    knowledge_qa_graph_builder.add_node("clarification_node", clarification_node)
    knowledge_qa_graph_builder.add_node("knowledge_retrieval", knowledge_retrieval)
    knowledge_qa_graph_builder.add_node("check_granularity", check_granularity)
    knowledge_qa_graph_builder.add_node("request_refinement", request_refinement)
    knowledge_qa_graph_builder.add_node("ask_for_specifics", ask_for_specifics)
    knowledge_qa_graph_builder.add_node("generate_final_answer", generate_final_answer)
    knowledge_qa_graph_builder.add_node("simplify_answer", simplify_answer)
    knowledge_qa_graph_builder.add_node("select_response_style", select_response_style)
    knowledge_qa_graph_builder.add_node("format_with_style", format_with_style)
    
    # 设置入口节点
    knowledge_qa_graph_builder.set_entry_point("query_analysis")
    
    # 添加条件边
    knowledge_qa_graph_builder.add_conditional_edges(
        "query_analysis",
        lambda x: "clarification_node" if not x.get("query_complete", False) and x.get("needs_clarification", False) else "knowledge_retrieval"
    )
    
    knowledge_qa_graph_builder.add_conditional_edges(
        "clarification_node",
        lambda x: None  # 等待用户响应后重新进入query_analysis
    )
    
    knowledge_qa_graph_builder.add_conditional_edges(
        "knowledge_retrieval",
        lambda x: "ask_for_specifics" if x.get("relevance_score", 0) < 0.7 else "check_granularity"
    )
    
    knowledge_qa_graph_builder.add_conditional_edges(
        "check_granularity",
        lambda x: "request_refinement" if not x.get("granularity_match", True) else "select_response_style"
    )
    
    knowledge_qa_graph_builder.add_conditional_edges(
        "request_refinement",
        lambda x: None  # 等待用户响应后重新进入query_analysis
    )
    
    knowledge_qa_graph_builder.add_conditional_edges(
        "ask_for_specifics",
        lambda x: None  # 等待用户响应后重新进入query_analysis
    )
    
    knowledge_qa_graph_builder.add_conditional_edges(
        "select_response_style",
        lambda x: "generate_final_answer"
    )
    
    knowledge_qa_graph_builder.add_conditional_edges(
        "generate_final_answer",
        lambda x: "simplify_answer" if x.get("needs_simplification", False) else "format_with_style"
    )
    
    knowledge_qa_graph_builder.add_conditional_edges(
        "simplify_answer",
        lambda x: "format_with_style"
    )
    
    knowledge_qa_graph_builder.add_conditional_edges(
        "format_with_style",
        lambda x: None
    )
    
    # 编译知识问答图
    return knowledge_qa_graph_builder.compile()


# 创建默认知识问答图实例
knowledge_qa_graph = build_knowledge_qa_graph() 