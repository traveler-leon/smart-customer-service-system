"""
Text2SQL模块配置
"""
import os

# 开发环境特定配置
TEXT2SQL_CONFIG = {
    # LLM配置
    "llm": {
        "api_key": os.getenv("LLM_API_KEY"),
        "base_url": os.getenv("LLM_BASE_URL"),
        "model": os.getenv("LLM_MODEL"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", 20000))
    },
    
    # 嵌入模型配置
    "embedding": {
        "api_key": os.getenv("EMBEDDING_API_KEY",os.getenv("LLM_API_KEY")),
        "base_url": os.getenv("EMBEDDING_BASE_URL",os.getenv("LLM_BASE_URL")),
        "embedding_model": os.getenv("EMBEDDING_MODEL"),
        "dimensions": int(os.getenv("EMBEDDING_DIMENSIONS", 512)),
        "max_tokens": int(os.getenv("EMBEDDING_MAX_TOKENS", 1024))
    },
    
    # 数据库配置
    "db": {
        "type": os.getenv("DB_TYPE", "postgresql"),
        "database": os.getenv("DB_DATABASE", "hzwl"),
        "host": os.getenv("DB_HOST", "192.168.0.200"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "min_size": int(os.getenv("DB_MIN_SIZE", "2")),
        "max_size": int(os.getenv("DB_MAX_SIZE", "5"))
    },
    
    # 向量数据库配置
    "storage": {
        "type": os.getenv("STORAGE_TYPE", "chromadb"),
        "host": os.getenv("CHROMA_HOST"),
        "port": int(os.getenv("CHROMA_PORT", "8000")),
        "n_results": int(os.getenv("CHROMA_N_RESULTS", "5")),
        "hnsw_config": {
            "M": int(os.getenv("CHROMA_M", "16")),
            "construction_ef": int(os.getenv("CHROMA_CONSTRUCTION_EF", "100")),
            "search_ef": int(os.getenv("CHROMA_SEARCH_EF", "50")),
            "space": os.getenv("CHROMA_SPACE", "cosine")
        }
    },
        # 缓存配置
    "cache": {
        "type": os.getenv("CACHE_TYPE", "memory"),
        "max_size": int(os.getenv("CACHE_MAX_SIZE", "100")),
        "ttl": int(os.getenv("CACHE_TTL", "600"))  # 10分钟
    },
    "dialect": os.getenv("DIALECT", "PostgreSQL"),
    "language": os.getenv("LANGUAGE", "zh")
}