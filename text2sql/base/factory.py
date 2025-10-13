import importlib
from typing import Dict, Any, List, Type
from common.logging import get_logger
from .interfaces import AsyncLLMProvider, AsyncVectorStore, AsyncDBConnector, AsyncEmbeddingProvider
from .abstract import AsyncSmartSqlBase

# 获取日志记录器
logger = get_logger("text2sql.factory")




class AsyncStorageFactory:
    """异步向量存储工厂"""
    
    @staticmethod
    async def create(storage_type: str, embedding_provider=None, config: Dict[str, Any] = None) -> AsyncVectorStore:
        """异步创建向量存储实例"""
        logger.info(f"创建异步向量存储: {storage_type}")
        
        try:
            module_path = f"..storage.{storage_type.lower()}"
            class_name = f"{storage_type.capitalize()}Storage"
            # 动态导入模块
            module = importlib.import_module(module_path, package="text2sql.base")
            
            # 获取存储类
            storage_class = getattr(module, class_name)
            
            # 创建实例，传入嵌入提供者
            storage = storage_class(config, embedding_provider=embedding_provider)
            
            # 异步初始化
            await storage.initialize()
            
            logger.info(f"异步向量存储 {storage_type} 创建并初始化成功")
            return storage
            
        except (ImportError, AttributeError) as e:
            logger.error(f"创建异步向量存储失败: {str(e)}")
            raise ValueError(f"不支持的向量存储类型: {storage_type}, 错误: {str(e)}")

class AsyncDBFactory:
    """异步数据库连接器工厂"""
    
    @staticmethod
    async def create(db_type: str, config: Dict[str, Any] = None) -> AsyncDBConnector:
        """异步创建数据库连接器实例"""
        try:
            module_path = f"..db.{db_type.lower()}"
            class_name = f"{db_type.capitalize()}Connector"
            
            module = importlib.import_module(module_path, package="text2sql.base")
            connector_class = getattr(module, class_name)
            
            connector = connector_class(config)
            await connector.connect()
            return connector
        except (ImportError, AttributeError) as e:
            raise ValueError(f"不支持的数据库类型: {db_type}，错误：{str(e)}")


class AsyncSmartSqlFactory:
    """异步SmartSQL工厂"""
    
    @staticmethod
    async def create(config: Dict[str, Any]) -> "AsyncSmartSqlBase":
        """异步创建SmartSQL实例"""
        logger.info("开始创建异步SmartSQL实例")
        
        # 并行创建各组件
        import asyncio
        
        # 配置提取
        llm_config = config.get("llm", {})
        # 新增嵌入模型配置提取
        embedding_config = config.get("embedding", {})
        
        storage_config = config.get("storage", {})
        storage_type = storage_config.pop("type", "chromadb")
        
        db_config = config.get("db", {})
        db_type = db_config.pop("type", "postgres")
        
        from ..embedding.generic import GenericEmbedding
        
        embedding_provider = GenericEmbedding(embedding_config)
        logger.info("嵌入模型提供者创建成功")
        
        from ..llm.generic import GenericLLM
        llm_provider = GenericLLM(llm_config)
        logger.info("LLM提供者创建成功")
        
        # 然后并行创建其他异步组件
        storage_task = AsyncStorageFactory.create(storage_type, embedding_provider, storage_config)
        db_task = AsyncDBFactory.create(db_type, db_config)
        
        # 等待异步组件创建完成
        vector_store, db_connector = await asyncio.gather(
            storage_task, db_task
        )
        
        
        # 导入AsyncSmartSqlBase类
        from .abstract import AsyncSmartSqlBase
        
        # 创建实例
        smart_sql = AsyncSmartSqlBase(
            llm_provider=llm_provider,
            embedding_provider=embedding_provider,  # 添加嵌入模型提供者
            vector_store=vector_store,
            db_connector=db_connector,
            config=config
        )
        
        # 初始化（如有需要）
        await smart_sql.initialize()
        
        logger.info("异步SmartSQL实例创建成功")
        return smart_sql
