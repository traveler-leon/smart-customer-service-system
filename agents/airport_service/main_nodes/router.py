"""
路由节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from agents.airport_service.state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from agents.airport_service.context_engineering.agent_memory import memory_enabled_agent
from langchain_core.prompts import ChatPromptTemplate
from agents.airport_service.core import filter_messages_for_llm,filter_messages_for_agent, max_msg_len,structed_model
from agents.airport_service.context_engineering.prompts import main_graph_prompts
from common.logging import get_logger
import asyncio
from pydantic import BaseModel, Field
from typing import Literal

# 获取路由节点专用日志记录器
logger = get_logger("agents.nodes.router")


class Route(BaseModel):
    step: Literal["flight_query", "business_service", "airport_info"]=Field(
        None,
        description=(
            "用于标识用户在当前对话中的主要意图分类。\n\n"
            "- flight_query：用户希望获取航班动态，例如航班号对应的起降时间、登机口信息、延误或取消情况。\n"
            "- business_service：用户需要办理或咨询机场范围内的服务，例如爱心服务、轮椅租赁、无人陪伴服务等。"
            "- airport_info：用户想要了解机场设施、交通换乘、安检规定、候机服务等常见问题。"
        )
    )

router_model = structed_model.with_structured_output(Route)

@memory_enabled_agent(application_id="机场主智能客服")
async def identify_intent(state: AirportMainServiceState, config: RunnableConfig):
    metadata = config["configurable"].get("metadata", {})
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    logger.info(f"进入主路由子智能体：{user_query}")
    router_assistant_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.ROUTER_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
        ("human", main_graph_prompts.ROUTER_HUMAN_PROMPT)
    ])

    chain = router_assistant_prompt | router_model
    messages = filter_messages_for_llm(state, max_msg_len)
    try:
        res = await chain.ainvoke({"messages": messages, "user_query": user_query})
        return {"messages":[AIMessage(content=res.step,name="主路由智能体")],"router": res.step,"user_query":user_query,"metadata":metadata}
    except Exception as e:
        logger.error(f"主路由子智能体执行失败: {e}")
        return {"messages":[AIMessage(content="用户意图识别失败",name="主路由智能体")],"router": "用户意图识别失败","user_query":user_query,"metadata":metadata}


def route_to_next_node(state: AirportMainServiceState):
    # 根据意图分类决定下一个节点
    intent_category = state.get("router", "")
    if intent_category == "flight_query":
        return "flight_info_search_node"
    elif intent_category == "business_service":
        return "business_assistant_node"
    elif intent_category == "airport_info":
        return "airport_info_search_node"
    else:
        # 默认路由到机场知识查询
        return "airport_info_search_node"