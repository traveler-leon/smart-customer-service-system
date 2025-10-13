import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from datetime import datetime
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, BaseMessage
from agents.airport_service.state import BusinessServiceState
from agents.airport_service.tools.business import wheelchair_rental
from agents.airport_service.core import filter_messages_for_agent, max_msg_len, structed_model
from common.logging import get_logger
from agents.airport_service.context_engineering.prompts import main_graph_prompts
from agents.airport_service.context_engineering.agent_memory import memory_enabled_agent
# 获取业务办理节点专用日志记录器
logger = get_logger("agents.main-nodes.business")

# 业务办理子智能体的工具列表
business_tools = [wheelchair_rental]
business_tool_node = ToolNode(business_tools)

# 将工具绑定到模型
llm_with_tools = structed_model.bind_tools(business_tools)

@memory_enabled_agent(application_id="机场主智能客服")
async def business_chatbot(state: BusinessServiceState, config: RunnableConfig):
    logger.info("进入业务办理聊天机器人节点")
    
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    business_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.BUSINESS_AGENT_PROMPT),
        ("placeholder", "{messages}")
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 过滤消息
    new_messages = filter_messages_for_agent(state, max_msg_len, "业务办理子智能体")
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    
    business_chain = business_prompt | llm_with_tools
    
    response = await business_chain.ainvoke({
        "user_query": user_query,
        "messages": messages
    })
    
    response.name = "业务办理子智能体"
    logger.info(f"业务办理聊天机器人响应: {response.content}")
    
    return {"messages": [response]}


# 创建手动构建的业务办理子智能体图
def create_business_agent():
    """创建业务办理子智能体图"""
    graph_builder = StateGraph(BusinessServiceState)
    graph_builder.add_node("chatbot", business_chatbot)
    graph_builder.add_node("tools", business_tool_node)
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")
    graph = graph_builder.compile()
    logger.info("业务办理子智能体图创建完成")
    return graph

# 创建业务办理子智能体
business_agent = create_business_agent()
