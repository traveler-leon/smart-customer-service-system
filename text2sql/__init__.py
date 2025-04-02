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
                "type": "qianwen",
                "temperature": 0.7,
                "api_key": "your_qianwen_api_key"
            },
            "storage": {
                "type": "chromadb",
                "host": "localhost",
                "port": 8000,
                "similarity_metric": "cosine",  # 相似度度量方式: cosine, l2, ip
                "hnsw_config": {
                    "M": 16,               # 图中每个节点的连接数
                    "efConstruction": 100, # 构建索引时的精度参数
                    "ef": 50               # 搜索时的精度参数
                },
                "n_results": 10,          # 默认返回结果数量
                "n_results_sql": 5,       # SQL查询返回结果数量
                "n_results_ddl": 3,       # DDL查询返回结果数量
                "n_results_documentation": 15 # 文档查询返回结果数量
            },
            "db": {
                "type": "sqlite",
                "path": ":memory:"
            },
            "middlewares": [
                {"type": "cache", "max_size": 100, "ttl": 3600}
            ],
            "dialect": "SQL",
            "language": "zh",
            "embedding": {
                "type": "openai",
                "api_key": "sk-zcewmhyhkaelmhrijbipqbrlfxhwnfbuegcpynkhdbzkqixd",
                "base_url": "https://api.siliconflow.cn/v1",  # 硅流API的base_url
                "embedding_model": "BAAI/bge-large-zh-v1.5"  # 使用BGE中文嵌入模型
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
