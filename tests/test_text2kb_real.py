"""
知识库检索模块实际测试文件
直接连接实际API进行测试，不使用模拟数据
使用pytest和pytest-asyncio进行异步测试
"""

import asyncio
import sys
import os
import json
import tracemalloc
import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime

# 启用tracemalloc来避免内存分配跟踪警告
tracemalloc.start()

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text2kb import retrieve_from_kb, kb_retrieve
from text2kb.config import KB_ADDRESS, KB_API_KEY
from text2kb.retrieval import get_dataset_id


# 测试固定装置
@pytest.fixture(scope="module")
def test_config():
    """返回测试配置"""
    return {
        "address": KB_ADDRESS,
        "api_key": KB_API_KEY,
        "dataset_names": ["济南机场知识库"],
        "test_questions": [
            "可以携带刀具吗?"
        ]
    }


@pytest.fixture(scope="module")
def results_dir():
    """创建并返回结果目录"""
    dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


@pytest.mark.asyncio
async def test_list_datasets(test_config):
    """测试获取所有可用知识库列表"""
    print(f"\n{'='*50}")
    print("测试获取所有可用知识库列表")
    print(f"{'='*50}")
    
    address = test_config["address"]
    api_key = test_config["api_key"]
    
    try:
        # 构建API URL
        base_url = f"http://{address}/api/v1/datasets"
        
        # 设置查询参数
        params = {
            "page": 1,
            "page_size": 100,
            "orderby": "create_time"
        }
        
        # 设置请求头
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # 发送请求
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, headers=headers) as response:
                assert response.status == 200, f"API请求失败，状态码: {response.status}"
                
                data = await response.json()
                print(f"成功获取知识库列表，共 {len(data['data'])} 个知识库:")
                
                for i, dataset in enumerate(data['data']):
                    print(f"\n知识库 {i+1}:")
                    print(f"  ID: {dataset['id']}")
                    print(f"  名称: {dataset['name']}")
                    print(f"  描述: {dataset.get('description', '无')}")
                    print(f"  创建时间: {dataset.get('create_time', '未知')}")
                    print('-' * 40)
                
                # 确保至少返回了一个知识库
                assert len(data['data']) > 0, "知识库列表为空"
    
    except Exception as e:
        print(f"测试出错: {e}")
        pytest.fail(f"测试出错: {e}")


@pytest.mark.asyncio
async def test_dataset_access(test_config):
    """测试能否访问各个知识库"""
    print(f"\n{'='*50}")
    print("测试知识库访问")
    print(f"{'='*50}")
    
    address = test_config["address"]
    api_key = test_config["api_key"]
    dataset_names = test_config["dataset_names"]
    
    success_count = 0
    
    for name in dataset_names:
        print(f"\n检查知识库: 【{name}】")
        
        # 获取数据集ID
        dataset_id = await get_dataset_id(
            address, 
            name, 
            api_key
        )
        
        if dataset_id:
            print(f"✅ 成功访问知识库: {name}")
            print(f"  数据集ID: {dataset_id}")
            success_count += 1
        else:
            print(f"❌ 无法访问知识库: {name}")
    
    # 确保至少有一个知识库可以访问
    assert success_count > 0, "没有任何知识库可以访问"


@pytest.mark.asyncio
async def test_retrieval_basic(test_config, results_dir):
    """测试基本的知识库检索功能"""
    # 保存测试结果的文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"retrieval_results_{timestamp}.txt")
    
    address = test_config["address"]
    api_key = test_config["api_key"]
    dataset_names = test_config["dataset_names"]
    test_questions = test_config["test_questions"]
    
    with open(results_file, "w", encoding="utf-8") as f:
        f.write(f"知识库检索测试结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")
        
        for dataset_name in dataset_names:
            print(f"\n{'='*50}")
            print(f"测试知识库: 【{dataset_name}】")
            print(f"{'='*50}")
            
            f.write(f"知识库: {dataset_name}\n")
            f.write("-"*80 + "\n\n")
            
            # 检查是否可以访问该知识库
            dataset_id = await get_dataset_id(address, dataset_name, api_key)
            if not dataset_id:
                print(f"❌ 无法访问知识库: {dataset_name}，跳过测试")
                f.write(f"无法访问知识库: {dataset_name}，跳过测试\n\n")
                continue
            
            for question in test_questions:
                print(f"\n测试问题: 【{question}】")
                f.write(f"问题: {question}\n")
                
                # 从知识库中检索信息
                results = await retrieve_from_kb(
                    question,
                    dataset_name,
                    address,
                    api_key,
                    top_k=3  # 使用更大的top_k值进行测试
                )
                
                if results:
                    print(f"找到 {len(results)} 条检索结果:")
                    f.write(f"找到 {len(results)} 条结果:\n")
                    
                    # 打印每条结果
                    for i, result in enumerate(results):
                        content = result['content']
                        similarity = result['similarity']
                        is_low_similarity = result['low_similarity']
                        
                        print(f"\n【结果 {i+1}】")
                        print(f"相似度: {similarity:.4f} {'[低相似度]' if is_low_similarity else ''}")
                        
                        if len(content) > 500:
                            print(f"{content[:500]}...\n(内容已截断，总长度: {len(content)}字符)")
                        else:
                            print(content)
                        print('-' * 40)
                        
                        # 写入文件
                        f.write(f"\n结果 {i+1}:\n")
                        f.write(f"相似度: {similarity:.4f} {'[低相似度]' if is_low_similarity else ''}\n")
                        f.write(f"{content}\n")
                        f.write('-' * 40 + '\n')
                    
                    # 验证结果不为空
                    assert len(results) > 0, "检索结果为空列表"
                    for result in results:
                        assert len(result['content']) > 0, "检索结果内容为空"
                else:
                    print("⚠️ 未找到结果")
                    f.write("未找到结果\n")
                
                f.write("\n" + "="*40 + "\n\n")
            
            f.write("\n" + "="*80 + "\n\n")
    
    print(f"\n测试结果已保存到: {results_file}")


@pytest.mark.asyncio
async def test_langchain_tool(test_config, results_dir):
    """测试LangChain工具集成"""
    # 保存测试结果的文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"langchain_tool_results_{timestamp}.txt")
    
    address = test_config["address"]
    api_key = test_config["api_key"]
    dataset_names = test_config["dataset_names"]
    test_questions = test_config["test_questions"]
    
    with open(results_file, "w", encoding="utf-8") as f:
        f.write(f"LangChain工具测试结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")
        
        # 使用第一个可访问的知识库
        dataset_name = None
        for name in dataset_names:
            dataset_id = await get_dataset_id(address, name, api_key)
            if dataset_id:
                dataset_name = name
                break
        
        if not dataset_name:
            print("❌ 无法访问任何知识库，跳过测试")
            f.write("无法访问任何知识库，跳过测试\n")
            pytest.skip("无法访问任何知识库")
            return
        
        print(f"\n{'='*50}")
        print(f"使用LangChain工具测试 - 知识库: 【{dataset_name}】")
        print(f"{'='*50}")
        
        f.write(f"知识库: {dataset_name}\n")
        f.write("-"*80 + "\n\n")
        
        for i, question in enumerate(test_questions):
            print(f"\n测试问题 {i+1}: 【{question}】")
            f.write(f"问题 {i+1}: {question}\n\n")
            
            # 调用LangChain工具
            result = await kb_retrieve.ainvoke({
                "question": question,
                "dataset_name": dataset_name
            })
            
            # 验证结果
            assert isinstance(result, str), "工具返回结果不是字符串"
            
            # 打印结果
            print("【工具返回结果】:")
            print('-' * 40)
            if len(result) > 1000:
                print(f"{result[:1000]}...\n(结果已截断，总长度: {len(result)}字符)")
            else:
                print(result)
            print('-' * 40)
            
            # 写入文件
            f.write("工具返回结果:\n")
            f.write(result + "\n")
            f.write('-' * 80 + '\n\n')
    
    print(f"\n测试结果已保存到: {results_file}")


@pytest.mark.asyncio
async def test_performance(test_config):
    """测试知识库检索性能"""
    print(f"\n{'='*50}")
    print("知识库检索性能测试")
    print(f"{'='*50}")
    
    address = test_config["address"]
    api_key = test_config["api_key"]
    dataset_names = test_config["dataset_names"]
    test_questions = test_config["test_questions"]
    
    # 使用第一个可访问的知识库
    dataset_name = None
    for name in dataset_names:
        dataset_id = await get_dataset_id(address, name, api_key)
        if dataset_id:
            dataset_name = name
            break
    
    if not dataset_name:
        print("❌ 无法访问任何知识库，跳过测试")
        pytest.skip("无法访问任何知识库")
        return
    
    question = test_questions[0]  # 使用第一个问题进行测试
    
    print(f"知识库: 【{dataset_name}】")
    print(f"问题: 【{question}】")
    print(f"运行 5 次检索，测量平均响应时间...")
    
    total_time = 0
    result_counts = []
    
    for i in range(5):
        start_time = datetime.now()
        
        # 从知识库中检索信息
        results = await retrieve_from_kb(
            question,
            dataset_name,
            address,
            api_key,
            top_k=15  # 使用更大的top_k值进行测试
        )
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        total_time += elapsed
        result_counts.append(len(results))
        
        print(f"  测试 {i+1}: 检索到 {len(results)} 条结果，耗时 {elapsed:.2f} 秒")
    
    avg_time = total_time / 5
    print(f"\n平均响应时间: {avg_time:.2f} 秒")
    print(f"结果数量: {result_counts}")
    
    # 验证性能指标
    assert avg_time < 10, f"平均响应时间 {avg_time:.2f} 秒超过10秒，性能不佳"


# 直接运行此文件时的主入口
if __name__ == "__main__":
    # 在Windows上设置事件循环策略
    import platform
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    print("\n==== 运行知识库检索模块实际API测试 ====")
    print("提示: 推荐使用 pytest 命令运行此测试文件")
    print("例如: pytest -xvs tests/test_text2kb_real.py")
    
    # 如果直接运行此文件，调用pytest运行测试
    import pytest
    sys.exit(pytest.main(["-xvs", __file__])) 