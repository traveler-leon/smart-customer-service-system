"""
用户画像提取使用示例
基于 memory_manager 和 TrustCall 的画像提取流程
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta

# 导入记忆管理器
from agents.airport_service.context_engineering.memory_manager import memory_manager

logger = logging.getLogger(__name__)

async def demo_profile_extraction():
    """演示完整的画像提取流程"""
    
    print("=" * 60)
    print("🎯 机场智能客服用户画像提取演示")
    print("=" * 60)
    
    # 模拟参数
    application_id = "airport_service"
    user_id = "user_business_001"
    run_id = "session_20241201_001"
    
    try:
        # 初始化记忆管理器
        await memory_manager.initialize()
        print("✅ 记忆管理器初始化完成")
        
        # ====================== 第一步：会话画像提取 ======================
        print(f"\n📋 步骤1: 提取会话画像")
        print(f"   应用ID: {application_id}")
        print(f"   用户ID: {user_id}")
        print(f"   会话ID: {run_id}")
        
        # 触发会话画像提取
        session_result = await memory_manager.trigger_session_profile_extraction(
            application_id=application_id,
            user_id=user_id,
            run_id=run_id
        )
        
        if session_result and session_result.get("success"):
            print("✅ 会话画像提取成功")
            print(f"   旅客类型: {session_result.get('traveler_type')}")
            print(f"   用户角色: {session_result.get('user_role')}")
            print(f"   置信度: {session_result.get('confidence_score', 0):.2f}")
        else:
            print("❌ 会话画像提取失败")
            if session_result:
                print(f"   错误: {session_result.get('error', '未知错误')}")
        
        # ====================== 第二步：每日画像聚合 ======================
        print(f"\n📋 步骤2: 每日画像聚合")
        
        # 模拟当天日期
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 触发每日画像聚合
        daily_result = await memory_manager.trigger_daily_profile_aggregation(
            user_id=user_id,
            date=today
        )
        
        if daily_result and daily_result.get("success"):
            print("✅ 每日画像聚合成功")
            print(f"   日期: {daily_result.get('date')}")
            print(f"   会话数: {daily_result.get('sessions_count', 0)}")
            print(f"   主要语言: {daily_result.get('dominant_language')}")
            print(f"   平均满意度: {daily_result.get('avg_satisfaction', 0):.2f}")
        else:
            print("❌ 每日画像聚合失败")
            if daily_result:
                print(f"   错误: {daily_result.get('error', '未知错误')}")
        
        # ====================== 第三步：深度洞察分析 ======================
        print(f"\n📋 步骤3: 深度洞察分析")
        
        # 触发深度洞察分析（分析最近30天）
        deep_result = await memory_manager.trigger_deep_insight_analysis(
            user_id=user_id,
            days=30
        )
        
        if deep_result and deep_result.get("success"):
            print("✅ 深度洞察分析成功")
            print(f"   分析周期: {deep_result.get('analysis_period')}")
            print(f"   旅客类型: {deep_result.get('traveler_type')}")
            print(f"   消费能力: {deep_result.get('spending_power')}")
            print(f"   客户价值: {deep_result.get('customer_value', 0):.2f}")
            print(f"   流失风险: {deep_result.get('retention_risk', 0):.2f}")
            print(f"   画像置信度: {deep_result.get('confidence', 0):.2f}")
        else:
            print("❌ 深度洞察分析失败")
            if deep_result:
                print(f"   错误: {deep_result.get('error', '未知错误')}")
        
        print(f"\n✅ 画像提取演示完成")
        
    except Exception as e:
        print(f"❌ 演示失败: {str(e)}")

async def demo_batch_profile_extraction():
    """演示批量画像提取"""
    
    print("\n" + "=" * 60)
    print("🔄 批量画像提取演示")
    print("=" * 60)
    
    application_id = "airport_service"
    
    # 模拟多个用户的会话
    user_sessions = [
        {"user_id": "user_business_001", "run_id": "session_001"},
        {"user_id": "user_leisure_002", "run_id": "session_002"},
        {"user_id": "user_family_003", "run_id": "session_003"},
    ]
    
    try:
        # 批量提取会话画像
        print("📋 批量提取会话画像...")
        
        for session in user_sessions:
            result = await memory_manager.trigger_session_profile_extraction(
                application_id=application_id,
                user_id=session["user_id"],
                run_id=session["run_id"]
            )
            
            if result and result.get("success"):
                print(f"✅ {session['user_id']} - 会话画像提取成功")
            else:
                print(f"❌ {session['user_id']} - 会话画像提取失败")
        
        # 批量每日聚合
        print("\n📋 批量每日画像聚合...")
        today = datetime.now().strftime("%Y-%m-%d")
        
        for session in user_sessions:
            result = await memory_manager.trigger_daily_profile_aggregation(
                user_id=session["user_id"],
                date=today
            )
            
            if result and result.get("success"):
                print(f"✅ {session['user_id']} - 每日画像聚合成功")
            else:
                print(f"❌ {session['user_id']} - 每日画像聚合失败")
        
        print(f"\n✅ 批量画像提取完成")
        
    except Exception as e:
        print(f"❌ 批量处理失败: {str(e)}")

async def demo_conversation_history_retrieval():
    """演示对话历史获取"""
    
    print("\n" + "=" * 60)
    print("📚 对话历史获取演示")
    print("=" * 60)
    
    try:
        # 获取特定用户的对话历史
        application_id = "airport_service"
        user_id = "user_business_001"
        run_id = "session_20241201_001"
        
        print(f"📋 获取对话历史")
        print(f"   应用ID: {application_id}")
        print(f"   用户ID: {user_id}")
        print(f"   会话ID: {run_id}")
        
        # 通过 memory_manager 获取对话历史
        conversation_history = await memory_manager.get_conversation_history(
            application_id=application_id,
            user_id=user_id,
            run_id=run_id,
            limit=10
        )
        
        if conversation_history:
            print(f"✅ 获取到 {len(conversation_history)} 条对话记录")
            
            # 显示前几条对话
            for i, conv in enumerate(conversation_history[:3], 1):
                print(f"\n   对话 {i}:")
                print(f"   用户: {conv.get('query', '')[:50]}...")
                print(f"   助手: {conv.get('response', '')[:50]}...")
                print(f"   时间: {conv.get('created_at', '')}")
        else:
            print("❌ 未找到对话历史")
        
    except Exception as e:
        print(f"❌ 对话历史获取失败: {str(e)}")

async def demo_profile_query():
    """演示画像查询"""
    
    print("\n" + "=" * 60)
    print("🔍 用户画像查询演示")
    print("=" * 60)
    
    try:
        user_id = "user_business_001"
        
        print(f"📋 查询用户画像: {user_id}")
        
        # 查询用户画像
        user_profile = await memory_manager.get_user_profile(user_id)
        
        if user_profile:
            print("✅ 获取到用户画像")
            print(f"   用户ID: {user_profile.user_id}")
            print(f"   最后更新: {user_profile.last_updated}")
            print(f"   数据来源: {user_profile.extraction_source}")
            print(f"   画像数据: {json.dumps(user_profile.profile_data, ensure_ascii=False, indent=2)}")
        else:
            print("❌ 未找到用户画像")
        
    except Exception as e:
        print(f"❌ 画像查询失败: {str(e)}")

class ProfileExtractionPipeline:
    """画像提取流水线"""
    
    def __init__(self):
        self.memory_manager = memory_manager
    
    async def run_session_extraction_pipeline(
        self,
        application_id: str,
        user_id: str,
        run_id: str
    ):
        """运行会话画像提取流水线"""
        try:
            # 第一步：提取会话画像
            session_result = await self.memory_manager.trigger_session_profile_extraction(
                application_id=application_id,
                user_id=user_id,
                run_id=run_id
            )
            
            # 第二步：如果是当天最后一次会话，触发每日聚合
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 检查是否还有其他活跃会话（实际应用中需要实现）
            # 这里简化为直接触发每日聚合
            daily_result = await self.memory_manager.trigger_daily_profile_aggregation(
                user_id=user_id,
                date=today
            )
            
            # 第三步：如果满足条件，触发深度分析
            # 例如：每周或每月定期触发
            current_day = datetime.now().weekday()
            if current_day == 0:  # 周一
                deep_result = await self.memory_manager.trigger_deep_insight_analysis(
                    user_id=user_id,
                    days=30
                )
            else:
                deep_result = None
            
            return {
                "session_extraction": session_result,
                "daily_aggregation": daily_result,
                "deep_analysis": deep_result
            }
            
        except Exception as e:
            logger.error(f"画像提取流水线失败: {str(e)}")
            return None

    async def run_scheduled_extraction(self):
        """运行定时画像提取"""
        try:
            # 获取需要处理的用户列表（实际应用中从数据库获取）
            users_to_process = ["user_001", "user_002", "user_003"]
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 批量处理每日聚合
            for user_id in users_to_process:
                try:
                    result = await self.memory_manager.trigger_daily_profile_aggregation(
                        user_id=user_id,
                        date=today
                    )
                    
                    if result and result.get("success"):
                        print(f"✅ {user_id} 每日聚合完成")
                    else:
                        print(f"❌ {user_id} 每日聚合失败")
                        
                except Exception as e:
                    print(f"❌ {user_id} 处理异常: {str(e)}")
            
            # 周一执行深度分析
            if datetime.now().weekday() == 0:
                for user_id in users_to_process:
                    try:
                        result = await self.memory_manager.trigger_deep_insight_analysis(
                            user_id=user_id,
                            days=30
                        )
                        
                        if result and result.get("success"):
                            print(f"✅ {user_id} 深度分析完成")
                        else:
                            print(f"❌ {user_id} 深度分析失败")
                            
                    except Exception as e:
                        print(f"❌ {user_id} 深度分析异常: {str(e)}")
            
        except Exception as e:
            print(f"❌ 定时提取失败: {str(e)}")

async def main():
    """主函数 - 运行所有演示"""
    
    # 演示1: 基础画像提取流程
    await demo_profile_extraction()
    
    # 演示2: 批量画像提取
    await demo_batch_profile_extraction()
    
    # 演示3: 对话历史获取
    await demo_conversation_history_retrieval()
    
    # 演示4: 画像查询
    await demo_profile_query()
    
    # 演示5: 画像提取流水线
    print("\n" + "=" * 60)
    print("🔄 画像提取流水线演示")
    print("=" * 60)
    
    pipeline = ProfileExtractionPipeline()
    
    # 模拟会话结束后触发画像提取
    pipeline_result = await pipeline.run_session_extraction_pipeline(
        application_id="airport_service",
        user_id="user_business_001",
        run_id="session_latest"
    )
    
    if pipeline_result:
        print("✅ 画像提取流水线执行完成")
        print(f"   会话提取: {'成功' if pipeline_result['session_extraction'] and pipeline_result['session_extraction'].get('success') else '失败'}")
        print(f"   每日聚合: {'成功' if pipeline_result['daily_aggregation'] and pipeline_result['daily_aggregation'].get('success') else '失败'}")
        print(f"   深度分析: {'成功' if pipeline_result['deep_analysis'] and pipeline_result['deep_analysis'].get('success') else '跳过'}")
    else:
        print("❌ 画像提取流水线执行失败")

if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
