"""
闲聊节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from agents.airport_service.state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from datetime import datetime
from agents.airport_service.core import filter_messages_for_agent, max_msg_len,base_model
from agents.airport_service.context_engineering.prompts import main_graph_prompts
from agents.airport_service.context_engineering.agent_memory import memory_enabled_agent
from common.logging import get_logger

logger = get_logger("agents.main-nodes.chitchat")

@memory_enabled_agent(application_id="机场主智能客服")
async def chitchat_agent(state: AirportMainServiceState, config: RunnableConfig):
    """
    处理闲聊问题的节点函数

    Args:
        state: 当前状态对象
        config: 可运行配置

    Returns:
        更新后的状态对象，包含闲聊回复
    """
    logger.info("机场知识问答2号子智能体:")
    
    # 获取用户信息
    user_id = config["configurable"].get("user_id", "unknown_user")
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    
    # 准备上下文信息
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"
    

    chitchat_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.CHITCHAT_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
        ("human", "{user_query}")
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    chain = chitchat_prompt | base_model
    
    # 获取消息历史
    new_messages = filter_messages_for_agent(state, max_msg_len, "机场知识问答2号子智能体")

    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    
    res = await chain.ainvoke({"messages": messages,"user_query":user_query,"language":language})
    # response = AIMessage(content="抱歉您的问题我暂时无法回答，请你拨打客服电话进行咨询。14634563456")
    res.name = "机场知识问答2号子智能体"
    
    return {"messages": [res]}