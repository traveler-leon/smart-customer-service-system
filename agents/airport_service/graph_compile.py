import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
import logging
from langgraph.graph import StateGraph
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.store.redis.aio import AsyncRedisStore
import redis.asyncio as redis
from config.utils import config_manager
from .main_nodes.summary import summarize_conversation

import platform
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Redis 配置
_redis_config = config_manager.get_agents_config().get("checkpoint-store")
REDIS_HOST = _redis_config.get("host")
REDIS_PORT = _redis_config.get("port")
REDIS_PASSWORD = _redis_config.get("password")
REDIS_DB = _redis_config.get("db")
REDIS_MAX_CONNECTIONS = _redis_config.get("max_connections", 20)

# TTL 配置（由LangGraph内置管理）
REDIS_CHECKPOINT_TTL = _redis_config.get("checkpoint_ttl", 7200)  # 2小时
REDIS_STORE_TTL = _redis_config.get("store_ttl", 86400)          # 24小时  
REDIS_SESSION_TTL = _redis_config.get("session_ttl", 1800)       # 30分钟

# 连接池配置
CONNECTION_POOL_CONFIG = {
    "max_connections": REDIS_MAX_CONNECTIONS,
    "retry_on_timeout": True,
    "retry_on_error": [ConnectionError, TimeoutError],
    "health_check_interval": 30,  # 30秒健康检查
    "socket_keepalive": True,
    "socket_keepalive_options": {}
}

# 构建Redis URL
def build_redis_url():
    """构建Redis连接URL"""
    if REDIS_PASSWORD:
        return f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:
        return f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

logger = logging.getLogger(__name__)

# TTL配置辅助函数
def get_checkpoint_ttl_config():
    """获取checkpoint的TTL配置"""
    return {
        "default_ttl": REDIS_CHECKPOINT_TTL,
        "expire_pattern": "checkpoints:*"
    }

def get_store_ttl_config():
    """获取store的TTL配置"""
    return {
        "default_ttl": REDIS_STORE_TTL,
        "expire_pattern": "store:*"
    }

# 图管理器 - 优化单例模式
class GraphManager:
    """管理多个图实例的优化单例类，支持连接池复用和TTL管理"""
    
    _instance = None
    _connection_pool: Optional[redis.ConnectionPool] = None
    _redis_url: Optional[str] = None
    _is_initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GraphManager, cls).__new__(cls)
            cls._instance._registered_graphs = {}
            cls._instance._graph_configs = {}  # 存储图的序列化配置
            cls._instance._compiled_graphs = {}  # 缓存已编译的图
        return cls._instance
    
    async def initialize(self):
        """初始化连接池和Redis组件（应用启动时调用一次）"""
        if self._is_initialized:
            return
            
        try:
            logger.info("🔧 初始化Redis连接池...")
            
            # 创建优化的连接池
            self._connection_pool = redis.ConnectionPool.from_url(
                build_redis_url(),
                **CONNECTION_POOL_CONFIG
            )
            
            # 测试连接
            test_client = redis.Redis(connection_pool=self._connection_pool)
            await test_client.ping()
            await test_client.aclose()
            # 存储Redis URL供后续使用
            self._redis_url = build_redis_url()
            self._is_initialized = True  
        except Exception as e:
            logger.error(f"❌ Redis连接池初始化失败: {e}")
            raise

    def register_graph(self, graph_id: str, graph: StateGraph):
        """注册一个新图"""
        self._registered_graphs[graph_id] = graph
        # 清除相关缓存
        if graph_id in self._graph_configs:
            del self._graph_configs[graph_id]
        if graph_id in self._compiled_graphs:
            del self._compiled_graphs[graph_id]
    
    @asynccontextmanager
    async def get_compiled_graph(self, graph_id: str = "default"):
        """获取已编译的图（使用连接池的Redis客户端，支持TTL）"""
        if not self._is_initialized:
            await self.initialize()
            
        # 确保请求的图已注册
        if graph_id not in self._registered_graphs:
            raise ValueError(f"图 '{graph_id}' 未注册")
        
        # 使用连接池创建Redis客户端
        redis_client = redis.Redis(connection_pool=self._connection_pool)
        
        try:
            checkpointer = AsyncRedisSaver(
                redis_client=redis_client,
                ttl=get_checkpoint_ttl_config()
            )
            store = AsyncRedisStore(
                redis_client=redis_client,
                ttl=get_store_ttl_config()
            )
            
            await checkpointer.asetup()
            await store.setup()
            
            # 编译图
            graph = self._registered_graphs[graph_id]
            compiled_graph = graph.compile(checkpointer=checkpointer, store=store)   
            yield compiled_graph
            
        finally:
            pass
    # 流式输出接口 - 优化版  
    async def process_chat_message_stream(self, message: str, thread_id: Dict, graph_id: str, output_node: List):
        """优化的流式消息处理"""
        async with self.get_compiled_graph(graph_id) as compiled_graph:
            async for msg_type, metadata in compiled_graph.astream(
                {"messages": ("human", message)}, 
                thread_id,
                stream_mode=["messages", "custom"]
            ):
                if msg_type == "messages" and metadata[0].content and metadata[1]["langgraph_node"] in output_node:
                    yield msg_type, metadata[1]["langgraph_node"], metadata[0].content
                elif msg_type == "custom" and metadata["node_name"] in output_node:
                    yield msg_type, metadata["node_name"], metadata["data"]
    
    async def process_chat_message(self, message: str, thread_id: Dict, graph_id: str):
        """优化的消息处理"""
        async with self.get_compiled_graph(graph_id) as compiled_graph:
            result = await compiled_graph.ainvoke(
                {"messages": ("human", message)}, 
                thread_id
            )
            return result["messages"][-1].content

    # 对话摘要 - 优化版
    async def summarize_conversation(self, thread_id: Dict, graph_id: str):
        """优化的对话摘要"""
        async with self.get_compiled_graph(graph_id) as compiled_graph:
            # 获取当前线程的消息历史
            messages = await compiled_graph.aget_state(thread_id)
            summary = await summarize_conversation(messages)
            return summary["summary"]
    
    async def get_connection_pool_stats(self):
        """获取连接池统计信息"""
        if not self._connection_pool:
            return {"status": "未初始化"}
        
        return {
            "max_connections": CONNECTION_POOL_CONFIG.get("max_connections", "未知"),
            "pool_class": self._connection_pool.__class__.__name__,
            "is_initialized": self._is_initialized
        }
    
    async def set_key_ttl(self, key: str, ttl: int):
        """为指定键设置TTL（手动设置特定键的过期时间）"""
        if not self._connection_pool:
            logger.warning("Redis连接池未初始化")
            return False
            
        try:
            redis_client = redis.Redis(connection_pool=self._connection_pool)
            result = await redis_client.expire(key, ttl)
            logger.info(f"为键 '{key}' 设置TTL {ttl}秒: {'成功' if result else '失败'}")
            return result
        except Exception as e:
            logger.error(f"设置键TTL失败: {e}")
            return False

    async def get_ttl_status(self) -> Dict:
        """获取TTL配置状态"""
        return {
            "checkpoint_ttl": REDIS_CHECKPOINT_TTL,
            "store_ttl": REDIS_STORE_TTL, 
            "session_ttl": REDIS_SESSION_TTL,
            "ttl_managed_by": "LangGraph内置TTL支持"
        }

    async def health_check(self) -> bool:
        """连接池健康检查"""
        try:
            if not self._connection_pool:
                return False
                
            test_client = redis.Redis(connection_pool=self._connection_pool)
            result = await test_client.ping()
            await test_client.aclose()
            return result
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
    
    async def cleanup(self):
        """清理资源，关闭所有Redis连接"""
        try:
            # 清理应用级连接池
            if self._connection_pool:
                await self._connection_pool.aclose()
            
            self._is_initialized = False
            logger.info("✅ Redis连接池清理完成（TTL由LangGraph自动管理）")
        except Exception as e:
            logger.error(f"清理连接池时出错: {e}")

# 创建全局单例实例
graph_manager = GraphManager()

# 应用启动/关闭的辅助函数
async def startup_redis():
    """应用启动时初始化Redis连接池"""
    await graph_manager.initialize()

async def shutdown_redis():
    """应用关闭时清理Redis连接"""
    await graph_manager.cleanup()
