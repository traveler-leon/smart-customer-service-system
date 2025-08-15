"""
共享的工具函数
避免循环导入问题
"""
from typing import Dict, List
import re
import json
from config.utils import config_manager

# 从配置文件获取模型配置
model_config = config_manager.get_agents_config().get("llm", {})
max_msg_len = model_config.get("max_history_turns", 20)
max_tokens = model_config.get("max_tokens", 10000)
memery_delay = 60*30

# 获取text2kb配置
_text2kb_config = config_manager.get_text2kb_config()
KB_SIMILARITY_THRESHOLD = float(_text2kb_config.get("kb_similarity_threshold"))

# 获取情感分析配置
emotion = config_manager.get_agents_config().get("emotions","tabularisai/multilingual-sentiment-analysis")

def filter_messages_for_agent(state: Dict, nb_messages: int = 10,agent_role: str = "user") -> List:
    from langchain_core.messages import HumanMessage, AIMessage
    messages = state.get("messages", [])
    filtered_messages = []
    if agent_role == "主路由智能体":
        for msg in messages[::-1]:
            if len(filtered_messages) <= nb_messages:
                if isinstance(msg, HumanMessage):
                    filtered_messages.insert(0,msg)
                elif isinstance(msg, AIMessage) and msg.name == agent_role:
                    filtered_messages.insert(0,AIMessage(content=str(msg.additional_kwargs['tool_calls'][0]["function"]), name=msg.name)) 
            else:
                break
    else:
        for msg in messages[::-1]:
            if len(filtered_messages) <= nb_messages:
                if isinstance(msg, HumanMessage):
                    filtered_messages.insert(0,msg)
                elif isinstance(msg, AIMessage) and msg.name == agent_role:
                    filtered_messages.insert(0,msg) 
    return filtered_messages


def filter_messages_for_llm(state: Dict, nb_messages: int = 10) -> List:
    """
    专门用于LLM调用的消息过滤函数
    移除所有ToolMessage和有tool_calls的消息，只保留Human和AI的对话消息
    """
    from langchain_core.messages import HumanMessage, AIMessage
    messages = state.get("messages", [])
    filtered_messages = []
    for idx,msg in enumerate(messages[::-1]):
        if idx < nb_messages:
            if isinstance(msg, HumanMessage) and idx != 0:
                filtered_messages.append(msg)
            elif isinstance(msg, AIMessage) and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                filtered_messages.append(msg)
    return filtered_messages 




def extract_flight_numbers_from_result(sql_result):
    pattern = re.compile(r'\b[A-Z]{2}\d{3,4}\b')
    flight_numbers = set()
    for row in sql_result:
        for value in row.values():
            if isinstance(value, str):
                matches = pattern.findall(value.upper())
                flight_numbers.update(matches)
    return list(flight_numbers)
