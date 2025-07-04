"""
配置工厂模块

提供便捷的配置创建和管理功能
"""

from typing import Dict, Any, Optional
from . import load_config


class ConfigFactory:
    """配置工厂类，提供各种配置的创建方法"""
    
    @staticmethod
    def create_logger_config(module_name: Optional[str] = None) -> Dict[str, Any]:
        """
        创建日志配置
        
        Args:
            module_name: 模块名称，如果提供则在日志目录下创建子目录
            
        Returns:
            日志配置字典
        """
        base_config = load_config()
        logging_config = base_config.get("logging", {})
        
        log_dir = logging_config.get("dir", "logs")
        if module_name:
            log_dir = f"{log_dir}/{module_name}"
            
        return {
            "log_dir": log_dir,
            "log_level": logging_config.get("level", "INFO"),
            "max_bytes": logging_config.get("max_bytes", 10 * 1024 * 1024),
            "backup_count": logging_config.get("backup_count", 5)
        }
    
    @staticmethod
    def create_app_config() -> Dict[str, Any]:
        """
        创建应用配置
        
        Returns:
            应用配置字典
        """
        base_config = load_config()
        return base_config.get("app", {
            "title": "智能客户服务系统",
            "description": "机场智能客服API",
            "version": "1.0.0",
            "cors_origins": ["*"],
            "host": "0.0.0.0",
            "port": 8081
        })
    
    @staticmethod
    def create_directories_config() -> Dict[str, Any]:
        """
        创建目录配置
        
        Returns:
            目录配置字典
        """
        base_config = load_config()
        return base_config.get("directories", {
            "data": "data",
            "logs": "logs"
        })
    
    @staticmethod
    def create_graph_config() -> Dict[str, Any]:
        """
        创建图配置
        
        Returns:
            图配置字典
        """
        base_config = load_config()
        return base_config.get("graph", {
            "name": "airport_service_graph"
        })


# 便捷函数
def get_logger_config(module_name: Optional[str] = None) -> Dict[str, Any]:
    """获取日志配置的便捷函数"""
    return ConfigFactory.create_logger_config(module_name)


def get_app_config() -> Dict[str, Any]:
    """获取应用配置的便捷函数"""
    return ConfigFactory.create_app_config()


def get_directories_config() -> Dict[str, Any]:
    """获取目录配置的便捷函数"""
    return ConfigFactory.create_directories_config()


def get_graph_config() -> Dict[str, Any]:
    """获取图配置的便捷函数"""
    return ConfigFactory.create_graph_config()
