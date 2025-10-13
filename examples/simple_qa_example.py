#!/usr/bin/env python3
"""
灵活的Redis QA系统使用示例 - 支持图片和扩展字段
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text2qa.simple_redis_qa import create_simple_qa

async def main():
    """主函数"""
    print("=== 灵活的Redis QA系统示例 ===")
    
    try:
        # 创建QA系统（自动连接Redis）- 配置时间衰减和分数阈值
        qa = await create_simple_qa(
            host="localhost", 
            port=6379, 
            db=2,
            score_threshold=0.1,  # 分数阈值：低于0.1的结果不返回
            time_decay_factor=0.8  # 时间衰减：每天分数乘以0.8
        )
        print("✅ 连接Redis成功（分数阈值: 0.1, 时间衰减: 0.8/天）")
        
        try:
            # 1. 添加基本QA对（只有问题和答案）
            basic_qa_id = await qa.add_qa(
                question="什么是机器学习？",
                answer="机器学习是一种人工智能技术，通过算法让计算机自动学习和改进。"
            )
            print(f"✅ 添加基本QA对: {basic_qa_id}")
            
            # 2. 添加带标签的QA对
            tagged_qa_id = await qa.add_qa(
                question="Python是什么？",
                answer="Python是一种高级编程语言，语法简洁明了。",
                tags=["编程", "Python"]
            )
            print(f"✅ 添加带标签QA对: {tagged_qa_id}")
            
            # 3. 添加带图片的QA对
            image_qa_id = await qa.add_qa(
                question="如何安装Python？",
                answer="访问python.org下载安装包，按照向导安装即可。",
                tags=["Python", "安装"],
                images=["https://example.com/python-install-step1.png", 
                       "https://example.com/python-install-step2.png"]
            )
            print(f"✅ 添加带图片QA对: {image_qa_id}")
            
            # 4. 添加带扩展字段的QA对
            extended_qa_id = await qa.add_qa(
                question="Redis有什么优点？",
                answer="Redis具有高性能、支持多种数据结构、持久化等优点。",
                tags=["数据库", "Redis"],
                images=["https://example.com/redis-architecture.png"],
                difficulty="中级",
                category="数据库技术",
                author="技术专家",
                source_url="https://redis.io/docs"
            )
            print(f"✅ 添加扩展QA对: {extended_qa_id}")
            
            # 5. 批量添加复杂QA对
            complex_qa_pairs = [
                {
                    "question": "Docker容器和虚拟机有什么区别？",
                    "answer": "Docker容器更轻量级，共享宿主机内核；虚拟机有完整操作系统。",
                    "tags": ["Docker", "虚拟化"],
                    "images": ["https://example.com/docker-vs-vm.png"],
                    "difficulty": "高级",
                    "category": "DevOps"
                },
                {
                    "question": "什么是微服务架构？",
                    "answer": "微服务是将应用程序分解为独立、可部署的小服务的架构模式。",
                    "tags": ["架构", "微服务"],
                    "video_url": "https://example.com/microservices-intro.mp4",
                    "related_links": ["https://microservices.io", "https://martinfowler.com/microservices"]
                }
            ]
            
            batch_ids = await qa.add_qa_batch(complex_qa_pairs)
            print(f"✅ 批量添加了 {len(batch_ids)} 个复杂QA对")
            
            # 6. 搜索测试（只匹配问题字段，考虑时间衰减和分数阈值）
            # 注意：搜索使用Redis Search的真实相似度分数（BM25算法）+ 时间衰减
            print("\n=== 搜索测试 ===")
            
            # 搜索"机器学习"
            result1 = await qa.search_one("机器学习")
            if result1:
                print(f"🔍 搜索'机器学习': {result1['question']}")
                print(f"   答案: {result1['answer']}")
                if result1.get('images'):
                    print(f"   相关图片: {result1['images']}")
                if result1.get('extra_fields'):
                    print(f"   扩展字段: {result1['extra_fields']}")
            else:
                print("🔍 搜索'机器学习': 未找到满足阈值的结果")
            
            # 搜索"Docker"
            result2 = await qa.search_one("Docker")
            if result2:
                print(f"\n🔍 搜索'Docker': {result2['question']}")
                print(f"   标签: {result2.get('tags', [])}")
                if result2.get('extra_fields'):
                    print(f"   难度: {result2['extra_fields'].get('difficulty')}")
                    print(f"   分类: {result2['extra_fields'].get('category')}")
            else:
                print("\n🔍 搜索'Docker': 未找到满足阈值的结果")
            
            # 搜索Python相关
            result3 = await qa.search_one("Python")
            if result3:
                print(f"\n🔍 搜索'Python': {result3['question']}")
                if result3.get('images'):
                    print(f"   图片数量: {len(result3['images'])}")
            else:
                print("\n🔍 搜索'Python': 未找到满足阈值的结果")
            
            # 7. 获取完整QA对
            print(f"\n=== 获取完整数据 ===")
            full_qa = await qa.get_qa(extended_qa_id)
            if full_qa:
                print(f"📋 完整QA数据:")
                print(f"   问题: {full_qa['question']}")
                print(f"   答案: {full_qa['answer']}")
                print(f"   标签: {full_qa.get('tags', [])}")
                print(f"   图片: {full_qa.get('images', [])}")
                print(f"   扩展字段: {full_qa.get('extra_fields', {})}")
            
            # 8. 统计信息
            total = await qa.count_qa()
            print(f"\n📊 总共有 {total} 个QA对")
            
        finally:
            # 关闭连接
            await qa.close()
            print("✅ 连接已关闭")
    
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        print("请确保Redis服务正在运行: redis-server")

if __name__ == "__main__":
    asyncio.run(main())