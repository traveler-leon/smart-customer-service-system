import asyncio
from typing import List, Dict, Any, Optional
from common.logging import get_logger
from ..base.interfaces import AsyncPlugin

# 获取日志记录器
logger = get_logger("text2sql.plugins")

class AsyncPluginManager:
    """异步插件管理器"""
    
    def __init__(self):
        self.plugins: List[AsyncPlugin] = []
        logger.info("初始化异步插件管理器")
    
    def register_plugin(self, plugin: AsyncPlugin) -> 'AsyncPluginManager':
        """注册插件"""
        logger.info(f"注册插件: {plugin.__class__.__name__}")
        self.plugins.append(plugin)
        return self
    
    async def initialize_plugins(self, smart_sql) -> None:
        """异步初始化所有插件"""
        if not self.plugins:
            logger.info("没有插件需要初始化")
            return
        
        logger.info(f"开始初始化 {len(self.plugins)} 个插件")
        init_tasks = []
        for plugin in self.plugins:
            init_tasks.append(plugin.initialize(smart_sql))
            
        # 并行初始化所有插件
        await asyncio.gather(*init_tasks)
        logger.info("所有插件初始化完成")
    
    async def execute_before_hooks(self, question: str, **kwargs) -> str:
        """异步执行所有前置钩子"""
        modified_question = question
        
        for plugin in self.plugins:
            # 串行执行以确保正确的顺序
            modified_question = await plugin.on_before_generate_sql(modified_question, **kwargs)
            
        return modified_question
    
    async def execute_after_hooks(self, question: str, sql: str, **kwargs) -> str:
        """异步执行所有后置钩子"""
        modified_sql = sql
        
        for plugin in self.plugins:
            # 串行执行以确保正确的顺序
            modified_sql = await plugin.on_after_generate_sql(question, modified_sql, **kwargs)
            
        return modified_sql
    
    async def execute_error_hooks(self, error: Exception, **kwargs) -> None:
        """异步执行所有错误钩子"""
        # 并行执行所有错误处理钩子
        error_tasks = []
        for plugin in self.plugins:
            error_tasks.append(plugin.on_error(error, **kwargs))
            
        await asyncio.gather(*error_tasks)
