"""
路由节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from agents.airport_service.state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from langgraph.store.base import BaseStore
from agents.airport_service.tools import airport_knowledge_query, flight_info_query,business_handler
from agents.airport_service.core import filter_messages_for_agent, max_msg_len,structed_model
from agents.airport_service.prompts import main_graph_prompts
from langgraph.config import get_store
from langchain_core.messages import AIMessage
from common.logging import get_logger
import asyncio

# 获取路由节点专用日志记录器
logger = get_logger("agents.nodes.router")
tool_model = structed_model.bind_tools([airport_knowledge_query, flight_info_query,business_handler])

async def identify_intent(state: AirportMainServiceState, config: RunnableConfig):
    
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    logger.info(f"进入主路由子智能体：{user_query}")
    airport_assistant_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.ROUTER_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
        ("human", "{user_query}")
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    chain = airport_assistant_prompt | tool_model
    new_messages = filter_messages_for_agent(state, max_msg_len, "主路由智能体")
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    # 调用链获取响应
    response = await chain.ainvoke({"messages": messages, "user_query": user_query})
    response.name = "主路由智能体"
    
    # 返回更新后的状态
    return {"messages": [response],"user_query":user_query}


def route_to_next_node(state: AirportMainServiceState):
    # 获取最新消息
    messages = state.get("messages", [])
    if not messages:
        return "airport_tool_node"

    latest_message = messages[-1]
    # 检查是否有工具调用
    if not hasattr(latest_message, "tool_calls") or not latest_message.tool_calls:
        return "airport_tool_node"

    # 根据工具调用决定下一个节点
    tool_name = latest_message.tool_calls[-1].get("name", "")
    if tool_name == "flight_info_query":
        return "flight_tool_node"
    elif tool_name == "business_handler":
        return "business_tool_node"
    else:
        return "airport_tool_node"