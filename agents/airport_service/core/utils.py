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



def filter_messages_for_agent(state: Dict, turn_count: int = 5, agent_role: str = "user") -> List:
    """
    根据对话轮次和智能体角色筛选消息
    
    逻辑说明：
    - 根据AI消息的name属性筛选特定agent的对话内容
    - 检测AI消息是否有tool_calls参数
    - 根据智能体类型确定用户消息位置：
      * 主路由智能体：用户消息在AI消息前一位
      * 其他智能体：用户消息在AI消息前三位
    - 如果没有tool_calls，取该消息 + 对应位置的用户消息
    - 如果有tool_calls，除了取用户消息，还要取AI消息后一位的工具消息
    - 消息格式：[query, ai_router_msg, tool_msg, agent1_msg, query, ai_router_msg, tool_msg, agent2_msg, ...]
    
    Args:
        state: 包含消息列表的状态字典
        turn_count: 要提取的对话轮次数量
        agent_role: 智能体角色名称，用于匹配AI消息的name属性。如果为"user"则不进行筛选
    
    Returns:
        筛选后的消息列表
    """
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    
    messages = state.get("messages", [])
    if not messages:
        return []
    
    filtered_messages = []
    turn_collected = 0
    
    # 从后往前遍历消息，查找AI消息
    for i in range(len(messages) - 1, -1, -1):
        if turn_collected >= turn_count:
            break
            
        msg = messages[i]
        
        # 只处理AI消息，并且检查agent名称是否匹配
        if isinstance(msg, AIMessage):
            # 检查AI消息的name属性是否匹配指定的agent_role
            msg_agent_name = getattr(msg, 'name', None)
            if msg_agent_name != agent_role:
                continue
                
            # 根据智能体类型确定用户消息的位置
            if agent_role == "主路由智能体":
                user_msg_step = 1  # 主路由智能体的用户消息在前面一位
            else:
                user_msg_step = 2  # 其他智能体的用户消息在前面三位
                
            current_turn_messages = []
            
            # 检查AI消息是否有tool_calls
            has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
            
            # 按时间顺序收集消息：用户消息 -> AI消息 -> 工具消息
            if has_tool_calls:
                # 有tool_calls的情况
                # 1. 添加用户消息（如果存在）
                if i - user_msg_step >= 0 and isinstance(messages[i - user_msg_step], HumanMessage):
                    current_turn_messages.append(messages[i - user_msg_step])
                
                # 2. 添加AI消息本身
                current_turn_messages.append(msg)
                
                # 3. 添加AI消息后一位的工具消息（如果存在）
                if i + 1 < len(messages) and isinstance(messages[i + 1], ToolMessage):
                    current_turn_messages.append(messages[i + 1])
            else:
                # 没有tool_calls的情况
                # 1. 添加用户消息（如果存在）
                if i - user_msg_step >= 0 and isinstance(messages[i - user_msg_step], HumanMessage):
                    current_turn_messages.append(messages[i - user_msg_step])
                
                # 2. 添加AI消息本身
                current_turn_messages.append(msg)
            
            # 如果成功收集到消息，则添加到结果中并增加轮次计数
            if current_turn_messages:
                # 将当前轮次的消息添加到结果列表的开头，保持最新的在前面
                filtered_messages = current_turn_messages + filtered_messages
                turn_collected += 1
    
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




