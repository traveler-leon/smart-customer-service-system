"""
开发环境配置

包含应用程序的通用配置，特定模块的配置应放在config/modules目录下
"""

import os

# 开发环境基础配置
CONFIG = {
    # 应用配置
    "app": {
        "title": "智能客户服务系统",
        "description": "智能机场客服API",
        "version": "1.0.0",
        "cors_origins": ["*"],
        "host": "0.0.0.0",
        "port": 8081
    },
    # 日志配置
    "logging": {
        "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        "dir": os.environ.get("LOG_DIR", "logs"),
        "max_bytes": int(os.environ.get("LOG_MAX_BYTES", str(10 * 1024 * 1024))),  # 10MB
        "backup_count": int(os.environ.get("LOG_BACKUP_COUNT", "5"))
    },
    # 目录配置
    "directories": {
        "data": os.environ.get("DATA_DIR", "data"),
        "logs": os.environ.get("LOG_DIR", "logs")
    },
    # 图配置
    "graph": {
        "name": "airport_service_graph"
    }
}