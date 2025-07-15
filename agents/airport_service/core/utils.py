"""
共享的工具函数
避免循环导入问题
"""
from typing import Dict, List
import re
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

def filter_messages(state: Dict, nb_messages: int = 10) -> List:
    """
    过滤消息列表，返回适合处理的格式
    确保不会破坏tool消息与tool_calls的对应关系
    """
    from langchain_core.messages import ToolMessage
    messages = state.get("messages", [])
    
    if len(messages) <= nb_messages:
        return {**state, "messages": messages}
    start_index = len(messages) - nb_messages
    for i in range(start_index, len(messages)):
        current_msg = messages[i]
        if isinstance(current_msg, ToolMessage):
            has_tool_calls = False
            for j in range(i-1, -1, -1):
                prev_msg = messages[j]
                if hasattr(prev_msg, 'tool_calls') and prev_msg.tool_calls:
                    for tool_call in prev_msg.tool_calls:
                        if tool_call.get('id') == getattr(current_msg, 'tool_call_id', None):
                            has_tool_calls = True
                            break
                    if has_tool_calls:
                        break
                if isinstance(prev_msg, ToolMessage) or (i - j) > 5:
                    break
            if not has_tool_calls:
                continue
        start_index = i
        break
    if start_index >= len(messages):
        start_index = max(0, len(messages) - 3)
    filtered_messages = messages[start_index:]
    return filtered_messages

def filter_messages_for_llm(state: Dict, nb_messages: int = 10) -> List:
    """
    专门用于LLM调用的消息过滤函数
    移除所有ToolMessage和有tool_calls的消息，只保留Human和AI的对话消息
    """
    from langchain_core.messages import ToolMessage, HumanMessage, AIMessage
    messages = state.get("messages", [])
    filtered_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            filtered_messages.append(msg)
        elif isinstance(msg, AIMessage) and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
            filtered_messages.append(msg)
    if len(filtered_messages) > nb_messages:
        filtered_messages = filtered_messages[-nb_messages:]
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
