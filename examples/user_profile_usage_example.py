"""
用户画像系统使用示例
展示如何集成和使用用户画像系统
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# 导入画像系统组件
from agents.airport_service.context_engineering.profile.profile_scheduler import (
    ProfileScheduler, ScheduleConfig, ProfileAPI
)
from agents.airport_service.context_engineering.profile.profile_extractor import ConversationData
from agents.airport_service.context_engineering.profile.operational_analytics import (
    OperationalAnalyticsEngine, AnalyticsFactory
)

class AirportCustomerServiceProfileSystem:
    """机场客服系统画像集成示例"""
    
    def __init__(self):
        # 配置画像系统
        self.config = ScheduleConfig(
            enable_session_extraction=True,
            enable_daily_aggregation=True,
            enable_deep_analysis=True,
            enable_operational_reports=True,
            daily_aggregation_time="01:00",
            deep_analysis_day=0,  # 周一
            deep_analysis_time="02:00",
            session_timeout_minutes=30,
            max_concurrent_extractions=10,
            batch_size=50
        )
        
        # 初始化系统组件
        self.scheduler = ProfileScheduler(self.config)
        self.api = ProfileAPI(self.scheduler)
        self.analytics = OperationalAnalyticsEngine()
        
        # 设置回调函数
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """设置系统回调函数"""
        
        async def on_session_end(conversation, result):
            """会话结束回调"""
            print(f"✅ 会话画像提取完成")
            print(f"   用户: {conversation.user_id}")
            print(f"   会话: {conversation.session_id}")
            print(f"   置信度: {result.confidence_score:.2f}")
            print(f"   处理时间: {result.processing_time:.2f}秒")
            
            # 这里可以添加业务逻辑，如：
            # - 发送画像更新通知
            # - 触发个性化推荐
            # - 更新用户标签
        
        async def on_daily_update(user_id, date, result):
            """每日更新回调"""
            print(f"📊 每日画像更新完成")
            print(f"   用户: {user_id}")
            print(f"   日期: {date}")
            print(f"   成功: {result.success}")
            
            # 这里可以添加业务逻辑，如：
            # - 更新用户分群
            # - 调整推荐策略
            # - 生成个性化内容
        
        async def on_deep_analysis(user_id, result):
            """深度分析回调"""
            print(f"🔍 深度画像分析完成")
            print(f"   用户: {user_id}")
            print(f"   置信度: {result.confidence_score:.2f}")
            print(f"   数据质量: {result.data_quality:.2f}")
            
            # 这里可以添加业务逻辑，如：
            # - 更新用户价值评级
            # - 调整服务策略
            # - 生成营销建议
        
        self.scheduler.add_session_end_callback(on_session_end)
        self.scheduler.add_daily_update_callback(on_daily_update)
        self.scheduler.add_deep_analysis_callback(on_deep_analysis)
    
    def start_system(self):
        """启动画像系统"""
        try:
            self.scheduler.start()
            print("🚀 用户画像系统已启动")
            print(f"📅 每日聚合时间: {self.config.daily_aggregation_time}")
            print(f"🔬 深度分析时间: 每周{self.config.deep_analysis_day} {self.config.deep_analysis_time}")
            print(f"⏱️  会话超时时间: {self.config.session_timeout_minutes}分钟")
        except Exception as e:
            print(f"❌ 系统启动失败: {str(e)}")
            raise
    
    def stop_system(self):
        """停止画像系统"""
        try:
            self.scheduler.stop()
            print("🛑 用户画像系统已停止")
        except Exception as e:
            print(f"❌ 系统停止失败: {str(e)}")
    
    async def handle_user_message(self, user_id: str, session_id: str, message: str, 
                                  source: str = "web", device: str = "pc", location: str = None):
        """处理用户消息并更新画像"""
        try:
            message_data = {
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat(),
                "technical_context": {
                    "source": source,
                    "device": device,
                    "location": location,
                    "ip": "127.0.0.1",  # 在实际应用中从请求中获取
                    "user_agent": "Mozilla/5.0..."  # 在实际应用中从请求中获取
                }
            }
            
            # 跟踪用户消息
            result = await self.api.track_message(user_id, session_id, message_data)
            
            if result["success"]:
                print(f"📝 用户消息已跟踪: {user_id}")
            else:
                print(f"❌ 消息跟踪失败: {result['error']}")
            
            return result
            
        except Exception as e:
            print(f"❌ 处理用户消息失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def handle_session_end(self, user_id: str, session_id: str):
        """处理会话结束"""
        try:
            result = await self.api.trigger_session_end(user_id, session_id)
            
            if result["success"]:
                print(f"✅ 会话结束处理完成: {session_id}")
            else:
                print(f"❌ 会话结束处理失败: {result['error']}")
            
            return result
            
        except Exception as e:
            print(f"❌ 会话结束处理失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_user_profile_summary(self, user_id: str):
        """获取用户画像摘要（模拟）"""
        # 在实际应用中，这里会从数据库查询用户画像
        return {
            "user_id": user_id,
            "traveler_type": "商旅人士",
            "user_role": "乘机人本人",
            "spending_power": "高价值客户",
            "loyalty_score": 0.85,
            "satisfaction_score": 0.88,
            "preferred_services": ["快速通道", "商务休息室", "优先值机"],
            "risk_level": "低",
            "last_updated": datetime.now().isoformat()
        }
    
    async def trigger_manual_analysis(self, user_id: str):
        """手动触发画像分析"""
        try:
            # 手动触发每日更新
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            daily_result = await self.api.manual_daily_update(user_id, yesterday)
            
            # 手动触发深度分析
            deep_result = await self.api.manual_deep_analysis(user_id, days=30)
            
            return {
                "daily_analysis": daily_result,
                "deep_analysis": deep_result
            }
            
        except Exception as e:
            print(f"❌ 手动分析失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def generate_operational_insights(self):
        """生成运营洞察"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 生成运营报告
            report = await self.analytics.generate_operational_report(today, "daily")
            
            # 生成管理层摘要
            summary = await self.analytics.generate_executive_summary(today)
            
            print("📈 运营洞察报告")
            print(f"总用户数: {report.total_users}")
            print(f"活跃用户: {report.active_users}")
            print(f"新增用户: {report.new_users}")
            print(f"平均满意度: {report.avg_satisfaction:.2f}")
            print(f"问题解决率: {report.resolution_rate:.2f}")
            print(f"系统健康度: {summary['overall_health_score']:.2f}")
            
            # 显示关键洞察
            print("\n💡 关键洞察:")
            for insight in report.key_insights[:3]:  # 显示前3个洞察
                print(f"- {insight.title}: {insight.description}")
            
            # 显示改进建议
            print("\n🎯 改进建议:")
            for rec in report.recommendations[:3]:  # 显示前3个建议
                print(f"- {rec}")
            
            return {
                "report": report,
                "summary": summary
            }
            
        except Exception as e:
            print(f"❌ 运营洞察生成失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_system_status(self):
        """获取系统状态"""
        try:
            status = self.api.get_system_status()
            
            print("🔧 系统状态")
            print(f"调度器运行: {status['running']}")
            print(f"活跃会话: {status['active_sessions']}")
            print(f"待处理: {status['pending_extractions']}")
            print(f"定时任务: {len(status['scheduled_jobs'])}个")
            
            return status
            
        except Exception as e:
            print(f"❌ 获取系统状态失败: {str(e)}")
            return {"success": False, "error": str(e)}


async def demo_scenario():
    """演示完整的使用场景"""
    print("=" * 60)
    print("🎯 机场智能客服用户画像系统演示")
    print("=" * 60)
    
    # 初始化系统
    profile_system = AirportCustomerServiceProfileSystem()
    
    try:
        # 启动系统
        profile_system.start_system()
        
        # 等待系统初始化
        await asyncio.sleep(1)
        
        print("\n📋 场景1: 用户咨询航班信息")
        user_id = "user_business_001"
        session_id = "session_20241201_001"
        
        # 模拟用户对话
        messages = [
            "我需要查询明天北京到上海的航班",
            "有没有上午10点左右的班次？",
            "我是金卡会员，可以使用快速通道吗？",
            "好的，帮我看下商务舱还有位置吗？",
            "谢谢，我已经了解了"
        ]
        
        for i, message in enumerate(messages):
            print(f"\n💬 用户消息 {i+1}: {message}")
            await profile_system.handle_user_message(
                user_id=user_id,
                session_id=session_id,
                message=message,
                source="wechat",
                device="mobile",
                location="北京"
            )
            await asyncio.sleep(0.5)  # 模拟消息间隔
        
        # 结束会话
        print(f"\n🔚 会话结束")
        await profile_system.handle_session_end(user_id, session_id)
        
        # 等待画像处理
        await asyncio.sleep(2)
        
        print("\n📋 场景2: 查看用户画像")
        profile = await profile_system.get_user_profile_summary(user_id)
        print(f"👤 用户画像: {json.dumps(profile, indent=2, ensure_ascii=False)}")
        
        print("\n📋 场景3: 手动触发分析")
        analysis_result = await profile_system.trigger_manual_analysis(user_id)
        print(f"🔍 分析结果: {analysis_result['daily_analysis']['success']}")
        
        print("\n📋 场景4: 运营洞察")
        await profile_system.generate_operational_insights()
        
        print("\n📋 场景5: 系统状态")
        profile_system.get_system_status()
        
        print("\n✅ 演示完成")
        
    except Exception as e:
        print(f"❌ 演示失败: {str(e)}")
    
    finally:
        # 停止系统
        profile_system.stop_system()


class ProfileSystemIntegration:
    """与现有系统集成的示例"""
    
    def __init__(self, profile_system: AirportCustomerServiceProfileSystem):
        self.profile_system = profile_system
    
    async def integrate_with_chat_system(self, chat_message_handler):
        """与聊天系统集成"""
        async def enhanced_handler(user_id, session_id, message, context):
            # 处理原始消息
            response = await chat_message_handler(user_id, session_id, message, context)
            
            # 更新用户画像
            await self.profile_system.handle_user_message(
                user_id=user_id,
                session_id=session_id,
                message=message,
                source=context.get("source", "web"),
                device=context.get("device", "pc"),
                location=context.get("location")
            )
            
            return response
        
        return enhanced_handler
    
    async def integrate_with_recommendation_system(self):
        """与推荐系统集成"""
        async def get_personalized_recommendations(user_id):
            # 获取用户画像
            profile = await self.profile_system.get_user_profile_summary(user_id)
            
            # 基于画像生成推荐
            recommendations = []
            
            if profile["traveler_type"] == "商旅人士":
                recommendations.extend([
                    "商务休息室使用指南",
                    "快速通道申请",
                    "会员积分查询"
                ])
            elif profile["traveler_type"] == "家庭出行":
                recommendations.extend([
                    "儿童陪伴服务",
                    "家庭安检通道",
                    "特殊餐食预定"
                ])
            
            return recommendations
        
        return get_personalized_recommendations


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_scenario())
