"""
共享的模型实例定义
避免循环导入问题
"""
from langchain_openai import ChatOpenAI
from config.utils import config_manager

# 从配置文件获取模型配置
model_config = config_manager.get_agents_config().get("llm", {})

# 创建共用模型实例
if model_config.get("base_model_type") == "qwen":
    from langchain_qwq import ChatQwen
    content_model = ChatQwen(
        model=model_config.get("model"),
        temperature=model_config.get("temperature", 0.7),
        api_key=model_config.get("api_key"),
        base_url=model_config.get("base_url"),
        enable_thinking=False)
else:
    content_model = ChatOpenAI(
        model=model_config.get("model"),
        temperature=model_config.get("temperature", 0.7),
        api_key=model_config.get("api_key"),
        base_url=model_config.get("base_url")
    )

base_model = ChatOpenAI(
    model=model_config.get("model"),
    temperature=model_config.get("temperature", 0.7),
    api_key=model_config.get("api_key"),
    base_url=model_config.get("base_url")
)

structed_model = ChatOpenAI(
    model=model_config.get("router_model"),
    temperature=model_config.get("router_temperature", 0.7),
    api_key=model_config.get("router_api_key"),
    base_url=model_config.get("router_base_url")
)

if model_config.get("image_thinking_model"):
    image_model = ChatOpenAI(
        model=model_config.get("image_thinking_model"),
        api_key=model_config.get("image_thinking_api_key"),
        base_url=model_config.get("image_thinking_base_url")
    ) 