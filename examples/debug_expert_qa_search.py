"""
专家QA检索调试工具
帮助排查为什么数据库中存在的记录检索不到的问题
"""
import asyncio
import sys
import os
from typing import List, Optional, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.airport_service.context_engineering.memory_manager import memory_manager


class ExpertQADebugger:
    """专家QA检索调试器"""
    
    def __init__(self):
        self.application_id = None
        
    async def initialize(self):
        """初始化记忆管理器"""
        try:
            await memory_manager.initialize()
            print("✅ 记忆管理器初始化成功")
            return True
        except Exception as e:
            print(f"❌ 记忆管理器初始化失败: {e}")
            return False
    
    async def debug_search_process(self, query: str, application_id: Optional[str] = None):
        """调试搜索过程"""
        print(f"\n🔍 调试搜索过程: '{query}'")
        print("="*80)
        
        # 步骤1: 直接调用memory_manager的search_expert_qa方法（无筛选）
        print("\n📋 步骤1: 直接调用memory_manager.search_expert_qa (无任何筛选)")
        try:
            raw_results = await memory_manager.search_expert_qa(
                query=query,
                application_id=None,  # 不进行任何筛选
                expert_id=None,
                tags=None,
                services=None,
                limit=100
            )
            print(f"   原始结果数量: {len(raw_results)}")
            if raw_results:
                for i, result in enumerate(raw_results[:5]):  # 只显示前5个
                    print(f"   结果 {i+1}:")
                    print(f"     问题: {result.get('question', '')[:50]}...")
                    print(f"     专家ID: {result.get('expert_id', '')}")
                    print(f"     应用ID: {result.get('application_id', '')}")
                    print(f"     相关度: {result.get('relevance_score', 0.0):.4f}")
                    print(f"     标签: {result.get('tags', '')}")
                    print(f"     服务: {result.get('services', '')}")
            else:
                print("   ❌ 没有找到任何结果")
        except Exception as e:
            print(f"   ❌ 错误: {e}")
        
        # 步骤2: 使用application_id筛选
        if application_id:
            print(f"\n📋 步骤2: 使用application_id筛选 ({application_id})")
            try:
                filtered_results = await memory_manager.search_expert_qa(
                    query=query,
                    application_id=application_id,
                    limit=100
                )
                print(f"   筛选后结果数量: {len(filtered_results)}")
                if filtered_results:
                    for i, result in enumerate(filtered_results[:3]):
                        print(f"   结果 {i+1}:")
                        print(f"     问题: {result.get('question', '')[:50]}...")
                        print(f"     相关度: {result.get('relevance_score', 0.0):.4f}")
                else:
                    print("   ❌ 应用ID筛选后没有结果")
            except Exception as e:
                print(f"   ❌ 错误: {e}")
        
        # 步骤3: 测试agent_memory中的函数
        print(f"\n📋 步骤3: 测试agent_memory.get_relevant_expert_qa_memories (默认score_limit=0.7)")
        try:
            from agents.airport_service.context_engineering.agent_memory import get_relevant_expert_qa_memories
            agent_results = await get_relevant_expert_qa_memories(
                query=query,
                application_id=application_id,
                score_limit=0.7  # 默认值
            )
            print(f"   agent_memory结果数量: {len(agent_results)}")
            if agent_results:
                for i, result in enumerate(agent_results[:3]):
                    print(f"   结果 {i+1}:")
                    print(f"     问题: {result.get('question', '')[:50]}...")
                    print(f"     相关度: {result.get('relevance_score', 0.0):.4f}")
            else:
                print("   ❌ agent_memory函数返回空结果")
        except Exception as e:
            print(f"   ❌ 错误: {e}")
        
        # 步骤4: 测试不同的score_limit值
        print(f"\n📋 步骤4: 测试不同的score_limit值")
        score_limits = [0.0, 0.1, 0.3, 0.5, 0.7, 0.8, 0.9]
        
        for score_limit in score_limits:
            try:
                from agents.airport_service.context_engineering.agent_memory import get_relevant_expert_qa_memories
                score_results = await get_relevant_expert_qa_memories(
                    query=query,
                    application_id=application_id,
                    score_limit=score_limit
                )
                print(f"   score_limit={score_limit}: {len(score_results)} 条结果")
                if score_results and len(score_results) > 0:
                    best_score = max(result.get('relevance_score', 0.0) for result in score_results)
                    print(f"     最高相关度: {best_score:.4f}")
            except Exception as e:
                print(f"   score_limit={score_limit}: 错误 - {e}")
    
    async def list_all_expert_qa(self, limit: int = 10):
        """列出所有专家QA记录"""
        print(f"\n📋 列出所有专家QA记录 (最多{limit}条)")
        print("="*80)
        
        try:
            # 使用get_expert_qa_list方法获取所有记录
            all_qa = await memory_manager.get_expert_qa_list(limit=limit)
            
            if not all_qa:
                print("❌ 数据库中没有任何专家QA记录")
                return
            
            print(f"✅ 找到 {len(all_qa)} 条专家QA记录:\n")
            
            for i, qa in enumerate(all_qa, 1):
                print(f"📋 记录 {i}:")
                print(f"   ID: {qa.get('memory_id', '')}")
                print(f"   问题: {qa.get('question', '')}")
                print(f"   答案: {qa.get('answer', '')[:100]}...")
                print(f"   专家ID: {qa.get('expert_id', '')}")
                print(f"   应用ID: {qa.get('application_id', '')}")
                print(f"   标签: {qa.get('tags', '')}")
                print(f"   服务: {qa.get('services', '')}")
                print(f"   创建时间: {qa.get('created_at', '')}")
                print("-" * 60)
        
        except Exception as e:
            print(f"❌ 列出专家QA记录时出错: {e}")
    
    async def test_specific_qa(self, memory_id: str):
        """测试特定QA记录的检索"""
        print(f"\n🎯 测试特定QA记录的检索: {memory_id}")
        print("="*80)
        
        try:
            # 先获取这条记录的详细信息
            all_qa = await memory_manager.get_expert_qa_list(limit=1000)
            target_qa = None
            
            for qa in all_qa:
                if qa.get('memory_id') == memory_id:
                    target_qa = qa
                    break
            
            if not target_qa:
                print(f"❌ 未找到ID为 {memory_id} 的记录")
                return
            
            print("📋 目标记录信息:")
            print(f"   问题: {target_qa.get('question', '')}")
            print(f"   答案: {target_qa.get('answer', '')[:100]}...")
            print(f"   专家ID: {target_qa.get('expert_id', '')}")
            print(f"   应用ID: {target_qa.get('application_id', '')}")
            print(f"   标签: {target_qa.get('tags', '')}")
            print(f"   服务: {target_qa.get('services', '')}")
            
            # 使用问题中的关键词进行搜索
            question = target_qa.get('question', '')
            if question:
                # 提取关键词
                keywords = [
                    question,  # 完整问题
                    question[:10],  # 前10个字符
                    question.split('？')[0] if '？' in question else question.split('?')[0],  # 去掉问号
                ]
                
                for keyword in keywords:
                    if keyword.strip():
                        print(f"\n🔍 使用关键词搜索: '{keyword}'")
                        await self.debug_search_process(
                            keyword, 
                            target_qa.get('application_id')
                        )
        
        except Exception as e:
            print(f"❌ 测试特定QA记录时出错: {e}")
    
    async def comprehensive_debug(self):
        """综合调试"""
        print("🚀 开始专家QA检索综合调试")
        print("="*80)
        
        # 初始化
        if not await self.initialize():
            return
        
        # 列出所有记录
        await self.list_all_expert_qa(20)
        
        # 交互式调试
        while True:
            print("\n" + "="*60)
            print("🔧 调试选项:")
            print("  1. 测试搜索查询")
            print("  2. 测试特定记录ID")
            print("  3. 重新列出所有记录")
            print("  4. 退出")
            
            try:
                choice = input("\n请选择操作 (1-4): ").strip()
                
                if choice == '1':
                    query = input("请输入搜索查询: ").strip()
                    if query:
                        app_id = input("请输入应用ID (直接回车跳过): ").strip() or None
                        await self.debug_search_process(query, app_id)
                
                elif choice == '2':
                    memory_id = input("请输入记录ID: ").strip()
                    if memory_id:
                        await self.test_specific_qa(memory_id)
                
                elif choice == '3':
                    await self.list_all_expert_qa(20)
                
                elif choice == '4':
                    break
                
                else:
                    print("❌ 无效选择，请输入1-4")
                    
            except KeyboardInterrupt:
                print("\n👋 调试已中断")
                break
            except Exception as e:
                print(f"❌ 调试过程中出错: {e}")
        
        print("👋 调试结束")


async def main():
    """主函数"""
    debugger = ExpertQADebugger()
    await debugger.comprehensive_debug()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
