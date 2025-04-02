import asyncio
from text2sql import create_text2sql

async def main():
    # 创建异步text2sql实例
    smart_sql = await create_text2sql({
        "llm": {
            "type": "qianwen",
            "api_key": "你的API密钥",
            "temperature": 0.7
        },
        "storage": {
            "type": "chromadb",
            "path": "./vector_db"
        },
        "db": {
            "type": "sqlite",
            "path": "example.db"
        },
        "middlewares": [
            {"type": "cache"}  # 只使用缓存中间件，不使用日志中间件
        ],
        "dialect": "SQLite",
        "language": "zh"
    })
    
    # 添加一些示例数据
    await smart_sql.vector_store.add_ddl("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        registration_date DATE,
        status TEXT
    );
    
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        order_date DATE,
        total_amount DECIMAL(10, 2),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    """)
    
    # 添加示例问题和SQL
    await smart_sql.vector_store.add_question_sql(
        "查询所有客户的数量",
        "SELECT COUNT(*) AS customer_count FROM customers;"
    )
    
    # 异步生成SQL
    sql = await smart_sql.generate_sql("统计每个月新增的客户数量")
    
    print(f"生成的SQL: {sql}")
    
    # 关闭资源
    await smart_sql.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
