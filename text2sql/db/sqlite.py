import asyncio
import aiosqlite
import pandas as pd
from typing import Any, Dict, List, Optional

from ..base.interfaces import AsyncDBConnector

class SQLiteConnector(AsyncDBConnector):
    """SQLite异步数据库连接器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.db_path = self.config.get("path", ":memory:")
        self.conn = None
    
    async def connect(self, **kwargs) -> Any:
        """异步连接到数据库"""
        if self.conn is None:
            self.conn = await aiosqlite.connect(self.db_path)
            # 设置行工厂以返回字典
            self.conn.row_factory = aiosqlite.Row
        return self.conn
    
    async def close(self) -> None:
        """异步关闭数据库连接"""
        if self.conn:
            await self.conn.close()
            self.conn = None
    
    async def run_sql(self, sql: str, **kwargs) -> pd.DataFrame:
        """异步执行SQL查询"""
        if not self.conn:
            await self.connect()
        
        # 异步执行查询
        async with self.conn.execute(sql) as cursor:
            rows = await cursor.fetchall()
            
            # 获取列名
            columns = [description[0] for description in cursor.description]
            
            # 转换为字典列表
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
        
        # 使用pandas处理结果
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None, lambda: pd.DataFrame(results)
        )
        
        return df
    
    async def get_schema(self, **kwargs) -> str:
        """异步获取数据库模式"""
        if not self.conn:
            await self.connect()
        
        # 获取所有表
        async with self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ) as cursor:
            tables = await cursor.fetchall()
        
        schema_parts = []
        
        # 获取每个表的结构
        for table in tables:
            table_name = table[0]
            
            # 获取表的CREATE语句
            async with self.conn.execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'"
            ) as cursor:
                create_stmt = await cursor.fetchone()
                
                if create_stmt and create_stmt[0]:
                    schema_parts.append(create_stmt[0] + ";")
        
        return "\n\n".join(schema_parts)
