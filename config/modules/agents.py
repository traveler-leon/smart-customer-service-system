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
        "image_thinking_base_url": os.getenv("IMAGE_LLM_BASE_URL",""),
        "image_thinking_api_key": os.getenv("IMAGE_LLM_API_KEY",""),
        "image_thinking_model": os.getenv("IMAGE_LLM_MODEL",""),

    },
    "checkpoint-store": {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "password": os.getenv("REDIS_PASSWORD",""),
        "db": int(os.getenv("REDIS_DB", "0")),
        
        # 连接池优化配置
        "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),  # 增加到50  
        # TTL 过期时间配置（秒）
        "checkpoint_ttl": int(os.getenv("REDIS_CHECKPOINT_TTL", "7200")),  # checkpoint过期时间，默认2小时
        "store_ttl": int(os.getenv("REDIS_STORE_TTL", "86400")),          # store过期时间，默认24小时
        "session_ttl": int(os.getenv("REDIS_SESSION_TTL", "1800")),       # 会话过期时间，默认30分钟
        
        # 注意：TTL清理由LangGraph内置管理，无需额外配置
    },
    "emotions":{
        'model_path':os.getenv("EMOTION_MODEL","tabularisai/multilingual-sentiment-analysis")
    }
} 