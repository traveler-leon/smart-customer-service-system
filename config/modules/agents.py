"""
机场服务模块配置
"""
import os

AGENTS_CONFIG = {
    "llm": {
        "base_url": os.getenv("LLM_BASE_URL"),
        "api_key": os.getenv("LLM_API_KEY"),
        "model": os.getenv("LLM_MODEL"),
        "temperature": os.getenv("LLM_TEMPERATURE"),
        "max_history_turns": int(os.getenv("LLM_MAX_HISTORY_TURNS", "10")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1000")),
    }
} 