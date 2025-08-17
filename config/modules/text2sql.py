"""
Text2SQL模块配置
"""
import os

# 开发环境特定配置
TEXT2SQL_CONFIG = {
    # LLM配置
    "llm": {
        "api_key": os.environ.get("LLM_API_KEY"),
        "base_url": os.environ.get("LLM_BASE_URL"),
        "model": os.environ.get("LLM_MODEL"),
        "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.7")),
        "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", 20000))
    },
    
    # 嵌入模型配置
    "embedding": {
        "api_key": os.environ.get("EMBEDDING_API_KEY"),
        "base_url": os.environ.get("EMBEDDING_BASE_URL"),
        "embedding_model": os.environ.get("EMBEDDING_MODEL"),
        "dimensions": int(os.environ.get("EMBEDDING_DIMENSIONS", 1024)),
        "max_tokens": int(os.environ.get("EMBEDDING_MAX_TOKENS", 512))
    },
    
    # 数据库配置
    "db": {
        "type": os.environ.get("DB_TYPE", "postgresql"),
        "database": os.environ.get("DB_DATABASE", "hzwl"),
        "host": os.environ.get("DB_HOST", "192.168.0.200"),
        "port": int(os.environ.get("DB_PORT", "5432")),
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
        "min_size": int(os.environ.get("DB_MIN_SIZE", "2")),
        "max_size": int(os.environ.get("DB_MAX_SIZE", "5"))
    },
    
    # 向量数据库配置
    "storage": {
        "type": os.environ.get("STORAGE_TYPE", "chromadb"),
        "host": os.environ.get("CHROMA_HOST"),
        "port": int(os.environ.get("CHROMA_PORT", "8000")),
        "n_results": int(os.environ.get("CHROMA_N_RESULTS", "5")),
        "hnsw_config": {
            "M": int(os.environ.get("CHROMA_M", "16")),
            "construction_ef": int(os.environ.get("CHROMA_CONSTRUCTION_EF", "100")),
            "search_ef": int(os.environ.get("CHROMA_SEARCH_EF", "50")),
            "space": os.environ.get("CHROMA_SPACE", "cosine")
        }
    },
        # 缓存配置
    "cache": {
        "type": os.environ.get("CACHE_TYPE", "memory"),
        "max_size": int(os.environ.get("CACHE_MAX_SIZE", "100")),
        "ttl": int(os.environ.get("CACHE_TTL", "600"))  # 10分钟
    },
    "dialect": os.environ.get("DIALECT", "PostgreSQL"),
    "language": os.environ.get("LANGUAGE", "zh")
}