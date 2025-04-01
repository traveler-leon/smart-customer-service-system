from common.logging import setup_logger

# 初始化日志系统
setup_logger(
    log_dir="logs/text2sql",
    log_level="INFO",
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5
) 