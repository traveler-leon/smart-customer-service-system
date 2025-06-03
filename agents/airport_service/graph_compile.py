import os
import asyncio
import urllib.parse
from psycopg.rows import dict_row
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore
from psycopg_pool import AsyncConnectionPool
from config.utils import config_manager
from .nodes.summary import summarize_conversation

import platform
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_agents_config = config_manager.get_agents_config().get("store")
DB_HOST = _agents_config.get("host")
DB_PORT = _agents_config.get("port")
DB_USER = _agents_config.get("user")
DB_PASSWORD = urllib.parse.quote_plus(_agents_config.get("password"))
DB_DATABASE = _agents_config.get("database")
DB_POOL_MIN_SIZE = _agents_config.get("min_size")
DB_POOL_MAX_SIZE = _agents_config.get("max_size")


from contextlib import asynccontextmanager
from typing import Dict,List

# 图管理器 - 单例模式
class GraphManager:
    """管理多个图实例的单例类"""
    
    _instance = None
    _checkpointer: AsyncPostgresSaver = None # Type hint
    _store: AsyncPostgresStore = None        # Type hint
    _db_pool: AsyncConnectionPool = None     # Optional: if sharing a single pool explicitly
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GraphManager, cls).__new__(cls)
            cls._instance._registered_graphs = {}
            cls._instance._graph_configs = {}  # 存储图的序列化配置
            # 注册默认图
        return cls._instance
    
    def register_graph(self, graph_id: str, graph: StateGraph):
        """注册一个新图"""
        self._registered_graphs[graph_id] = graph
        # 清除缓存的配置
        if graph_id in self._graph_configs:
            del self._graph_configs[graph_id]
    
    @asynccontextmanager
    async def _create_db_connections(self, conn_uri):
        """创建并设置数据库连接（checkpointer和store）
        
        Args:
            conn_uri: 数据库连接URI
            
        Returns:
            tuple: (active_checkpointer, active_store) 准备好的数据库连接
        """
        # 使用共享的连接池
        if not self._db_pool or self._db_pool.closed:
            await self.initialize_pool()
            
        # 创建 checkpointer 并传递池
        checkpointer = AsyncPostgresSaver(self._db_pool)
        store = AsyncPostgresStore(self._db_pool)
        
        await checkpointer.setup()
        await store.setup()
        
        try:
            yield checkpointer, store
        except Exception as e:
            print(f"Database connection error: {e}")
            raise
    
    @asynccontextmanager
    async def get_chat_app(self, graph_id: str = "default"):
        """获取已编译的聊天应用实例"""
        # 确保请求的图已注册
        if graph_id not in self._registered_graphs:
            raise ValueError(f"图 '{graph_id}' 未注册")
        
        conn_uri = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
        # 创建并使用数据库连接
        async with self._create_db_connections(conn_uri) as (active_checkpointer, active_store):
            # 检查是否有缓存的配置
            if graph_id not in self._graph_configs:
                # 第一次编译并存储配置
                graph = self._registered_graphs[graph_id]
                compiled_graph = graph.compile(checkpointer=active_checkpointer, store=active_store)
                # 存储图的配置
                self._graph_configs[graph_id] = {
                    "graph": graph,  # 存储原始图实例
                    "is_compiled": True
                }
            else:
                # 使用缓存的图实例重新编译
                graph = self._graph_configs[graph_id]["graph"]
                compiled_graph = graph.compile(checkpointer=active_checkpointer, store=active_store)
            
            try:
                yield compiled_graph
            except Exception as e:
                print(f"Error in graph execution: {e}")
                raise
    # 对话   
    async def process_chat_message(self, message: str, thread_id: Dict, graph_id: str,output_node:List):
        """处理聊天消息
        
        Args:
            message: It's the user message for chat agent to handle
            thread_id: 线程ID
            graph_id: 要使用的图的ID，默认为"default"
        """
        async with self.get_chat_app(graph_id) as chat_app:
            async for result, metadata in chat_app.astream(
                {"messages": ("human", message)}, 
                thread_id,
                stream_mode="messages"
            ):
                if result.content and metadata["langgraph_node"] in output_node:
                    yield metadata["langgraph_node"],result.content

    # 对话摘要
    async def summarize_conversation(self,  thread_id: Dict, graph_id: str):
        """对对话进行摘要总结"""
        """对对话进行摘要总结
        
        Args:
            thread_id: 线程ID
            graph_id: 要使用的图的ID，默认为"default"
            
        Returns:
            对话摘要
        """
        # 获取已编译的图实例
        async with self.get_chat_app(graph_id) as chat_app:
            # 获取当前线程的消息历史
            messages = await chat_app.aget_state(thread_id)
            summary = await summarize_conversation(messages)
            return summary["summary"]
    
    async def initialize_pool(self):
        # 创建持久连接池
        connection_kwargs = {
            "autocommit": True,  # 已存在，确保为True
            "prepare_threshold": 0,
            "row_factory": dict_row  # 添加这一行
        }

        self._db_pool = AsyncConnectionPool(
            conninfo=f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}",
            min_size=DB_POOL_MIN_SIZE,
            max_size=DB_POOL_MAX_SIZE,
            kwargs=connection_kwargs
        )
        await self._db_pool.open()
    
    async def cleanup(self):
        """清理资源，关闭所有数据库连接"""
        if self._db_pool:
            await self._db_pool.close()

# 创建全局单例实例
graph_manager = GraphManager()
