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
from agents.airport_service.tools import flight_info_query2docs,get_text2sql_instance
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage
from agents.airport_service.core import filter_messages_for_agent, max_msg_len,base_model,extract_flight_numbers_from_result
from agents.airport_service.context_engineering.prompts import main_graph_prompts
from agents.airport_service.context_engineering.agent_memory import memory_enabled_agent
from datetime import datetime
from langgraph.config import get_stream_writer
from common.logging import get_logger
# 获取航班信息节点专用日志记录器
logger = get_logger("agents.main-nodes.flight")

def extract_airline_code_from_flight_number(flight_number: str) -> str:
    if not flight_number or len(flight_number) < 2:
        return ""
    airline_code = flight_number[:2].upper()
    return airline_code
    

async def build_and_run_flight_sql_query(flights: list[str]) -> str:
    flight_str = ",".join(f"'{f}'" for f in flights)
    sql = f"""
    SELECT *
    FROM flight_dynamic_information
    WHERE flight_number IN ({flight_str});
    """
    smart_sql = await get_text2sql_instance()
    result = await smart_sql.run_sql(sql.strip())
    
    return result

async def build_and_run_logo_query(airline_codes: list[str]) -> dict:
    if not airline_codes:
        return {}
    
    # 去重并过滤空值
    unique_codes = list(set(code.upper() for code in airline_codes if code))
    if not unique_codes:
        return {}
    
    code_str = ",".join(f"'{code}'" for code in unique_codes)
    sql = f"""
    SELECT airline_code, logo_data_uri
    FROM airline_logos
    WHERE airline_code IN ({code_str});
    """
    
    try:
        smart_sql = await get_text2sql_instance()
        result = await smart_sql.run_sql(sql.strip())
        
        # 将结果转换为字典格式
        logo_dict = {}
        if isinstance(result, list):
            for row in result:
                if isinstance(row, dict) and 'airline_code' in row and 'logo_data_uri' in row:
                    logo_dict[row['airline_code']] = row['logo_data_uri']
        
        return logo_dict
    except Exception as e:
        logger.error(f"查询logo数据时发生错误: {e}")
        return {}


async def send_flight_info_to_user(sql_result,nb):
    flights = []
    send_flight_info = []
    tmp = {}
    try:
        flights = extract_flight_numbers_from_result(sql_result)
        flights_msg = await build_and_run_flight_sql_query(flights)
    except Exception as e:
        sql_result = []
        flights_msg = []
    
    if len(flights_msg) > 0:
        # 提取所有航班的航空公司代码
        airline_codes = []
        for flight in flights_msg:
            if isinstance(flight, dict) and 'flight_number' in flight:
                airline_code = extract_airline_code_from_flight_number(flight['flight_number'])
                if airline_code:
                    airline_codes.append(airline_code)
        
        # 查询logo数据
        logo_data = await build_and_run_logo_query(airline_codes)
        
        # 处理每个航班信息，添加logo数据
        for flight in flights_msg:
            tmp.clear()
            if isinstance(flight, str):
                continue
            tmp = flight.copy() 
            tmp["subscribe_supported"] = True
            
            # 添加logo数据
            if 'flight_number' in tmp:
                airline_code = extract_airline_code_from_flight_number(tmp['flight_number'])
                if airline_code and airline_code in logo_data:
                    tmp["airline_logo"] = logo_data[airline_code]
                else:
                    # 如果没有找到logo，设置为None或空字符串
                    tmp["airline_logo"] = None
            
            send_flight_info.append(tmp.copy())
        else:
            subscribe_data = {
                "type": "flight_list",
                "data": send_flight_info,
                "title": "相关航班号信息",
                "action_hint": "您本次对话涉及到如下航班，可点击进行订阅，便于后续航班信息推送给您"
            }
            writer = get_stream_writer()
            writer({"node_name":"flight_assistant_node","data":subscribe_data})



@memory_enabled_agent(application_id="机场主智能客服")
async def flight_info_agent(state: AirportMainServiceState, config: RunnableConfig):
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
        ("human", main_graph_prompts.FLIGHT_INFO_HUMAN_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    context_docs = state.get("db_context_docs", {})
    # 获取消息历史
    new_messages = filter_messages_for_agent(state, max_msg_len, "航班信息问答子智能体")
    logger.info(f"航班信息问答子智能体隔离后的消息:---------")
    logger.info(f"{new_messages}")
    logger.info(f"航班信息问答子智能体隔离后的消息:---------")

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
    await send_flight_info_to_user(sql_result,5)

    return {"messages":[res],"db_context_docs":None}


async def flight_info_search(state: AirportMainServiceState, config: RunnableConfig):
    messages = filter_messages_for_agent(state, max_msg_len, "航班信息问答子智能体")
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    docs = await flight_info_query2docs(user_query, messages)
    return {"db_context_docs":docs["db_context_docs"]}

