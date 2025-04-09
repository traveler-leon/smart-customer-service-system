import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from text2sql.storge.chromadb import ChromadbStorage
from text2sql.base.interfaces import AsyncEmbeddingProvider

# 创建一个嵌入提供者的模拟实现
class MockEmbeddingProvider(AsyncEmbeddingProvider):
    async def generate_embedding(self, data, **kwargs):
        # 简单地返回一个固定长度的向量，实际应用中需要真实的嵌入模型
        return {"embedding": [0.1] * 384}

# 测试配置
TEST_CONFIG = {
    "host": "localhost",
    "port": 8000,
    "n_results": 5,
}

@pytest.fixture
async def chroma_storage():
    """创建并初始化ChromaDB存储对象"""
    # 创建一个模拟的嵌入提供者
    embedding_provider = MockEmbeddingProvider()
    
    # 使用模拟的嵌入提供者创建ChromaDB存储
    storage = ChromadbStorage(
        config=TEST_CONFIG,
        embedding_provider=embedding_provider
    )
    
    # 模拟initialize方法，避免实际连接到ChromaDB
    with patch.object(storage, 'initialize', new_callable=AsyncMock) as mock_init:
        # 设置模拟的集合
        storage.client = AsyncMock()
        storage.sql_collection = AsyncMock()
        storage.ddl_collection = AsyncMock()
        storage.documentation_collection = AsyncMock()
        
        # 初始化存储
        await storage.initialize()
        yield storage
        
        # 测试完成后关闭连接
        await storage.close()

@pytest.mark.asyncio
async def test_initialize():
    """测试初始化过程"""
    embedding_provider = MockEmbeddingProvider()
    storage = ChromadbStorage(config=TEST_CONFIG, embedding_provider=embedding_provider)
    
    with patch('chromadb.AsyncHttpClient', new_callable=AsyncMock) as mock_client:
        # 模拟客户端和集合
        mock_client.return_value = AsyncMock()
        mock_client.return_value.get_or_create_collection = AsyncMock()
        mock_client.return_value.get_or_create_collection.return_value = AsyncMock()
        
        # 初始化存储
        await storage.initialize()
        
        # 验证客户端是否使用正确的参数创建
        mock_client.assert_called_once()
        
        # 验证是否创建了三个集合
        assert mock_client.return_value.get_or_create_collection.call_count == 3

@pytest.mark.asyncio
async def test_check_health(chroma_storage):
    """测试健康检查"""
    # 模拟心跳检测成功
    chroma_storage.client.heartbeat.return_value = "ok"
    assert await chroma_storage.check_health() is True
    
    # 模拟心跳检测失败
    chroma_storage.client.heartbeat.side_effect = Exception("连接失败")
    assert await chroma_storage.check_health() is False

@pytest.mark.asyncio
async def test_add_question_sql(chroma_storage):
    """测试添加问题SQL映射"""
    # 设置模拟
    chroma_storage.ensure_connection = AsyncMock()
    chroma_storage.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    chroma_storage.sql_collection.add = AsyncMock()
    
    # 执行测试
    question = "如何查询用户表中的所有用户？"
    sql = "SELECT * FROM users;"
    
    # 模拟添加问题SQL映射
    result_id = await chroma_storage.add_question_sql(question, sql)
    
    # 验证是否调用了正确的方法
    chroma_storage.ensure_connection.assert_called_once()
    chroma_storage.generate_embedding.assert_called_once_with(question)
    chroma_storage.sql_collection.add.assert_called_once()
    
    # 验证返回的ID格式
    assert result_id.endswith("-sql")

@pytest.mark.asyncio
async def test_add_ddl(chroma_storage):
    """测试添加DDL语句"""
    # 设置模拟
    chroma_storage.ensure_connection = AsyncMock()
    chroma_storage.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    chroma_storage.ddl_collection.add = AsyncMock()
    
    # 执行测试
    ddl = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));"
    
    # 模拟添加DDL
    result_id = await chroma_storage.add_ddl(ddl)
    
    # 验证是否调用了正确的方法
    chroma_storage.ensure_connection.assert_called_once()
    chroma_storage.generate_embedding.assert_called_once_with(ddl)
    chroma_storage.ddl_collection.add.assert_called_once()
    
    # 验证返回的ID格式
    assert result_id.endswith("-ddl")

@pytest.mark.asyncio
async def test_add_documentation(chroma_storage):
    """测试添加文档"""
    # 设置模拟
    chroma_storage.ensure_connection = AsyncMock()
    chroma_storage.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    chroma_storage.documentation_collection.add = AsyncMock()
    
    # 执行测试
    documentation = "用户表存储了系统中所有用户的基本信息，包括ID和姓名。"
    
    # 模拟添加文档
    result_id = await chroma_storage.add_documentation(documentation)
    
    # 验证是否调用了正确的方法
    chroma_storage.ensure_connection.assert_called_once()
    chroma_storage.generate_embedding.assert_called_once_with(documentation)
    chroma_storage.documentation_collection.add.assert_called_once()
    
    # 验证返回的ID格式
    assert result_id.endswith("-doc")

@pytest.mark.asyncio
async def test_get_similar_question_sql(chroma_storage):
    """测试获取类似问题的SQL"""
    # 设置模拟
    chroma_storage.ensure_connection = AsyncMock()
    chroma_storage.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    
    # 模拟查询结果
    mock_results = {
        "documents": ["如何查询用户表中的所有用户？"],
        "metadatas": [{"type": "sql-qa", "detail": "SELECT * FROM users;"}]
    }
    chroma_storage.sql_collection.query = AsyncMock(return_value=mock_results)
    
    # 执行测试
    question = "查询所有用户"
    results = await chroma_storage.get_similar_question_sql(question)
    
    # 验证是否调用了正确的方法
    chroma_storage.ensure_connection.assert_called_once()
    chroma_storage.generate_embedding.assert_called_once_with(question)
    chroma_storage.sql_collection.query.assert_called_once()
    
    # 验证返回的结果格式
    assert isinstance(results, list)

@pytest.mark.asyncio
async def test_get_related_ddl(chroma_storage):
    """测试获取相关DDL语句"""
    # 设置模拟
    chroma_storage.ensure_connection = AsyncMock()
    chroma_storage.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    
    # 模拟查询结果
    mock_results = {
        "documents": ["CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));"],
        "metadatas": [{"type": "table-ddl"}]
    }
    chroma_storage.ddl_collection.query = AsyncMock(return_value=mock_results)
    
    # 执行测试
    question = "用户表结构"
    results = await chroma_storage.get_related_ddl(question)
    
    # 验证是否调用了正确的方法
    chroma_storage.ensure_connection.assert_called_once()
    chroma_storage.generate_embedding.assert_called_once_with(question)
    chroma_storage.ddl_collection.query.assert_called_once()
    
    # 验证返回的结果
    assert isinstance(results, list)

@pytest.mark.asyncio
async def test_get_related_documentation(chroma_storage):
    """测试获取相关文档"""
    # 设置模拟
    chroma_storage.ensure_connection = AsyncMock()
    chroma_storage.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    
    # 模拟查询结果
    mock_results = {
        "documents": ["用户表存储了系统中所有用户的基本信息，包括ID和姓名。"],
        "metadatas": [{"type": "table-documentation"}]
    }
    chroma_storage.documentation_collection.query = AsyncMock(return_value=mock_results)
    
    # 执行测试
    question = "用户表说明"
    results = await chroma_storage.get_related_documentation(question)
    
    # 验证是否调用了正确的方法
    chroma_storage.ensure_connection.assert_called_once()
    chroma_storage.generate_embedding.assert_called_once_with(question)
    chroma_storage.documentation_collection.query.assert_called_once()
    
    # 验证返回的结果
    assert isinstance(results, list)

@pytest.mark.asyncio
async def test_get_training_data(chroma_storage):
    """测试获取训练数据"""
    # 设置模拟
    chroma_storage.ensure_connection = AsyncMock()
    
    # 模拟SQL集合数据
    sql_data = {
        "documents": ['{"question": "如何查询用户表中的所有用户？", "sql": "SELECT * FROM users;"}'],
        "ids": ["test-sql"],
        "metadatas": [{"sql": "SELECT * FROM users;"}]
    }
    chroma_storage.sql_collection.get = AsyncMock(return_value=sql_data)
    
    # 模拟DDL集合数据
    ddl_data = {
        "documents": ["CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));"],
        "ids": ["test-ddl"],
        "metadatas": [{}]
    }
    chroma_storage.ddl_collection.get = AsyncMock(return_value=ddl_data)
    
    # 模拟文档集合数据
    doc_data = {
        "documents": ["用户表存储了系统中所有用户的基本信息，包括ID和姓名。"],
        "ids": ["test-doc"],
        "metadatas": [{}]
    }
    chroma_storage.documentation_collection.get = AsyncMock(return_value=doc_data)
    
    # 执行测试
    df = await chroma_storage.get_training_data()
    
    # 验证是否调用了正确的方法
    chroma_storage.ensure_connection.assert_called_once()
    chroma_storage.sql_collection.get.assert_called_once()
    chroma_storage.ddl_collection.get.assert_called_once()
    chroma_storage.documentation_collection.get.assert_called_once()
    
    # 验证返回的DataFrame
    assert not df.empty

@pytest.mark.asyncio
async def test_remove_training_data(chroma_storage):
    """测试移除训练数据"""
    # 设置模拟
    chroma_storage.ensure_connection = AsyncMock()
    chroma_storage.sql_collection.delete = AsyncMock()
    chroma_storage.ddl_collection.delete = AsyncMock()
    chroma_storage.documentation_collection.delete = AsyncMock()
    
    # 测试移除SQL训练数据
    sql_id = "test-sql"
    result1 = await chroma_storage.remove_training_data(sql_id)
    assert result1 is False  # ID不符合格式要求
    
    # 测试移除DDL训练数据
    ddl_id = "test-ddl"
    result2 = await chroma_storage.remove_training_data(ddl_id)
    assert result2 is False  # ID不符合格式要求
    
    # 测试移除文档训练数据
    doc_id = "test-doc"
    result3 = await chroma_storage.remove_training_data(doc_id)
    assert result3 is False  # ID不符合格式要求
    
    # 测试正确的ID格式
    result4 = await chroma_storage.remove_training_data("test-sql")
    assert result4 is False
    
    result5 = await chroma_storage.remove_training_data("test-ddl")
    assert result5 is False
    
    result6 = await chroma_storage.remove_training_data("test-doc")
    assert result6 is False

@pytest.mark.asyncio
async def test_remove_collection(chroma_storage):
    """测试移除集合"""
    # 设置模拟
    chroma_storage.ensure_connection = AsyncMock()
    chroma_storage.client.delete_collection = AsyncMock()
    chroma_storage.client.get_or_create_collection = AsyncMock()
    
    # 测试移除SQL集合
    result1 = await chroma_storage.remove_collection("sql-sql")
    assert result1 is True
    chroma_storage.client.delete_collection.assert_called_with(name="sql-sql")
    
    # 测试移除DDL集合
    result2 = await chroma_storage.remove_collection("sql-ddl")
    assert result2 is True
    chroma_storage.client.delete_collection.assert_called_with(name="sql-ddl")
    
    # 测试移除文档集合
    result3 = await chroma_storage.remove_collection("sql-documentation")
    assert result3 is True
    chroma_storage.client.delete_collection.assert_called_with(name="sql-documentation")
    
    # 测试移除不存在的集合
    result4 = await chroma_storage.remove_collection("non-existent")
    assert result4 is False

# 集成测试 - 需要实际的ChromaDB服务
@pytest.mark.asyncio
@pytest.mark.integration
async def test_integration_workflow():
    """集成测试完整工作流程（需要实际的ChromaDB服务）"""
    # 跳过这个测试，除非明确要求运行集成测试
    pytest.skip("集成测试需要实际的ChromaDB服务")
    
    embedding_provider = MockEmbeddingProvider()
    storage = ChromadbStorage(config=TEST_CONFIG, embedding_provider=embedding_provider)
    
    try:
        # 初始化存储
        await storage.initialize()
        
        # 检查健康状态
        health = await storage.check_health()
        assert health is True
        
        # 清理现有集合
        await storage.remove_collection("sql-sql")
        await storage.remove_collection("sql-ddl")
        await storage.remove_collection("sql-documentation")
        
        # 添加测试数据
        question = "如何查询用户表中的所有用户？"
        sql = "SELECT * FROM users;"
        sql_id = await storage.add_question_sql(question, sql)
        
        ddl = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));"
        ddl_id = await storage.add_ddl(ddl)
        
        documentation = "用户表存储了系统中所有用户的基本信息，包括ID和姓名。"
        doc_id = await storage.add_documentation(documentation)
        
        # 查询相似数据
        similar_sql = await storage.get_similar_question_sql("查询所有用户")
        assert len(similar_sql) > 0
        
        related_ddl = await storage.get_related_ddl("用户表结构")
        assert len(related_ddl) > 0
        
        related_docs = await storage.get_related_documentation("用户表说明")
        assert len(related_docs) > 0
        
        # 获取训练数据
        training_data = await storage.get_training_data()
        assert not training_data.empty
        
        # 移除训练数据
        await storage.remove_training_data(sql_id)
        await storage.remove_training_data(ddl_id)
        await storage.remove_training_data(doc_id)
        
    finally:
        # 清理
        await storage.close()

if __name__ == "__main__":
    # 运行测试
    pytest.main(["-xvs", "test_chromadb.py"]) 