from . import setup_logger, get_logger

def example_usage():
    # 设置日志系统
    setup_logger(
        log_dir="logs",
        log_level="DEBUG",
        max_bytes=5*1024*1024,  # 5MB
        backup_count=3
    )
    
    # 获取不同模块的日志记录器
    app_logger = get_logger("app")
    text2sql_logger = get_logger("text2sql")
    
    # 使用日志记录器
    app_logger.info("应用程序启动")
    text2sql_logger.debug("Text2SQL模块初始化")
    
    try:
        # 模拟一些操作
        app_logger.warning("这是一个警告消息")
        text2sql_logger.error("这是一个错误消息")
    except Exception as e:
        app_logger.critical(f"发生严重错误: {str(e)}", exc_info=True)

if __name__ == "__main__":
    example_usage() 