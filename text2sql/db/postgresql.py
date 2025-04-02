import asyncio
import asyncpg
import pandas as pd
from typing import Any, Dict, List, Optional

from ..base.interfaces import AsyncDBConnector

class PostgresqlConnector(AsyncDBConnector):
    """PostgreSQL异步数据库连接器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 5432)
        self.database = self.config.get("database", "postgres")
        self.user = self.config.get("user", "postgres")
        self.password = self.config.get("password", "")
        self.conn = None
        self.pool = None
    
    async def connect(self, **kwargs) -> Any:
        """异步连接到数据库"""
        if self.pool is None:
            # 创建连接池
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                **kwargs
            )
        return self.pool
    
    async def close(self) -> None:
        """异步关闭数据库连接"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def run_sql(self, sql: str, **kwargs) -> pd.DataFrame:
        """异步执行SQL查询"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            # 异步执行查询
            stmt = await conn.prepare(sql)
            rows = await stmt.fetch()
            
            # 获取列名
            columns = [desc.name for desc in stmt.get_attributes()]
            
            # 转换为字典列表
            results = []
            for row in rows:
                results.append({columns[i]: row[i] for i in range(len(columns))})
        
        # 使用pandas处理结果
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None, lambda: pd.DataFrame(results)
        )
        
        return df
    
    async def get_schema(self, **kwargs) -> str:
        """异步获取数据库模式"""
        if not self.pool:
            await self.connect()
        
        schema_parts = []
        
        async with self.pool.acquire() as conn:
            # 获取所有表和视图
            tables = await conn.fetch("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
            """)
            
            for table in tables:
                table_name = table['table_name']
                table_schema = table['table_schema']
                
                # 获取列信息
                columns = await conn.fetch("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = $1 AND table_schema = $2
                    ORDER BY ordinal_position
                """, table_name, table_schema)
                
                # 创建CREATE TABLE语句
                create_stmt = [f"CREATE TABLE {table_schema}.{table_name} ("]
                
                column_defs = []
                for column in columns:
                    nullability = "NULL" if column['is_nullable'] == 'YES' else "NOT NULL"
                    default = f"DEFAULT {column['column_default']}" if column['column_default'] else ""
                    column_defs.append(
                        f"    {column['column_name']} {column['data_type']} {nullability} {default}".strip()
                    )
                
                create_stmt.append(",\n".join(column_defs))
                create_stmt.append(");")
                
                schema_parts.append("\n".join(create_stmt))
        
        return "\n\n".join(schema_parts)
