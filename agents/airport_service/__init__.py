"""
机场客服多智能体系统
"""
from langchain_openai import ChatOpenAI
from config.utils import config_manager
from .main_graph import build_airport_service_graph 
from .graph_compile import graph_manager

model_config = config_manager.get_agents_config().get("llm", {})
# 创建共用模型实例
base_model = ChatOpenAI(
    model=model_config.get("model"),
    temperature=model_config.get("temperature", 0.5),
    api_key=model_config.get("api_key"),
    base_url=model_config.get("base_url")
)


__all__ = [
    "build_airport_service_graph"
    ,"graph_manager"
    ]
