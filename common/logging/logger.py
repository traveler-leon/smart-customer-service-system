import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any

class LoggerManager:
    _instance = None
    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def setup(cls, 
              log_dir: str = "logs",
              log_level: str = "INFO",
              max_bytes: int = 10 * 1024 * 1024,  # 10MB
              backup_count: int = 5,
              format_string: Optional[str] = None) -> None:
        """
        设置日志系统
        
        Args:
            log_dir: 日志文件目录
            log_level: 日志级别
            max_bytes: 单个日志文件最大大小
            backup_count: 保留的日志文件数量
            format_string: 自定义日志格式
        """
        if cls._initialized:
            return

        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)

        # 设置默认日志格式
        if format_string is None:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        # 创建根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(format_string))
        root_logger.addHandler(console_handler)

        # 创建文件处理器
        log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(format_string))
        root_logger.addHandler(file_handler)

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称
            
        Returns:
            logging.Logger: 日志记录器实例
        """
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]

def setup_logger(**kwargs: Any) -> None:
    """
    设置日志系统的便捷函数
    
    Args:
        **kwargs: 传递给LoggerManager.setup的参数
    """
    LoggerManager().setup(**kwargs)

def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器的便捷函数
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    return LoggerManager().get_logger(name) 