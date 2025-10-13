import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
import logging
from langgraph.graph import StateGraph
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
import redis.asyncio as redis
from config.utils import config_manager
from .main_nodes.summary import summarize_conversation
import hashlib

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

logger = logging.getLogger(__name__)

# 图管理器 - 简化单例模式
class GraphManager:
    """管理多个图实例的简化单例类"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GraphManager, cls).__new__(cls)
            cls._instance._registered_graphs = {}
            cls._instance._graph_db_mapping = {}  # 图ID到Redis数据库的映射
        return cls._instance

    def register_graph(self, graph_id: str, graph: StateGraph):
        """注册一个新图，并为其分配专用的索引前缀"""
        self._registered_graphs[graph_id] = graph
        # 为每个图生成唯一的索引前缀，避免索引名冲突
        index_prefix = self._get_graph_index_prefix(graph_id)
        self._graph_db_mapping[graph_id] = index_prefix
        logger.info(f"图 '{graph_id}' 已注册，索引前缀: {index_prefix}")
    
    def _get_graph_index_prefix(self, graph_id: str) -> str:
        """为图ID生成一个唯一的索引前缀"""
        # 使用哈希确保相同graph_id总是得到相同的前缀
        hash_obj = hashlib.md5(graph_id.encode())
        # 取哈希的前8位作为前缀，确保唯一性
        prefix = hash_obj.hexdigest()[:8]
        return f"lg_{prefix}"
    
    @asynccontextmanager
    async def get_compiled_graph(self, graph_id: str = "default"):
        """获取已编译的图（所有图使用数据库0，通过错误处理避免索引冲突）"""
        # 确保请求的图已注册
        if graph_id not in self._registered_graphs:
            raise ValueError(f"图 '{graph_id}' 未注册")
        
        # 所有图都使用数据库0（Redis索引限制）
        # 获取该图的索引前缀（用于日志记录）
        index_prefix = self._graph_db_mapping.get(graph_id, "default")
        
        # 创建Redis客户端，使用数据库0
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=0,  # 强制使用数据库0（Redis索引限制）
            password=REDIS_PASSWORD,
            decode_responses=False,  # checkpoint需要bytes模式
            max_connections=REDIS_MAX_CONNECTIONS,
            socket_connect_timeout=5.0,
            socket_timeout=5.0
        )
        
        try:
            # 测试连接
            await redis_client.ping()
            logger.debug(f"图 '{graph_id}' Redis连接成功，使用数据库: 0，索引前缀: {index_prefix}")
            
            # 创建checkpointer，使用正确的TTL配置格式
            ttl_config = {
                "default_ttl": REDIS_CHECKPOINT_TTL
            }
            checkpointer = AsyncRedisSaver(
                redis_client=redis_client,
                ttl=ttl_config
            )
            
            # 安全地设置checkpointer，处理各种索引相关异常
            try:
                await checkpointer.asetup()
                logger.debug(f"图 '{graph_id}' checkpointer设置成功")
            except Exception as setup_error:
                error_msg = str(setup_error)
                # 检查是否是索引相关的错误
                if any(keyword in error_msg for keyword in [
                    "Index already exists", 
                    "Cannot create index on db != 0",
                    "index name already exists"
                ]):
                    if "Cannot create index on db != 0" in error_msg:
                        logger.warning(f"图 '{graph_id}' 尝试在非0数据库创建索引，已强制使用数据库0")
                    else:
                        logger.info(f"图 '{graph_id}' 的Redis索引已存在，继续使用现有索引")
                    
                    # 索引问题不应该阻止图的正常使用，尝试继续
                    logger.info(f"图 '{graph_id}' 将尝试使用现有的Redis索引配置")
                else:
                    # 其他不相关的错误需要抛出
                    logger.error(f"图 '{graph_id}' checkpointer设置失败: {setup_error}")
                    raise
            
            # 编译图
            graph = self._registered_graphs[graph_id]
            compiled_graph = graph.compile(checkpointer=checkpointer)   
            yield compiled_graph
            
        except Exception as e:
            logger.error(f"图 '{graph_id}' 编译失败: {e}")
            raise
        finally:
            await redis_client.aclose()
    # 流式输出接口 - 优化版  
    async def process_chat_message_stream(self, message: str, thread_id: Dict, graph_id: str, msg_nodes: List,custom_nodes: List):
        """优化的流式消息处理"""
        async with self.get_compiled_graph(graph_id) as compiled_graph:
            async for msg_type, metadata in compiled_graph.astream(
                {"messages": ("human", message)}, 
                thread_id,
                stream_mode=["messages", "custom"]
            ):
                if msg_type == "messages" and metadata[0].content and metadata[1]["langgraph_node"] in msg_nodes:
                    yield msg_type, metadata[1]["langgraph_node"], metadata[0].content
                elif msg_type == "custom" and metadata["node_name"] in custom_nodes:
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
    
    async def get_redis_stats(self) -> Dict:
        """获取Redis连接状态"""
        return {
            "host": REDIS_HOST,
            "port": REDIS_PORT,
            "forced_db": 0,  # 所有图强制使用数据库0（Redis索引限制）
            "configured_db": REDIS_DB,  # 原配置的数据库
            "graph_index_mapping": self._graph_db_mapping,  # 现在存储索引前缀
            "max_connections": REDIS_MAX_CONNECTIONS,
            "checkpoint_ttl": REDIS_CHECKPOINT_TTL,
            "registered_graphs": list(self._registered_graphs.keys())
        }

    async def health_check(self) -> bool:
        """Redis健康检查"""
        try:
            test_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,  # 使用数据库0进行健康检查
                password=REDIS_PASSWORD,
                socket_connect_timeout=5.0,
                socket_timeout=5.0
            )
            result = await test_client.ping()
            await test_client.aclose()
            return result
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False

# 创建全局单例实例
graph_manager = GraphManager()

# 应用启动/关闭的辅助函数
async def startup_redis():
    """应用启动时检查Redis连接"""
    logger.info("🔧 检查Redis连接...")
    if await graph_manager.health_check():
        logger.info("✅ Redis连接正常")
    else:
        logger.error("❌ Redis连接失败")
        raise Exception("Redis连接失败")

async def shutdown_redis():
    """应用关闭时的清理工作"""
    logger.info("🔧 应用关闭，Redis连接将自动清理")
