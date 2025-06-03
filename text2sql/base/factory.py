import importlib
from typing import Dict, Any, List, Type
from common.logging import get_logger
from .interfaces import AsyncLLMProvider, AsyncVectorStore, AsyncDBConnector, AsyncMiddleware, AsyncEmbeddingProvider
from .abstract import AsyncSmartSqlBase

# 获取日志记录器
logger = get_logger("text2sql.factory")

class AsyncLLMFactory:
    """异步LLM提供者工厂"""
    
    @staticmethod
    async def create(provider_type: str, config: Dict[str, Any] = None) -> AsyncLLMProvider:
        """异步创建LLM提供者实例"""
        logger.info(f"创建LLM提供者: {provider_type}")
        # 使用动态导入创建实例
        try:
            module_path = f"..llm.{provider_type.lower()}"
            class_name = f"{provider_type.capitalize()}LLM"
            
            module = importlib.import_module(module_path, package="text2sql.base")
            provider_class = getattr(module, class_name)
            
            provider = provider_class(config)
            logger.info(f"{provider_type} LLM提供者创建成功")
            return provider
        except (ImportError, AttributeError) as e:
            logger.error(f"创建LLM提供者失败: {str(e)}")
            raise ValueError(f"不支持的LLM提供者类型: {provider_type}，错误：{str(e)}")

class AsyncEmbeddingFactory:
    """异步嵌入模型提供者工厂"""
    
    @staticmethod
    async def create(provider_type: str, config: Dict[str, Any] = None) -> AsyncEmbeddingProvider:
        """异步创建嵌入模型提供者实例"""
        logger.info(f"创建嵌入模型提供者: {provider_type}")
        # 使用动态导入创建实例
        try:
            module_path = f"..embedding.{provider_type.lower()}"
            class_name = f"{provider_type.capitalize()}Embedding"
            
            module = importlib.import_module(module_path, package="text2sql.base")
            provider_class = getattr(module, class_name)
            
            provider = provider_class(config)
            logger.info(f"{provider_type} 嵌入模型提供者创建成功")
            return provider
        except (ImportError, AttributeError) as e:
            logger.error(f"创建嵌入模型提供者失败: {str(e)}")
            raise ValueError(f"不支持的嵌入模型提供者类型: {provider_type}，错误：{str(e)}")

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

class AsyncMiddlewareFactory:
    """异步中间件工厂"""
    
    @staticmethod
    async def create(middleware_type: str, config: Dict[str, Any] = None) -> AsyncMiddleware:
        """异步创建中间件实例"""
        try:
            module_path = f"..middleware.{middleware_type.lower()}"
            class_name = f"{middleware_type.capitalize()}Middleware"
            
            module = importlib.import_module(module_path, package="text2sql.base")
            middleware_class = getattr(module, class_name)
            
            middleware = middleware_class(config)
            return middleware
        except (ImportError, AttributeError) as e:
            raise ValueError(f"不支持的中间件类型: {middleware_type}，错误：{str(e)}")

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
        llm_type = llm_config.pop("type", "qwen")
        
        # 新增嵌入模型配置提取
        embedding_config = config.get("embedding", {})
        # 如果没有独立配置嵌入模型，默认使用与LLM相同的提供商
        embedding_type = embedding_config.pop("type", "qwen")
        
        storage_config = config.get("storage", {})
        storage_type = storage_config.pop("type", "chromadb")
        
        db_config = config.get("db", {})
        db_type = db_config.pop("type", "postgres")
        
        # 首先创建嵌入提供者，因为存储器需要它
        embedding_provider = await AsyncEmbeddingFactory.create(embedding_type, embedding_config)
        
        # 然后并行创建其他组件
        llm_task = AsyncLLMFactory.create(llm_type, llm_config)
        storage_task = AsyncStorageFactory.create(storage_type, embedding_provider, storage_config)
        db_task = AsyncDBFactory.create(db_type, db_config)
        
        # 等待所有组件创建完成
        llm_provider, vector_store, db_connector = await asyncio.gather(
            llm_task, storage_task, db_task
        )
        
        # 创建中间件（如果有）
        middlewares = []
        middleware_configs = config.get("middlewares", [])
        for mw_config in middleware_configs:
            mw_type = mw_config.pop("type")
            middleware = await AsyncMiddlewareFactory.create(mw_type, mw_config)
            middlewares.append(middleware)
        
        # 导入AsyncSmartSqlBase类
        from .abstract import AsyncSmartSqlBase
        
        # 创建实例
        smart_sql = AsyncSmartSqlBase(
            llm_provider=llm_provider,
            embedding_provider=embedding_provider,  # 添加嵌入模型提供者
            vector_store=vector_store,
            db_connector=db_connector,
            middlewares=middlewares,
            config=config
        )
        
        # 初始化（如有需要）
        await smart_sql.initialize()
        
        logger.info("异步SmartSQL实例创建成功")
        return smart_sql
