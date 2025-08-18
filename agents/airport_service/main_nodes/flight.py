"""
航班信息节点
"""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from agents.airport_service.state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from agents.airport_service.tools import flight_info_query
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage,RemoveMessage
from agents.airport_service.core import filter_messages_for_agent, max_msg_len,base_model,extract_flight_numbers_from_result
from agents.airport_service.context_engineering.prompts import main_graph_prompts
from langgraph.store.base import BaseStore
from langgraph.config import get_store
from datetime import datetime
from langgraph.config import get_stream_writer
from common.logging import get_logger
# 获取航班信息节点专用日志记录器
logger = get_logger("agents.main-nodes.flight")
flight_tool_node = ToolNode([flight_info_query])

def send_flight_info_to_user(sql_result,nb):
    flights = []
    send_flight_info = []
    tmp = {}
    try:
        flights = extract_flight_numbers_from_result(sql_result)
    except Exception as e:
        flights = []
    if len(flights) > 0:
        for flight in flights:
            tmp.clear()
            tmp["flight_number"] = flight
            tmp["subscribe_supported"] = True
            send_flight_info.append(tmp.copy())
        else:
            subscribe_data = {
                "type": "flight_list",
                "data": send_flight_info[:nb],
                "title": "相关航班号信息",
                "action_hint": "您本次对话涉及到如下航班，可点击进行订阅，便于后续航班信息推送给您"
            }
            writer = get_stream_writer()
            writer({"node_name":"flight_assistant_node","data":subscribe_data})




async def provide_flight_info(state: AirportMainServiceState, config: RunnableConfig):
    """
    提供航班信息的节点函数

    Args:
        state: 当前状态对象
        config: 可运行配置

    Returns:
        更新后的状态对象，包含航班信息
    """
    logger.info("进入航班信息问答子智能体:")
    kb_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.FLIGHT_INFO_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
        ("human", main_graph_prompts.FLIGHT_INFO_HUMAN_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    context_docs = state.get("db_context_docs", "")
    # 获取消息历史
    new_messages = filter_messages_for_agent(state, max_msg_len, "航班信息问答子智能体")
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    # 处理不同格式的sql_result
    sql_result = context_docs.get("data", "")
    sql_query = context_docs.get("sql", "")

    # 数据有效，调用LLM进行处理
    kb_chain = kb_prompt | base_model
    res = await kb_chain.ainvoke({ 
        "user_query": user_query,
        "sql": sql_query,
        "sql_result": sql_result,
        "messages": messages
    })
    res.name = "航班信息问答子智能体"

    send_flight_info_to_user(sql_result,5)
    
    # 提取用户画像
    # profile_executor.submit({"messages":state["messages"]+[res]},after_seconds=memery_delay)
    # episode_executor.submit({"messages":state["messages"]+[res]},after_seconds=memery_delay)

    return {"messages":[res]}
