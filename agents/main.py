"""
机场智能客服系统的主程序
"""

from typing import Dict, List, Any, Optional, Annotated
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages

from agents.state import AirportServiceState
from agents.knowledge_qa.graph import knowledge_qa_graph
from agents.flight_info.graph import flight_info_graph 
from agents.business_service.graph import business_service_graph
from agents.utils.llm_utils import default_llm


def classify_intent(state: AirportServiceState):
    """意图分类节点，识别用户意图"""
    messages = state["messages"]
    latest_message = messages[-1]["content"] if isinstance(messages[-1], dict) else messages[-1].content
    
    # 使用LLM识别意图
    system_prompt = """分析用户消息，确定其意图类别。
    可能的意图类别包括:
    - knowledge_qa: 用户询问机场知识、规定、设施等信息
    - flight_info: 用户查询航班信息，如起降时间、状态等
    - business_service: 用户需要办理业务，如值机、改签、退票等
    - other: 其他意图，如打招呼、闲聊等
    
    回复格式:
    {
      "intent": "意图类别",
      "confidence": 0.0-1.0的置信度得分
    }"""
    
    analysis_result = default_llm.invoke(
        [{"role": "user", "content": latest_message}],
        system_prompt=system_prompt,
        output_format="JSON"
    )
    
    # 解析LLM返回的JSON结果
    result = default_llm.parse_json_response(analysis_result, {
        "intent": "other",
        "confidence": 0.0
    })
    
    # 获取意图和置信度
    intent = result.get("intent", "other")
    confidence = result.get("confidence", 0.0)
    
    # 根据置信度判断是否需要人工干预
    needs_human = confidence < 0.3
    
    return {
        "intent": intent,
        "current_module": intent if intent in ["knowledge_qa", "flight_info", "business_service"] else "other",
        "needs_human": needs_human
    }


def handle_general_query(state: AirportServiceState):
    """处理一般性查询"""
    messages = state["messages"]
    latest_message = messages[-1]["content"] if isinstance(messages[-1], dict) else messages[-1].content
    
    # 使用LLM生成回复
    system_prompt = """你是机场智能客服助手。
    请礼貌地回复用户的一般性问题。
    如果用户询问超出你能力范围的问题，可以引导他们尝试更专业的查询方式，
    如询问航班信息、咨询机场规定或办理业务等。"""
    
    response = default_llm.invoke(
        [{"role": "user", "content": latest_message}],
        system_prompt=system_prompt
    )
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": response}],
        "results": {"general_response": response}
    }


def human_handover(state: AirportServiceState):
    """人工客服交接"""
    handover_message = """非常抱歉，您的问题可能需要人工客服进一步处理。
    
    我正在为您转接人工客服，稍后会有专业客服人员与您联系。
    
    您也可以直接拨打客服热线：400-123-4567
    """
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": handover_message}],
        "needs_human": True
    }


class AirportCustomerService:
    """机场智能客服系统"""
    
    def __init__(self):
        """初始化机场智能客服系统"""
        # 构建主图
        graph_builder = StateGraph(AirportServiceState)
        
        # 添加节点
        graph_builder.add_node("classify_intent", classify_intent)
        graph_builder.add_node("knowledge_qa", knowledge_qa_graph)
        graph_builder.add_node("flight_info", flight_info_graph)
        graph_builder.add_node("business_service", business_service_graph)
        graph_builder.add_node("handle_general_query", handle_general_query)
        graph_builder.add_node("human_handover", human_handover)
        
        # 设置入口节点
        graph_builder.add_edge(START, "classify_intent")
        
        # 添加条件边
        graph_builder.add_conditional_edges(
            "classify_intent",
            lambda x: "human_handover" if x.get("needs_human", False) else x.get("current_module", "handle_general_query")
        )
        
        # 设置子图的输出边
        graph_builder.add_edge("knowledge_qa", "classify_intent")
        graph_builder.add_edge("flight_info", "classify_intent")
        graph_builder.add_edge("business_service", "classify_intent")
        
        # 编译图
        self.graph = graph_builder.compile()
        
    def process_message(self, message: str, user_id: Optional[str] = None):
        """处理用户消息
        
        Args:
            message: 用户消息文本
            user_id: 用户ID，用于会话区分
            
        Returns:
            生成的回复
        """
        # 初始化状态
        state = {
            "messages": [{"role": "user", "content": message}],
            "intent": "unknown",
            "results": {},
            "needs_db_query": False,
            "needs_api_call": False,
            "needs_human": False,
            "context": {},
            "user_id": user_id,
            "current_module": "unknown"
        }
        
        # 执行图
        for chunk in self.graph.stream(state):
            pass
        
        # 返回最后一条助手消息
        final_state = chunk.values
        final_messages = final_state.get("messages", [])
        assistant_messages = [m["content"] if isinstance(m, dict) else m.content 
                             for m in final_messages 
                             if (isinstance(m, dict) and m["role"] == "assistant") or 
                                getattr(m, "type", None) == "assistant"]
        
        return assistant_messages[-1] if assistant_messages else "抱歉，我无法回答您的问题。请重新描述您的需求。" 