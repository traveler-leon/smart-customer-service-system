#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ChromadbStorage简单测试脚本
不依赖unittest.mock，使用简单的print语句测试基本功能
测试使用QwenEmbedding作为embedding支持
"""
import asyncio
import json
import sys

# 导入需要测试的类
from text2sql.storge.chromadb import ChromadbStorage
from text2sql.embedding.qwen_model import QwenEmbedding

# 测试配置
TEST_CONFIG = {
    "host": "116.198.252.1",
    "port": 8000,
    "n_results": 5,
    "hnsw_config": {
        "M": 16,                  # 每个节点的最大出边数
        "construction_ef": 100,   # 建立索引时考虑的邻居数
        "search_ef": 50,          # 查询时考虑的邻居数
        "space": "cosine"         # 向量空间距离计算方式
    }
}

# 通义千问embedding配置
QWEN_CONFIG = {
    "api_key": "sk-2e8c1dd4f75a44bf8114b337a5498a91",  # 请使用您的实际API密钥
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "embedding_model": "text-embedding-v3"
}

# 测试颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# 测试QwenEmbedding基本功能
async def test_qwen_embedding():
    print(f"{Colors.HEADER}测试QwenEmbedding基本功能{Colors.ENDC}")
    
    try:
        # 创建通义千问嵌入提供者
        print("创建通义千问嵌入提供者...")
        embedding_provider = QwenEmbedding(QWEN_CONFIG)
        
        # 测试生成嵌入
        print(f"{Colors.OKBLUE}1. 测试生成嵌入向量{Colors.ENDC}")
        text = "测试文本：这是用于测试嵌入功能的文本示例。"
        
        print(f"生成嵌入中...")
        embedding_result = await embedding_provider.generate_embedding(text)
        
        if embedding_result and "embedding" in embedding_result:
            embedding = embedding_result["embedding"]
            tokens_used = embedding_result.get("tokens_used", 0)
            print(f"嵌入生成成功: 维度={len(embedding)}, 使用tokens={tokens_used}")
            print(f"向量前5个值: {embedding[:5]}")
        else:
            print(f"{Colors.FAIL}嵌入生成失败{Colors.ENDC}")
            return False
            
        # 测试生成多个不同文本的嵌入
        print(f"{Colors.OKBLUE}2. 测试生成多个文本的嵌入向量{Colors.ENDC}")
        texts = [
            "用户表包含用户的基本信息",
            "订单表记录了用户的购买记录",
            "如何查询用户的所有订单?"
        ]
        
        for i, text in enumerate(texts):
            print(f"生成第{i+1}个文本的嵌入中...")
            result = await embedding_provider.generate_embedding(text)
            print(f"文本 {i+1} 嵌入生成成功: 维度={len(result['embedding'])}")
        
        # 测试嵌入相似度（手动计算余弦相似度）
        print(f"{Colors.OKBLUE}3. 测试嵌入向量的相似度{Colors.ENDC}")
        
        # 相似的文本
        similar_texts = [
            "如何查看所有用户的订单记录?",  # 与第3个文本相似
            "订单表中包含了什么信息?"      # 与第2个文本相似
        ]
        
        similar_embeddings = []
        for i, text in enumerate(similar_texts):
            print(f"生成相似文本{i+1}的嵌入中...")
            result = await embedding_provider.generate_embedding(text)
            similar_embeddings.append(result["embedding"])
        
        print("嵌入生成完成，实际使用时，可以将这些嵌入向量存入ChromaDB中")
        print("存入ChromaDB后，可以通过向量相似度搜索找到语义相似的文本")
        
    except Exception as e:
        print(f"{Colors.FAIL}测试过程中发生异常: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 关闭嵌入提供者
        if 'embedding_provider' in locals():
            print("关闭嵌入提供者...")
            await embedding_provider.close()
    
    print(f"{Colors.OKGREEN}QwenEmbedding基本功能测试通过！{Colors.ENDC}")
    return True

# 简化的ChromaDB连接测试
async def test_chromadb_connection():
    print(f"{Colors.HEADER}测试ChromaDB连接{Colors.ENDC}")
    
    try:
        # 创建通义千问嵌入提供者
        print("创建嵌入提供者...")
        embedding_provider = QwenEmbedding(QWEN_CONFIG)
        
        # 创建ChromaDB存储实例
        print("创建ChromaDB存储实例...")
        storage = ChromadbStorage(config=TEST_CONFIG, embedding_provider=embedding_provider)
        
        # 打印HNSW配置参数
        print(f"\nHNSW配置参数:")
        print(f"- similarity_metric: {storage.hnsw_config['space']}")
        print(f"- M: {storage.hnsw_config['M']} (对应 hnsw:M)")
        print(f"- construction_ef: {storage.hnsw_config['construction_ef']} (对应 hnsw:construction_ef)")
        print(f"- search_ef: {storage.hnsw_config['search_ef']} (对应 hnsw:search_ef)")
        print(f"- space: {storage.hnsw_config['space']} (对应 hnsw:space)")
        print(f"注意: ChromaDB要求使用hnsw:construction_ef和hnsw:search_ef作为参数名\n")
        
        # 尝试初始化连接
        print("尝试连接到ChromaDB服务器...")
        print(f"连接信息: 主机={TEST_CONFIG['host']}, 端口={TEST_CONFIG['port']}")
        
        try:
            print(f"{Colors.WARNING}注意: 这将尝试连接到真实的ChromaDB服务器{Colors.ENDC}")
            print(f"{Colors.WARNING}如果没有运行的ChromaDB服务器，这一步会失败{Colors.ENDC}")
            print("初始化连接...")
            await storage.initialize()
            print(f"{Colors.OKGREEN}成功连接到ChromaDB服务器!{Colors.ENDC}")
            
            # 检查健康状态
            print("检查ChromaDB健康状态...")
            health = await storage.check_health()
            if health:
                print(f"{Colors.OKGREEN}ChromaDB服务健康状态良好!{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}ChromaDB服务健康状态异常!{Colors.ENDC}")
                
            print("关闭ChromaDB连接...")
            await storage.close()
            
        except Exception as e:
            print(f"{Colors.FAIL}无法连接到ChromaDB服务器: {str(e)}{Colors.ENDC}")
            print("这是正常的，如果您没有运行ChromaDB服务器")
            print("可以通过以下命令启动ChromaDB服务器:")
            print("  docker run -p 8000:8000 ghcr.io/chroma-core/chroma:latest")
            print("或者按照ChromaDB文档在本地安装并运行服务")
        
    except Exception as e:
        print(f"{Colors.FAIL}测试过程中发生异常: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 关闭嵌入提供者
        if 'embedding_provider' in locals():
            await embedding_provider.close()
    
    print(f"{Colors.OKGREEN}ChromaDB连接测试完成!{Colors.ENDC}")
    return True

# 测试向ChromaDB添加数据的流程描述
def print_chromadb_workflow():
    print(f"{Colors.HEADER}ChromaDB工作流程说明{Colors.ENDC}")
    print(f"{Colors.OKBLUE}以下是使用ChromaDB和QwenEmbedding的典型流程:{Colors.ENDC}")
    print("1. 创建嵌入提供者 (QwenEmbedding)")
    print("2. 创建并初始化ChromaDB存储")
    print("3. 添加数据:")
    print("   - 添加SQL问题和答案")
    print("   - 添加DDL语句")
    print("   - 添加文档说明")
    print("4. 查询相似数据:")
    print("   - 查询相似SQL")
    print("   - 查询相关DDL")
    print("   - 查询相关文档")
    print("5. 关闭连接")
    
    print(f"\n{Colors.OKBLUE}ChromaDB集合参数配置说明:{Colors.ENDC}")
    print("根据最新的ChromaDB文档，创建集合时使用的HNSW参数格式如下:")
    print("- hnsw:M - 每个节点的最大出边数")
    print("- hnsw:construction_ef - 建立索引时考虑的邻居数")
    print("- hnsw:search_ef - 查询时考虑的邻居数")
    print("- hnsw:space - 向量空间距离计算方式 (cosine, l2, ip等)")
    print("\n配置示例:")
    print("""
    config = {
        "host": "116.198.252.1",
        "port": 8000,
        "hnsw_config": {
            "M": 16,
            "construction_ef": 100,
            "search_ef": 50,
            "space": "cosine"
        }
    }
    """)
    
    print(f"\n{Colors.OKBLUE}添加SQL问题的示例代码:{Colors.ENDC}")
    print("""
    # 创建嵌入提供者和存储
    embedding_provider = QwenEmbedding(config)
    storage = ChromadbStorage(config, embedding_provider)
    await storage.initialize()
    
    # 添加SQL问题和答案
    question = "如何查询用户表中的所有活跃用户？"
    sql = "SELECT * FROM users WHERE status = 'active';"
    sql_id = await storage.add_question_sql(question, sql)
    print(f"添加SQL成功，ID: {sql_id}")
    
    # 查询相似SQL
    query = "获取活跃用户"
    results = await storage.get_similar_question_sql(query)
    for result in results:
        print(f"问题: {result['question']}")
        print(f"SQL: {result['sql']}")
    """)
    
    print(f"\n{Colors.OKBLUE}ChromaDB在语义搜索中的优势:{Colors.ENDC}")
    print("- 基于嵌入向量的相似度搜索")
    print("- 支持语义匹配而非仅关键词匹配")
    print("- 可以找到表达相似但用词不同的问题")
    print("- 高效的向量检索算法，支持大规模数据")
    
    print(f"\n{Colors.OKGREEN}要运行实际测试，请确保ChromaDB服务器已启动，并更新配置信息{Colors.ENDC}")

# 测试ChromaDB添加功能-修改版
async def test_add_functions():
    print(f"{Colors.HEADER}测试ChromaDB添加功能{Colors.ENDC}")
    
    try:
        # 创建通义千问嵌入提供者
        # print("创建嵌入提供者...")
        embedding_provider = QwenEmbedding(QWEN_CONFIG)
        
        # # 创建ChromaDB存储实例
        # print("创建ChromaDB存储实例...")
        storage = ChromadbStorage(config=TEST_CONFIG, embedding_provider=embedding_provider)
        
        # # 初始化连接
        # print("初始化连接...")
        await storage.initialize()
        # print(f"{Colors.OKGREEN}成功连接到ChromaDB服务器!{Colors.ENDC}")
        
        # # 1. 测试添加问题SQL映射
        # print(f"\n{Colors.OKBLUE}1. 测试添加问题SQL映射{Colors.ENDC}")
        # question = "我只是下测试一下信息？"
        # sql = "SELECT name,gender FROM customers;"
        # print(f"添加问题: {question}")
        # print(f"对应SQL: {sql}")
        # sql_id = await storage.add_question_sql(question, sql)
        # print(f"{Colors.OKGREEN}添加问题SQL成功，ID: {sql_id}{Colors.ENDC}")
        
        # # 2. 测试添加DDL语句
        # print(f"\n{Colors.OKBLUE}2. 测试添加DDL语句{Colors.ENDC}")
        # ddl = "CREATE TABLE customers (id INT PRIMARY KEY, name VARCHAR(100));"
        # print(f"添加DDL: {ddl}")
        # ddl_id = await storage.add_ddl(ddl)
        # print(f"{Colors.OKGREEN}添加DDL成功，ID: {ddl_id}{Colors.ENDC}")
        
        # # 3. 测试添加文档 - 简化版本
        # print(f"\n{Colors.OKBLUE}3. 测试添加文档{Colors.ENDC}")
        # try:
        #     # 使用一个非常简单的文档内容
        #     documentation = "客户表基本信息"
        #     print(f"添加简单文档: {documentation}")
            
        #     # 先测试生成嵌入向量
        #     print("测试生成文档嵌入向量...")
        #     embedding = await storage.generate_embedding(documentation)
        #     print(f"嵌入向量生成成功，维度: {len(embedding)}")
            
        #     # 然后尝试添加文档
        #     print("尝试添加文档...")
        #     doc_id = await storage.add_documentation(documentation)
        #     print(f"{Colors.OKGREEN}添加文档成功，ID: {doc_id}{Colors.ENDC}")
        # except Exception as doc_error:
        #     print(f"{Colors.FAIL}添加文档时出错: {str(doc_error)}{Colors.ENDC}")
        #     import traceback
        #     traceback.print_exc()
        
        # 测试添加后的验证 - 可选
        print(f"\n{Colors.OKBLUE}4. 验证添加的数据{Colors.ENDC}")
        try:
            print("获取训练数据...")
            data = await storage.get_training_data()
            print(f"获取到 {len(data)} 条训练数据")
            print(f"数据类型分布: {data['training_data_type'].value_counts().to_dict()}")
        except Exception as data_error:
            print(f"{Colors.FAIL}获取训练数据时出错: {str(data_error)}{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.FAIL}测试过程中发生异常: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 关闭连接
        if 'storage' in locals():
            print("\n关闭ChromaDB连接...")
            await storage.close()
        if 'embedding_provider' in locals():
            await embedding_provider.close()
    
    print(f"{Colors.OKGREEN}ChromaDB添加功能测试完成!{Colors.ENDC}")
    return True

# 测试ChromaDB查询功能
async def test_query_functions():
    print(f"{Colors.HEADER}测试ChromaDB查询功能{Colors.ENDC}")
    
    try:
        # 创建通义千问嵌入提供者
        print("创建嵌入提供者...")
        embedding_provider = QwenEmbedding(QWEN_CONFIG)
        
        # 创建ChromaDB存储实例
        print("创建ChromaDB存储实例...")
        storage = ChromadbStorage(config=TEST_CONFIG, embedding_provider=embedding_provider)
        
        # 初始化连接
        print("初始化连接...")
        await storage.initialize()
        print(f"{Colors.OKGREEN}成功连接到ChromaDB服务器!{Colors.ENDC}")
        
        # 1. 测试查询类似问题SQL
        print(f"\n{Colors.OKBLUE}1. 测试查询类似问题SQL{Colors.ENDC}")
        query = "查询客户信息"
        print(f"查询问题: {query}")
        similar_questions = await storage.get_similar_question_sql(query)
        print(f"找到 {len(similar_questions)} 个类似问题:f{similar_questions}")
        for i, question in enumerate(similar_questions):
            print(f"  结果 {i+1}:")
            if isinstance(question, dict) and "question" in question and "sql" in question:
                print(f"    问题: {question['question']}")
                print(f"    SQL: {question['sql']}")
            else:
                print(f"    {question}")
                
        # 2. 测试查询相关DDL
        print(f"\n{Colors.OKBLUE}2. 测试查询相关DDL{Colors.ENDC}")
        query = "客户表结构"
        print(f"查询内容: {query}")
        related_ddls = await storage.get_related_ddl(query)
        print(f"找到 {len(related_ddls)} 个相关DDL")
        for i, ddl in enumerate(related_ddls):
            print(f"  结果 {i+1}: {ddl[:100]}...")
            
        # 3. 测试查询相关文档
        print(f"\n{Colors.OKBLUE}3. 测试查询相关文档{Colors.ENDC}")
        query = "客户表字段说明"
        print(f"查询内容: {query}")
        related_docs = await storage.get_related_documentation(query)
        print(f"找到 {len(related_docs)} 个相关文档")
        for i, doc in enumerate(related_docs):
            print(f"  结果 {i+1}: {doc[:100]}...")
            
    except Exception as e:
        print(f"{Colors.FAIL}测试过程中发生异常: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 关闭连接
        if 'storage' in locals():
            print("\n关闭ChromaDB连接...")
            await storage.close()
        if 'embedding_provider' in locals():
            await embedding_provider.close()
    
    print(f"{Colors.OKGREEN}ChromaDB查询功能测试完成!{Colors.ENDC}")
    return True

# 主函数
async def main():
    print(f"{Colors.BOLD}开始简化版ChromadbStorage测试 (使用QwenEmbedding){Colors.ENDC}")
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="测试QwenEmbedding与ChromaDB功能")
    parser.add_argument("--connect", action="store_true", help="测试ChromaDB连接")
    parser.add_argument("--workflow", action="store_true", help="显示ChromaDB工作流程")
    parser.add_argument("--add", action="store_true", help="测试ChromaDB添加功能")
    parser.add_argument("--query", action="store_true", help="测试ChromaDB查询功能")
    args = parser.parse_args()
    
    success = True
    
    try:      
        # 测试QwenEmbedding功能
        # print("\n" + "="*50)
        # print("测试QwenEmbedding生成嵌入向量")
        # print("="*50)
        # basic_test_success = await test_qwen_embedding()
        # success = success and basic_test_success
        
        # 测试ChromaDB连接
        if args.connect:
            print("\n" + "="*50)
            print("测试ChromaDB连接")
            print("="*50)
            connect_test_success = await test_chromadb_connection()
            success = success and connect_test_success
        
        # 测试ChromaDB添加功能
        if args.add:
            print("\n" + "="*50)
            print("测试ChromaDB添加功能")
            print("="*50)
            add_test_success = await test_add_functions()
            success = success and add_test_success
            
        # 测试ChromaDB查询功能
        if args.query:
            print("\n" + "="*50)
            print("测试ChromaDB查询功能")
            print("="*50)
            query_test_success = await test_query_functions()
            success = success and query_test_success
        
        # 显示ChromaDB工作流程
        if args.workflow or not (args.connect or args.add or args.query):
            print("\n" + "="*50)
            print("ChromaDB工作流程说明")
            print("="*50)
            print_chromadb_workflow()
            
        if success:
            print(f"\n{Colors.BOLD}{Colors.OKGREEN}测试成功完成！{Colors.ENDC}")
        else:
            print(f"\n{Colors.BOLD}{Colors.FAIL}测试失败！{Colors.ENDC}")
            sys.exit(1)
    except Exception as e:
        print(f"{Colors.FAIL}测试过程中发生异常: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# 执行主函数
if __name__ == "__main__":
    asyncio.run(main()) 