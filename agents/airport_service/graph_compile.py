import os
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
from typing import Dict,List

# 图管理器 - 单例模式
class GraphManager:
    """管理多个图实例的单例类"""
    
    _instance = None
    
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
    async def get_chat_app(self, graph_id: str = "default"):
        """获取已编译的聊天应用实例"""
        # 确保请求的图已注册
        if graph_id not in self._registered_graphs:
            raise ValueError(f"图 '{graph_id}' 未注册")
        
        # 确保数据目录存在
        os.makedirs("data", exist_ok=True)
        db_path = f"data/{graph_id}.db"
        
        # 创建新的saver和连接
        saver = AsyncSqliteSaver.from_conn_string(db_path)
        async with saver as active_saver:
            # 检查是否有缓存的配置
            if graph_id not in self._graph_configs:
                # 第一次编译并存储配置
                graph = self._registered_graphs[graph_id]
                compiled_graph = graph.compile(checkpointer=active_saver)
                # 存储图的配置
                self._graph_configs[graph_id] = {
                    "graph": graph,  # 存储原始图实例
                    "is_compiled": True
                }
            else:
                # 使用缓存的图实例重新编译
                graph = self._graph_configs[graph_id]["graph"]
                compiled_graph = graph.compile(checkpointer=active_saver)
            
            try:
                yield compiled_graph
            except Exception as e:
                print(f"Error in graph execution: {e}")
                raise
        
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
                    yield result.content
    
    async def cleanup(self):
        """清理资源，关闭所有数据库连接"""

# 创建全局单例实例
graph_manager = GraphManager()
