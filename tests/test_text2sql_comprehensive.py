import asyncio
import unittest
import pandas as pd
from typing import Dict, Any, List

from text2sql import create_text2sql


class Text2SQLTestCase(unittest.TestCase):
    """测试Text2SQL模块的主要功能"""
    
    @classmethod
    async def asyncSetUp(cls):
        """异步设置测试环境"""
        # 创建测试配置
        cls.config = {
            "llm": {
                "type": "qwen",  # 使用已实现的千问模型
                "api_key": "sk-2e8c1dd4f7bf8114b337a549",  # 替换为您的API密钥
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # 百炼服务的base_url
                "model": "qwen2.5-72b-instruct"  # 使用千问2.5-72B模型
            },
            "storage": {
                "type": "chromadb",
                "host": "116.198.252.190",
                "port": 8000,
                "n_results": 5,
                "hnsw_config": {
                    "M": 16,                  # 每个节点的最大出边数
                    "construction_ef": 100,   # 建立索引时考虑的邻居数
                    "search_ef": 50,          # 查询时考虑的邻居数
                    "space": "cosine"         # 向量空间距离计算方式
                }
            },
            "db": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "xtron",  # 使用默认数据库
                "user": "postgres",
                "password": "942413L_eon",
                "min_size": 2,
                "max_size": 5
            },
            "middlewares": [
                {"type": "cache", "max_size": 10, "ttl": 60}  # 小缓存以便于测试
            ],
            "dialect": "PostgreSQL",
            "language": "zh",
            "embedding": {
                "type": "qwen",  # 使用已实现的嵌入模型
                "api_key": "sk-2e8c1dd4f4bf8114b337a541",  # 请使用您的实际API密钥
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "embedding_model": "text-embedding-v3"
            }
        }
        
        # 创建text2sql实例
        cls.smart_sql = await create_text2sql(cls.config)
        
        # 添加测试数据
        # await cls.smart_sql.vector_store.add_ddl("""
        # CREATE TABLE users (
        #     id INTEGER PRIMARY KEY,
        #     username TEXT NOT NULL,
        #     email TEXT UNIQUE,
        #     status TEXT,
        #     created_at TIMESTAMP
        # );
        
        # CREATE TABLE products (
        #     id INTEGER PRIMARY KEY,
        #     name TEXT NOT NULL,
        #     price DECIMAL(10, 2),
        #     category TEXT,
        #     inventory INTEGER
        # );
        
        # CREATE TABLE orders (
        #     id INTEGER PRIMARY KEY,
        #     user_id INTEGER,
        #     order_date TIMESTAMP,
        #     total_amount DECIMAL(10, 2),
        #     status TEXT,
        #     FOREIGN KEY (user_id) REFERENCES users(id)
        # );
        # """)
        
        # # 添加示例问题和SQL
        # await cls.smart_sql.vector_store.add_question_sql(
        #     "统计所有活跃用户的数量",
        #     "SELECT COUNT(*) FROM users WHERE status = 'active';"
        # )
        
        # await cls.smart_sql.vector_store.add_question_sql(
        #     "查询价格高于100元的产品",
        #     "SELECT * FROM products WHERE price > 100;"
        # )
        
        # # 添加文档
        # await cls.smart_sql.vector_store.add_documentation(
        #     "用户表中status字段可能的值包括: active, inactive, suspended。"
        # )
    
    @classmethod
    async def asyncTearDown(cls):
        """异步清理测试环境"""
        if hasattr(cls, 'smart_sql'):
            # 清理向量存储中的测试集合
            collections = ["test_question_sql", "test_ddl", "test_documentation"]
            for collection in collections:
                await cls.smart_sql.vector_store.remove_collection(collection)
            
            # 关闭资源
            await cls.smart_sql.shutdown()
    
    @classmethod
    def setUpClass(cls):
        """设置类级别测试环境"""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cls.asyncSetUp())
    
    @classmethod
    def tearDownClass(cls):
        """清理类级别测试环境"""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cls.asyncTearDown())
    
    def test_create_instance(self):
        """测试text2sql实例创建成功"""
        self.assertIsNotNone(self.smart_sql)
        self.assertIsNotNone(self.smart_sql.llm_provider)
        self.assertIsNotNone(self.smart_sql.embedding_provider)
        self.assertIsNotNone(self.smart_sql.vector_store)
        self.assertIsNotNone(self.smart_sql.db_connector)
        self.assertEqual(len(self.smart_sql.middlewares), 1)  # 应该有一个缓存中间件
    
    async def test_generate_sql(self):
        """测试SQL生成功能"""
        sql = await self.smart_sql.generate_sql("查询所有活跃用户")
        self.assertIsNotNone(sql)
        self.assertIn("SELECT", sql.upper())
        self.assertIn("USERS", sql.upper())
        self.assertIn("ACTIVE", sql.upper())
    
    async def test_embedding_generation(self):
        """测试嵌入生成功能"""
        embedding = await self.smart_sql.generate_embedding("测试文本")
        self.assertIsNotNone(embedding)
        self.assertTrue(len(embedding) > 0)
    
    async def test_vector_store_retrieval(self):
        """测试向量存储检索功能"""
        # 测试问题-SQL检索
        similar_questions = await self.smart_sql.vector_store.get_similar_question_sql("查询活跃用户数量")
        self.assertTrue(len(similar_questions) > 0)
        self.assertIn("question", similar_questions[0])
        self.assertIn("sql", similar_questions[0])
        
        # 测试文档检索
        docs = await self.smart_sql.vector_store.get_related_documentation("用户状态")
        self.assertTrue(len(docs) > 0)
        self.assertIn("status", docs[0])
    
    async def test_middleware(self):
        """测试中间件功能（缓存）"""
        # 找到缓存中间件
        cache_middleware = None
        for middleware in self.smart_sql.middlewares:
            if middleware.__class__.__name__ == "CacheMiddleware":
                cache_middleware = middleware
                break
                
        self.assertIsNotNone(cache_middleware, "未找到缓存中间件")
        
        # 记录初始命中次数
        initial_hits = cache_middleware.hits
        initial_misses = cache_middleware.misses
        
        # 第一次查询
        test_question = "查询所有活跃用户"
        sql1 = await self.smart_sql.generate_sql(test_question)
        
        # 验证缓存未命中
        self.assertEqual(cache_middleware.misses, initial_misses + 1, "第一次查询应该导致缓存未命中")
        self.assertEqual(cache_middleware.hits, initial_hits, "第一次查询不应导致缓存命中")
        
        # 相同查询应从缓存获取相同结果
        sql2 = await self.smart_sql.generate_sql(test_question)
        
        # 验证结果一致
        self.assertEqual(sql1, sql2, "两次查询结果应该一致")
        
        # 验证缓存命中
        self.assertEqual(cache_middleware.hits, initial_hits + 1, "第二次查询应该导致缓存命中")
        self.assertEqual(cache_middleware.misses, initial_misses + 1, "第二次查询不应增加未命中计数")

    async def test_run_sql(self):
        """测试SQL执行功能"""
        # 创建测试表
        
        # 执行查询
        result = await self.smart_sql.db_connector.run_sql("SELECT * FROM users")
        print(f"测试结果: {result}")
        
        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)

    async def test_ask(self):
        """测试ask方法功能"""
        # 使用ask方法发起问题
        question = "查询所有用户的数量"
        result = await self.smart_sql.ask(question)
        print(f"测试结果: {result}")
        # 验证结果结构
        self.assertIsInstance(result, dict)
        self.assertIn('sql', result)
        self.assertIn('data', result)
        
        # 验证SQL内容
        self.assertIsNotNone(result['sql'])
        self.assertIn('SELECT', result['sql'].upper())
        self.assertIn('COUNT', result['sql'].upper())
        self.assertIn('USERS', result['sql'].upper())
        
        # 验证数据结果
        self.assertIsNotNone(result['data'])
        if not isinstance(result['data'], dict) or not result['data'].get('error'):
            # 如果不是错误结果，应该是记录列表
            self.assertIsInstance(result['data'], list)
        
        # 测试包含错误的情况
        # error_question = "查询不存在的表中的数据"
        # error_result = await self.smart_sql.ask(error_question)
        
        # 即使SQL生成失败，仍应返回字典
        # self.assertIsInstance(error_result, dict)
        
    async def test_train(self):
        """测试train方法功能"""
        # 准备各种类型的训练数据
        training_data = [
            # DDL类型训练数据
            {
                'ddl': '''
                CREATE TABLE customers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                '''
            },
            {
                'ddl': """
                        CREATE TABLE users (
                            id                        SERIAL PRIMARY KEY, -- 用户唯一标识符，主键，自动递增
                            name                      VARCHAR,            -- 用户名（可选）
                            updated_at                TIMESTAMP(3) WITH TIME ZONE NOT NULL DEFAULT NOW(), -- 记录最后更新时间，默认为当前时间
                            created_at                TIMESTAMP(3) WITH TIME ZONE NOT NULL DEFAULT NOW(), -- 记录创建时间，默认为当前时间
                            email                     VARCHAR NOT NULL,   -- 用户邮箱，必填项，用于登录或联系
                            reset_password_token      VARCHAR,            -- 密码重置令牌（可选），用于密码重置功能
                            reset_password_expiration TIMESTAMP(3) WITH TIME ZONE, -- 密码重置令牌的过期时间（可选）
                            salt                      VARCHAR,            -- 密码加密时使用的盐值（可选）
                            hash                      VARCHAR,            -- 加密后的密码哈希值（可选）
                            login_attempts            NUMERIC DEFAULT 0,  -- 登录尝试次数，默认为 0，用于防止暴力破解
                            lock_until                TIMESTAMP(3) WITH TIME ZONE -- 账户锁定时间（可选），用于限制登录
                        );

                        -- 添加注释
                        COMMENT ON COLUMN users.id IS '用户唯一标识符，主键，自动递增';
                        COMMENT ON COLUMN users.name IS '用户名（可选）';
                        COMMENT ON COLUMN users.updated_at IS '记录最后更新时间，默认为当前时间';
                        COMMENT ON COLUMN users.created_at IS '记录创建时间，默认为当前时间';
                        COMMENT ON COLUMN users.email IS '用户邮箱，必填项，用于登录或联系';
                        COMMENT ON COLUMN users.reset_password_token IS '密码重置令牌（可选），用于密码重置功能';
                        COMMENT ON COLUMN users.reset_password_expiration IS '密码重置令牌的过期时间（可选）';
                        COMMENT ON COLUMN users.salt IS '密码加密时使用的盐值（可选）';
                        COMMENT ON COLUMN users.hash IS '加密后的密码哈希值（可选）';
                        COMMENT ON COLUMN users.login_attempts IS '登录尝试次数，默认为 0，用于防止暴力破解';
                        COMMENT ON COLUMN users.lock_until IS '账户锁定时间（可选），用于限制登录';
                    """
            },
            # 文档类型训练数据
            {
                'documentation': '客户表(customers)用于存储客户基本信息，包括姓名、邮箱等。'
            },
            # 问题-SQL对类型训练数据
            {
                'question': '查询所有客户的数量',
                'sql': 'SELECT COUNT(*) FROM customers;',
                'tags': ['count', 'customers']
            }
        ]
        
        # 执行训练
        result = await self.smart_sql.train(training_data)
        
        # 验证结果结构
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('failed', result)
        self.assertIn('status', result)
        
        # 验证训练成功
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(result['success']), 4)  # 应该有3条成功记录
        self.assertEqual(len(result['failed']), 0)   # 不应有失败记录
        
        # 验证各类型训练数据结果
        type_counts = {'ddl': 0, 'documentation': 0, 'question_sql': 0}
        for item in result['success']:
            self.assertIn('type', item)
            self.assertIn('id', item)
            type_counts[item['type']] += 1
        
        self.assertEqual(type_counts['ddl'], 2)
        self.assertEqual(type_counts['documentation'], 1)
        self.assertEqual(type_counts['question_sql'], 1)
        
        # 测试错误处理
        invalid_data = [{'invalid_key': 'invalid_value'}]
        error_result = await self.smart_sql.train(invalid_data)
        
        self.assertEqual(error_result['status'], 'completed')
        self.assertEqual(len(error_result['success']), 0)
        self.assertEqual(len(error_result['failed']), 1)
        
        # 测试单条数据（非列表）
        single_data = {
            'question': '查询姓名包含"张"的客户',
            'sql': "SELECT * FROM customers WHERE name LIKE '%张%';",
        }
        single_result = await self.smart_sql.train(single_data)
        
        self.assertEqual(single_result['status'], 'completed')
        self.assertEqual(len(single_result['success']), 1)
        self.assertEqual(single_result['success'][0]['type'], 'question_sql')


# 运行异步测试的辅助函数
async def run_async_test(test_name):
    """运行单个异步测试"""
    test_case = Text2SQLTestCase(test_name)
    try:
        await getattr(test_case, test_name)()
    finally:
        pass  # 清理工作已在tearDownClass中完成

def run_tests():
    """运行所有测试"""
    # 设置测试套件
    suite = unittest.TestSuite()
    
    # 添加同步测试
    suite.addTest(Text2SQLTestCase('test_create_instance'))
    
    # 运行测试套件
    unittest.TextTestRunner().run(suite)
    
    # 运行异步测试
    async_tests = [
        # 'test_generate_sql',
        # 'test_embedding_generation',
        # 'test_vector_store_retrieval',
        # 'test_middleware',
        # 'test_run_sql',
        # 'test_train',
        'test_ask'
    ]
    
    loop = asyncio.get_event_loop()
    for test_name in async_tests:
        print(f"\n运行测试: {test_name}")
        loop.run_until_complete(run_async_test(test_name))

if __name__ == "__main__":
    run_tests() 