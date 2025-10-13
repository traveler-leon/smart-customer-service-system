"""
专家QA检索方法使用示例
演示如何使用新添加的search_expert_qa方法进行专家QA检索
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.airport_service.context_engineering.memory_manager import memory_manager


async def demo_expert_qa_search():
    """演示专家QA检索功能"""
    
    # 初始化记忆管理器
    await memory_manager.initialize()
    print("记忆管理器已初始化")
    
    # 示例1: 添加几个专家QA对
    print("\n=== 添加示例专家QA对 ===")
    
    qa_pairs = [
        {
            "question": "航班延误了怎么办？",
            "answer": "如果您的航班延误，我们将为您提供以下帮助：1. 免费改签至下一班可用航班 2. 如延误超过4小时，提供餐食补贴 3. 如需过夜，提供酒店住宿",
            "expert_id": "expert_001",
            "application_id": "airport_service",
            "metadata": {
                "tags": "航班延误,改签,补偿",
                "services": "航班服务,客户服务",
                "images": ""
            }
        },
        {
            "question": "如何办理值机手续？",
            "answer": "您可以通过以下方式办理值机：1. 网上值机：航班起飞前24小时开放 2. 手机APP值机 3. 机场自助值机设备 4. 人工柜台值机",
            "expert_id": "expert_002", 
            "application_id": "airport_service",
            "metadata": {
                "tags": "值机,登机,手续",
                "services": "值机服务,登机服务",
                "images": ""
            }
        },
        {
            "question": "行李托运有什么规定？",
            "answer": "行李托运规定如下：1. 经济舱免费托运20kg 2. 商务舱免费托运30kg 3. 超重费用按每公斤收费 4. 禁止携带易燃易爆物品",
            "expert_id": "expert_001",
            "application_id": "airport_service", 
            "metadata": {
                "tags": "行李托运,重量限制,费用",
                "services": "行李服务",
                "images": ""
            }
        }
    ]
    
    # 添加专家QA对
    for qa in qa_pairs:
        try:
            memory_id = await memory_manager.add_expert_qa(
                question=qa["question"],
                answer=qa["answer"],
                expert_id=qa["expert_id"],
                application_id=qa["application_id"],
                metadata=qa["metadata"]
            )
            print(f"添加专家QA成功: {memory_id} - {qa['question'][:20]}...")
        except Exception as e:
            print(f"添加专家QA失败: {e}")
    
    # 等待一下让数据索引完成
    await asyncio.sleep(2)
    
    # 示例2: 基本检索
    print("\n=== 基本检索测试 ===")
    
    search_queries = [
        "我的航班晚点了",
        "怎么办理登机",
        "行李超重怎么办",
        "机场服务"
    ]
    
    for query in search_queries:
        print(f"\n查询: '{query}'")
        results = await memory_manager.search_expert_qa(
            query=query,
            limit=3
        )
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. [相关度: {result['relevance_score']:.3f}] {result['question']}")
                print(f"     答案: {result['answer'][:50]}...")
                print(f"     专家: {result['expert_id']}")
        else:
            print("  未找到相关结果")
    
    # 示例3: 带筛选条件的检索
    print("\n=== 带筛选条件的检索 ===")
    
    # 按专家ID筛选
    print("\n按专家ID筛选 (expert_001):")
    results = await memory_manager.search_expert_qa(
        query="服务",
        expert_id="expert_001",
        limit=5
    )
    
    for result in results:
        print(f"  - {result['question']} (专家: {result['expert_id']})")
    
    # 按应用ID筛选
    print("\n按应用ID筛选 (airport_service):")
    results = await memory_manager.search_expert_qa(
        query="办理",
        application_id="airport_service",
        limit=5
    )
    
    for result in results:
        print(f"  - {result['question']} (应用: {result['application_id']})")
    
    # 按标签筛选
    print("\n按标签筛选 (包含'值机'标签):")
    results = await memory_manager.search_expert_qa(
        query="手续",
        tags=["值机"],
        limit=5
    )
    
    for result in results:
        print(f"  - {result['question']} (标签: {result['tags']})")
    
    # 按服务筛选  
    print("\n按服务筛选 (包含'行李服务'):")
    results = await memory_manager.search_expert_qa(
        query="规定",
        services=["行李服务"],
        limit=5
    )
    
    for result in results:
        print(f"  - {result['question']} (服务: {result['services']})")
    
    # 示例4: 综合筛选
    print("\n=== 综合筛选测试 ===")
    
    print("查询航班相关问题，专家expert_001，应用airport_service:")
    results = await memory_manager.search_expert_qa(
        query="航班",
        application_id="airport_service",
        expert_id="expert_001",
        limit=5
    )
    
    for result in results:
        print(f"  - {result['question']}")
        print(f"    相关度: {result['relevance_score']:.3f}")
        print(f"    专家: {result['expert_id']}")
        print(f"    应用: {result['application_id']}")
        print(f"    标签: {result['tags']}")
        print()
    
    # 示例5: 显示详细结果结构
    print("\n=== 详细结果结构 ===")
    
    results = await memory_manager.search_expert_qa(
        query="延误",
        limit=1
    )
    
    if results:
        result = results[0]
        print("完整结果结构:")
        for key, value in result.items():
            if key == 'metadata':
                print(f"  {key}: {type(value)} (包含详细元数据)")
            else:
                print(f"  {key}: {value}")


async def demo_comparison_with_conversation_search():
    """对比专家QA检索和对话检索的区别"""
    
    print("\n" + "="*50)
    print("对比专家QA检索和对话检索")
    print("="*50)
    
    query = "航班延误"
    
    # 专家QA检索
    print(f"\n专家QA检索结果 (查询: '{query}'):")
    expert_results = await memory_manager.search_expert_qa(
        query=query,
        limit=3
    )
    
    for i, result in enumerate(expert_results, 1):
        print(f"  {i}. [QA] {result['question']}")
        print(f"     答案: {result['answer'][:60]}...")
        print(f"     相关度: {result['relevance_score']:.3f}")
    
    # 对话检索
    print(f"\n对话检索结果 (查询: '{query}'):")
    conversation_results = await memory_manager.search_conversations(
        query=query,
        limit=3
    )
    
    for i, result in enumerate(conversation_results, 1):
        print(f"  {i}. [对话] {result['query']}")
        print(f"     回答: {result['response'][:60]}...")
        print(f"     相关度: {result['relevance_score']:.3f}")
    
    print(f"\n专家QA结果数量: {len(expert_results)}")
    print(f"对话结果数量: {len(conversation_results)}")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_expert_qa_search())
    asyncio.run(demo_comparison_with_conversation_search())
