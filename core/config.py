import os
from typing import List

class Settings:
    """应用配置类"""
    APP_TITLE: str = "智能客户服务系统"
    APP_DESCRIPTION: str = "智能机场客服系统API"
    API_VERSION: str = "1.0.0"
    # 允许的CORS来源
    CORS_ORIGINS: List[str] = ["*"]
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    # 数据目录
    DATA_DIR: str = "data"
    # 图管理器配置
    GRAPH_NAME: str = "airport_service_graph"

settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.LOG_DIR, exist_ok=True) 