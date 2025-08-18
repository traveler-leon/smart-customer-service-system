"""
闲聊节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
import httpx
from agents.airport_service.state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langgraph.prebuilt import ToolNode
from langgraph.config import get_store
from langgraph.store.base import BaseStore
from langgraph.types import Command
from datetime import datetime
from agents.airport_service.tools import chitchat_query
from agents.airport_service.core import filter_messages_for_agent, max_msg_len,base_model
from agents.airport_service.context_engineering.prompts import main_graph_prompts
from agents.airport_service.context_engineering.agent_memory import memory_enabled_agent, AgentMemoryMixin
from common.logging import get_logger

logger = get_logger("agents.main-nodes.chitchat")
chitchat_tool_node = ToolNode([chitchat_query])

async def handle_chitchat(state: AirportMainServiceState, config: RunnableConfig):
    """
    处理闲聊问题的节点函数

    Args:
        state: 当前状态对象
        config: 可运行配置

    Returns:
        更新后的状态对象，包含闲聊回复
    """
    logger.info("进入闲聊子智能体:")
    
    # 获取用户信息
    user_id = config["configurable"].get("user_id", "unknown_user")
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    
    # 使用记忆增强prompt
    base_prompt = main_graph_prompts.CHITCHAT_SYSTEM_PROMPT
    
    # 准备上下文信息
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"
    

    chitchat_prompt = ChatPromptTemplate.from_messages([
        ("system", base_prompt),
        ("placeholder", "{messages}"),
        ("human", "{user_query}")
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    chain = chitchat_prompt | base_model
    
    # 获取消息历史
    new_messages = filter_messages_for_agent(state, max_msg_len, "闲聊子智能体")
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    
    response = await chain.ainvoke({"messages": messages,"user_query":user_query,"language":language})
    response.name = "闲聊子智能体"
    
    return Command(
        update={"messages": [response]},
        goto="translate_output_node"
    )