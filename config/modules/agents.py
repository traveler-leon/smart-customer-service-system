"""
机场服务模块配置
"""
import os

AGENTS_CONFIG = {
    "llm": {
        "base_model_type": os.getenv("LLM_TYPE"),
        "base_url": os.getenv("LLM_BASE_URL"),
        "api_key": os.getenv("LLM_API_KEY"),
        "model": os.getenv("LLM_MODEL"),
        "temperature": os.getenv("LLM_TEMPERATURE"),
        "max_history_turns": int(os.getenv("LLM_MAX_HISTORY_TURNS", "10")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1000")),
        "router_base_url": os.getenv("ROUTER_LLM_BASE_URL"),
        "router_api_key": os.getenv("ROUTER_LLM_API_KEY"),
        "router_model": os.getenv("ROUTER_LLM_MODEL"),
        "router_temperature": os.getenv("ROUTER_LLM_TEMPERATURE"),

    },
    "store":{
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_DATABASE"),
        "min_size": int(os.getenv("DB_POOL_MIN_SIZE", "5")),
        "max_size": int(os.getenv("DB_POOL_MAX_SIZE", "20"))
    },
    "emotions":{
        'model_path':os.getenv("EMOTION_MODEL","tabularisai/multilingual-sentiment-analysis")
    }
} 