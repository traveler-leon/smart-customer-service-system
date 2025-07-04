"""
节点模块

提供机场客服系统的各种节点实现
"""

from langchain_openai import ChatOpenAI
from config.utils import config_manager
from config.factory import get_logger_config
from common.logging import setup_logger, get_logger
from typing import Dict,List
from langmem import create_memory_store_manager,ReflectionExecutor
from agents.airport_service.state import UserProfile,Episode

# 初始化nodes模块日志
logger_config = get_logger_config("agents")
setup_logger(**logger_config)
logger = get_logger("agents.nodes")

# 从配置文件获取模型配置
model_config = config_manager.get_agents_config().get("llm", {})
max_msg_len = model_config.get("max_history_turns", 20)
max_tokens = model_config.get("max_tokens", 10000)
memery_delay = 60*30

emotion = config_manager.get_agents_config().get("emotions")


# 创建共用模型实例
if model_config.get("base_model_type") == "qwen":
    from langchain_qwq import ChatQwen
    base_model = ChatQwen(
        model=model_config.get("model"),
        temperature=model_config.get("temperature", 0.7),
        api_key=model_config.get("api_key"),
        base_url=model_config.get("base_url"),
        enable_thinking=True)
else:
    base_model = ChatOpenAI(
        model=model_config.get("model"),
        temperature=model_config.get("temperature", 0.7),
        api_key=model_config.get("api_key"),
        base_url=model_config.get("base_url")
    )
router_model = ChatOpenAI(
    model=model_config.get("router_model"),
    temperature=model_config.get("router_temperature", 0.7),
    api_key=model_config.get("router_api_key"),
    base_url=model_config.get("router_base_url")
)

# 将 filter_messages 函数移动到这里
def filter_messages(state: Dict, nb_messages: int = 10) -> List:
    """
    过滤消息列表，返回适合处理的格式
    确保不会破坏tool消息与tool_calls的对应关系
    """
    from langchain_core.messages import ToolMessage
    
    messages = state.get("messages", [])
    
    if len(messages) <= nb_messages:
        return {**state, "messages": messages}
    
    # 找到合适的截取位置，避免破坏tool消息链
    start_index = len(messages) - nb_messages
    
    # 从候选起始位置开始，确保不会截断tool消息链
    for i in range(start_index, len(messages)):
        current_msg = messages[i]
        
        # 如果当前消息是ToolMessage，需要检查前面是否有对应的tool_calls
        if isinstance(current_msg, ToolMessage):
            # 查找前面是否有对应的tool_calls消息
            has_tool_calls = False
            for j in range(i-1, -1, -1):
                prev_msg = messages[j]
                if hasattr(prev_msg, 'tool_calls') and prev_msg.tool_calls:
                    # 检查tool_call_id是否匹配
                    for tool_call in prev_msg.tool_calls:
                        if tool_call.get('id') == getattr(current_msg, 'tool_call_id', None):
                            has_tool_calls = True
                            break
                    if has_tool_calls:
                        break
                # 如果遇到另一个ToolMessage或者距离太远，停止查找
                if isinstance(prev_msg, ToolMessage) or (i - j) > 5:
                    break
            
            # 如果没有找到对应的tool_calls，跳过这个ToolMessage
            if not has_tool_calls:
                continue
        
        # 找到合适的起始位置
        start_index = i
        break
    
    # 确保至少保留一些消息
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
    
    # 过滤掉Tool相关的消息，只保留对话消息
    filtered_messages = []
    for msg in messages:
        # 只保留Human和AI消息，并且AI消息不能有tool_calls
        if isinstance(msg, HumanMessage):
            filtered_messages.append(msg)
        elif isinstance(msg, AIMessage) and not (hasattr(msg, 'tool_calls') and msg.tool_calls):
            filtered_messages.append(msg)
    
    # 限制消息数量
    if len(filtered_messages) > nb_messages:
        filtered_messages = filtered_messages[-nb_messages:]
    
    return filtered_messages


# 知识抽取
## 用户画像
profile_manager = create_memory_store_manager(
    base_model,
    namespace=("users", "{passenger_id}", "profile"),  # Isolate profiles by user
    schemas=[UserProfile],
    instructions="根据用户对话内容，提取用户画像信息",
    enable_inserts=False,  # Update existing profile only
)
profile_executor = ReflectionExecutor(profile_manager)

##历史事件
episode_manager = create_memory_store_manager(
    base_model,
    namespace=("memories", "episodes"),
    schemas=[Episode],
    instructions="提取具有代表性的卓越问题解决案例，包括其为何有效的原因。",
    enable_inserts=True,  
)
episode_executor = ReflectionExecutor(episode_manager)


# 导出模块
from . import router
from . import flight
from . import airport
from . import chitchat
from . import summary
from . import translator
from . import artificial
from . import business

logger.info("节点模块初始化完成")

