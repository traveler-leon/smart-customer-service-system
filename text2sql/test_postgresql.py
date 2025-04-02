import asyncio
import pandas as pd
from .db.postgresql import PostgresqlConnector

# 测试配置 - 请根据你的环境修改
CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "xtron",  # 使用默认数据库
    "user": "postgres",
    "password": "942413L_eon",
    "min_size": 2,
    "max_size": 5
}

async def test_postgresql():
    """简单测试PostgreSQL连接器"""
    print("开始测试PostgreSQL连接器...")
    
    # 初始化连接器
    db = PostgresqlConnector(CONFIG)
    
    try:
        # 测试1: 正常SQL查询
        print("\n测试1: 正常SQL查询")
        result = await db.run_sql("SELECT * from users")
        
        if isinstance(result, pd.DataFrame):
            print(f"✅ 查询成功! 结果类型: {type(result)}")
            print(f"数据内容:\n{result}")
        else:
            print(f"❌ 查询失败! 返回了非DataFrame结果: {result}")
        
        # 测试2: SQL语法错误
        print("\n测试2: SQL语法错误")
        result = await db.run_sql("SELEC 1")  # 故意拼写错误
        
        if isinstance(result, dict) and result.get("error"):
            print(f"✅ 语法错误测试成功! 错误信息: {result['message']}")
        else:
            print(f"❌ 语法错误测试失败! 返回了意外结果: {result}")
        
        # 测试3: 表不存在
        print("\n测试3: 表不存在")
        result = await db.run_sql("SELECT * FROM non_existent_table")
        
        if isinstance(result, dict) and result.get("error"):
            print(f"✅ 表不存在测试成功! 错误信息: {result['message']}")
        else:
            print(f"❌ 表不存在测试失败! 返回了意外结果: {result}")
        
        # 测试4: 获取数据库模式
        print("\n测试4: 获取数据库模式")
        try:
            schema = await db.get_schema()
            print(f"✅ 获取模式成功!")
            print(f"模式片段:\n{schema[:500]}...")  # 只打印前500个字符
        except Exception as e:
            print(f"❌ 获取模式失败! 错误: {str(e)}")
    
    except Exception as e:
        print(f"测试过程中发生未捕获异常: {str(e)}")
    finally:
        # 关闭连接
        print("\n关闭连接...")
        await db.close()
        print("测试完成!")

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_postgresql())
