"""
节点模块
"""

from langchain_openai import ChatOpenAI
from config.utils import config_manager
from typing import List, Dict

# 从配置文件获取模型配置
model_config = config_manager.get_agents_config().get("llm", {})

# 创建共用模型实例
base_model = ChatOpenAI(
    model=model_config.get("model"),
    temperature=model_config.get("temperature", 0.5),
    api_key=model_config.get("api_key"),
    base_url=model_config.get("base_url")
)

# 将 filter_messages 函数移动到这里
def filter_messages(state: Dict, nb_messages: int = 10) -> Dict:
    """过滤消息列表，返回适合处理的格式"""
    messages = state.get("messages", [])
    if len(messages) > nb_messages:
        messages = messages[-nb_messages:]
    return {**state, "messages": messages}

# 导出模块
from . import router
from . import flight
from . import airport
from . import chitchat

