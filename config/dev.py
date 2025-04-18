"""
开发环境配置

包含应用程序的通用配置，特定模块的配置应放在config/modules目录下
"""

import os

# 开发环境基础配置
CONFIG = {
    # 日志配置
    "logging": {
        "level": os.environ.get("LOG_LEVEL", "DEBUG"),
        "dir": os.environ.get("LOG_DIR", "logs"),
        "max_bytes": int(os.environ.get("LOG_MAX_BYTES", str(10 * 1024 * 1024))),  # 10MB
        "backup_count": int(os.environ.get("LOG_BACKUP_COUNT", "5"))
    }
} 