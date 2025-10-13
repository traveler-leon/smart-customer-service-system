"""
交互式专家QA检索测试工具
支持循环输入问题，实时检索相关的专家QA内容
"""
import asyncio
import sys
import os
from typing import List, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.airport_service.context_engineering.agent_memory import (
    get_relevant_expert_qa_memories,
    AgentMemoryMixin
)
from agents.airport_service.context_engineering.memory_manager import memory_manager


class InteractiveExpertQATest:
    """交互式专家QA测试类"""
    
    def __init__(self):
        # self.application_id = "airport_service"
        # self.application_id = "机场主智能客服"
        self.application_id = None
        self.expert_id = None
        self.tags = None
        self.services = None
        self.score_limit = 0.0  # 改为更宽松的默认值，避免过度筛选
        self.limit = 100
        
    async def initialize(self):
        """初始化记忆管理器"""
        try:
            await memory_manager.initialize()
            print("✅ 记忆管理器初始化成功")
            return True
        except Exception as e:
            print(f"❌ 记忆管理器初始化失败: {e}")
            return False
    
    async def add_sample_expert_qa(self):
        """添加示例专家QA数据"""

        
        # 等待数据索引完成
        print("⏳ 等待数据索引完成...")
        await asyncio.sleep(3)
        print("✅ 数据索引完成")
        
    def display_settings(self):
        """显示当前设置"""
        print("\n" + "="*60)
        print("🔧 当前检索设置:")
        print(f"  应用ID: {self.application_id}")
        print(f"  专家ID筛选: {self.expert_id or '无'}")
        print(f"  标签筛选: {self.tags or '无'}")
        print(f"  服务筛选: {self.services or '无'}")
        print(f"  相关度阈值: {self.score_limit}")
        print(f"  返回数量限制: {self.limit}")
        print("="*60)
        
    def display_help(self):
        """显示帮助信息"""
        print("\n" + "="*60)
        print("📖 使用说明:")
        print("  直接输入问题                - 检索相关专家QA")
        print("  /set expert <expert_id>     - 设置专家ID筛选")
        print("  /set tags <tag1,tag2>       - 设置标签筛选")
        print("  /set services <svc1,svc2>   - 设置服务筛选")
        print("  /set score <0.0-1.0>        - 设置相关度阈值")
        print("  /set limit <数量>            - 设置返回数量限制")
        print("  /clear                      - 清除所有筛选条件")
        print("  /show                       - 显示当前设置")
        print("  /help                       - 显示此帮助")
        print("  /quit 或 /exit              - 退出程序")
        print("="*60)
        
    async def handle_command(self, user_input: str) -> bool:
        """处理命令，返回是否继续运行"""
        if user_input in ['/quit', '/exit']:
            return False
            
        elif user_input == '/help':
            self.display_help()
            
        elif user_input == '/show':
            self.display_settings()
            
        elif user_input == '/clear':
            self.expert_id = None
            self.tags = None
            self.services = None
            print("✅ 已清除所有筛选条件")
            
        elif user_input.startswith('/set '):
            await self.handle_set_command(user_input)
            
        else:
            await self.search_expert_qa(user_input)
            
        return True
        
    async def handle_set_command(self, command: str):
        """处理设置命令"""
        parts = command.split(' ', 2)
        if len(parts) < 3:
            print("❌ 设置命令格式错误，请使用 /set <参数> <值>")
            return
            
        param = parts[1].lower()
        value = parts[2].strip()
        
        if param == 'expert':
            self.expert_id = value if value.lower() != 'none' else None
            print(f"✅ 专家ID筛选已设置为: {self.expert_id}")
            
        elif param == 'tags':
            if value.lower() == 'none':
                self.tags = None
            else:
                self.tags = [tag.strip() for tag in value.split(',') if tag.strip()]
            print(f"✅ 标签筛选已设置为: {self.tags}")
            
        elif param == 'services':
            if value.lower() == 'none':
                self.services = None
            else:
                self.services = [svc.strip() for svc in value.split(',') if svc.strip()]
            print(f"✅ 服务筛选已设置为: {self.services}")
            
        elif param == 'score':
            try:
                score = float(value)
                if 0.0 <= score <= 1.0:
                    self.score_limit = score
                    print(f"✅ 相关度阈值已设置为: {self.score_limit}")
                else:
                    print("❌ 相关度阈值必须在 0.0-1.0 之间")
            except ValueError:
                print("❌ 相关度阈值必须是数字")
                
        elif param == 'limit':
            try:
                limit = int(value)
                if limit > 0:
                    self.limit = limit
                    print(f"✅ 返回数量限制已设置为: {self.limit}")
                else:
                    print("❌ 返回数量限制必须大于0")
            except ValueError:
                print("❌ 返回数量限制必须是整数")
                
        else:
            print(f"❌ 未知参数: {param}")
            print("支持的参数: expert, tags, services, score, limit")
    
    async def search_expert_qa(self, query: str):
        """检索专家QA"""
        if not query.strip():
            print("❌ 请输入有效的问题")
            return
            
        print(f"\n🔍 正在检索: '{query}'")
        print("-" * 60)
        
        try:
            # 使用 agent_memory 中的函数进行检索
            results = await get_relevant_expert_qa_memories(
                query=query,
                application_id=self.application_id,
                expert_id=self.expert_id,
                tags=self.tags,
                services=self.services,
                score_limit=self.score_limit,
                limit=self.limit
            )
            
            if not results:
                print("❌ 未找到相关的专家QA内容")
                print("💡 建议:")
                print("  - 尝试使用不同的关键词")
                print("  - 降低相关度阈值 (使用 /set score <值>)")
                print("  - 清除筛选条件 (使用 /clear)")
                return
                
            print(f"✅ 找到 {len(results)} 条相关内容:\n")
            
            for i, result in enumerate(results, 1):
                print(f"📋 结果 {i}:")
                print(f"   🤔 问题: {result['question']}")
                print(f"   💡 答案: {result['answer']}")
                print(f"   👨‍💼 专家: {result['expert_id']}")
                print(f"   🏷️  标签: {result['tags']}")
                print(f"   🔧 服务: {result['services']}")
                print(f"   📊 相关度: {result['relevance_score']:.3f}")
                print(f"   ⏰ 创建时间: {result['created_at']}")
                print("-" * 60)
                
        except Exception as e:
            print(f"❌ 检索过程中发生错误: {e}")
    
    async def run_interactive_test(self):
        """运行交互式测试"""
        print("🚀 启动交互式专家QA检索测试工具")
        print("="*60)
        
        # 初始化
        if not await self.initialize():
            return
            
        # 询问是否添加示例数据
        while True:
            add_sample = input("\n❓ 是否添加示例专家QA数据？(y/n): ").strip().lower()
            if add_sample in ['y', 'yes', '是']:
                await self.add_sample_expert_qa()
                break
            elif add_sample in ['n', 'no', '否']:
                print("⏭️  跳过添加示例数据")
                break
            else:
                print("❌ 请输入 y 或 n")
        
        # 显示帮助和设置
        self.display_help()
        self.display_settings()
        
        print("\n🎯 开始交互式检索测试 (输入 /help 查看帮助, /quit 退出)")
        print("="*60)
        
        # 主循环
        while True:
            try:
                user_input = input("\n💬 请输入问题或命令: ").strip()
                
                if not user_input:
                    print("❌ 输入不能为空")
                    continue
                    
                # 处理命令或检索
                should_continue = await self.handle_command(user_input)
                if not should_continue:
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"❌ 程序运行出错: {e}")
                continue
        
        print("👋 谢谢使用，再见！")


async def main():
    """主函数"""
    test_tool = InteractiveExpertQATest()
    await test_tool.run_interactive_test()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
