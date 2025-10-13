"""
共享的模型实例定义
避免循环导入问题
"""
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from config.utils import config_manager

# 从配置文件获取模型配置
llm_model_config = config_manager.get_agents_config().get("llm", {})
emb_model_config = config_manager.get_agents_config().get("embedding", {})



# 创建共用模型实
if llm_model_config.get("enable_thinking") == True:
    content_model = ChatOpenAI(
        model_name=llm_model_config.get("model"),
        temperature=llm_model_config.get("temperature", 0.7),
        extra_body={"thinking":{"type":"enabled"}},
        streaming=True,
        openai_api_key=llm_model_config.get("api_key"),
        openai_api_base=llm_model_config.get("base_url")
    )
else:
    content_model = ChatOpenAI(
        model_name=llm_model_config.get("model"),
        temperature=llm_model_config.get("temperature", 0.7),
        openai_api_key=llm_model_config.get("api_key"),
        openai_api_base=llm_model_config.get("base_url")
    )


base_model = ChatOpenAI(
    model_name=llm_model_config.get("model"),
    temperature=llm_model_config.get("temperature", 0.7),
    openai_api_key=llm_model_config.get("api_key"),
    openai_api_base=llm_model_config.get("base_url")
)
structed_model = ChatOpenAI(
    model_name=llm_model_config.get("router_model"),
    temperature=llm_model_config.get("router_temperature", 0.7),
    openai_api_key=llm_model_config.get("router_api_key"),
    openai_api_base=llm_model_config.get("router_base_url")
)


image_model = ChatOpenAI(
    model_name=llm_model_config.get("image_thinking_model"),
    temperature=llm_model_config.get("image_thinking_temperature", 0.7),
    openai_api_key=llm_model_config.get("image_thinking_api_key"),
    openai_api_base=llm_model_config.get("image_thinking_base_url")
)


emb_model = OpenAIEmbeddings(
    model=emb_model_config.get("embedding_model"),
    openai_api_key=emb_model_config.get("api_key"),
    openai_api_base=emb_model_config.get("base_url"),
    # dimensions=emb_model_config.get("dimensions")
)