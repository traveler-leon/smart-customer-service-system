"""
节点模块
"""

from langchain_openai import ChatOpenAI
from config.utils import config_manager
from typing import List, Dict
from langmem import create_memory_store_manager,ReflectionExecutor
from langchain.chat_models import init_chat_model
from agents.airport_service.state import UserProfile,Episode

# 从配置文件获取模型配置
model_config = config_manager.get_agents_config().get("llm", {})
max_msg_len = model_config.get("max_history_turns", 10)
max_tokens = model_config.get("max_tokens", 10000)
memery_delay = 60*30

emotion = config_manager.get_agents_config().get("emotions")


# 创建共用模型实例
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
def filter_messages(state: Dict, nb_messages: int = 10) -> Dict:
    """过滤消息列表，返回适合处理的格式"""
    messages = state.get("messages", [])
    if len(messages) > nb_messages:
        messages = messages[-nb_messages:]
    return {**state, "messages": messages}


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

