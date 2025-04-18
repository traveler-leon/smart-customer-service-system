"""
机场服务模块配置
"""
import os

AGENTS_CONFIG = {
    "llm": {
        "base_url": os.getenv("LLM_BASE_URL"),
        "api_key": os.getenv("LLM_API_KEY"),
        "model": os.getenv("LLM_MODEL"),
        "temperature": os.getenv("LLM_TEMPERATURE")
    }
} 