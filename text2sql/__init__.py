import asyncio
from typing import Dict, Any, Optional
from common.logging import setup_logger, get_logger

from .base.factory import AsyncSmartSqlFactory
from .base.interfaces import AsyncPlugin

# 初始化日志系统
setup_logger(
    log_dir="logs/text2sql",
    log_level="INFO",
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5
)

# 获取text2sql模块的日志记录器
logger = get_logger("text2sql")

async def create_text2sql(config: Optional[Dict[str, Any]] = None):
    """异步创建text2sql实例"""
    logger.info("开始创建异步text2sql实例")
    
    if config is None:
        # 默认配置
        config = {
            "llm": {
                "type": "qwen",  # 使用已实现的千问模型
                "api_key": "sk-2e8c1dd4f75a44bf8114b337a91",  # 替换为您的API密钥
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # 百炼服务的base_url
                "model": "qwen2.5-72b-instruct"  # 使用千问2.5-72B模型
            },
            "storage": {
                "type": "chromadb",
                "host": "116.198.252.198",
                "port": 8000,
                "n_results": 5,
                "hnsw_config": {
                    "M": 16,                  # 每个节点的最大出边数
                    "construction_ef": 100,   # 建立索引时考虑的邻居数
                    "search_ef": 50,          # 查询时考虑的邻居数
                    "space": "cosine"         # 向量空间距离计算方式
                }
            },
            "db": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "xtron",  # 使用默认数据库
                "user": "postgres",
                "password": "942413L_eon",
                "min_size": 2,
                "max_size": 5
            },
            "middlewares": [
                {"type": "cache", "max_size": 10, "ttl": 60}  # 小缓存以便于测试
            ],
            "dialect": "PostgreSQL",
            "language": "zh",
            "embedding": {
                "type": "qwen",  # 使用已实现的嵌入模型
                "api_key": "sk-2e8c1dd4f75a44bf8114b337a549",  # 请使用您的实际API密钥
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "embedding_model": "text-embedding-v3"
            }
        }
    
    # 异步创建实例
    smart_sql = await AsyncSmartSqlFactory.create(config)
    logger.info("异步text2sql实例创建成功")
    return smart_sql

async def register_plugin(smart_sql, plugin: AsyncPlugin):
    """异步注册插件"""
    logger.info(f"注册插件: {plugin.__class__.__name__}")
    
    if not hasattr(smart_sql, 'plugin_manager'):
        from .plugins.manager import AsyncPluginManager
        smart_sql.plugin_manager = AsyncPluginManager()
    
    # 注册并初始化插件
    smart_sql.plugin_manager.register_plugin(plugin)
    await smart_sql.plugin_manager.initialize_plugins(smart_sql)
    
    return smart_sql

# 为了兼容性提供同步入口点
def sync_create_text2sql(config: Optional[Dict[str, Any]] = None):
    """同步创建text2sql实例（内部使用异步）"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(create_text2sql(config))
