"""
优化后的用户画像调度系统
重构原有profile_scheduler.py，提供更清晰的调度架构
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .user_profile_models import ProfileUpdateResult
from .profile_extractor import create_profile_extractor
from .operational_analytics import OperationalAnalyticsEngine

logger = logging.getLogger(__name__)

@dataclass
class ScheduleConfig:
    """调度配置"""
    enable_session_extraction: bool = True
    enable_daily_aggregation: bool = True
    enable_deep_analysis: bool = True
    enable_operational_reports: bool = True
    
    # 调度时间配置
    daily_aggregation_time: str = "01:00"  # 每日凌晨1点
    deep_analysis_day: int = 0  # 周一
    deep_analysis_time: str = "02:00"  # 凌晨2点
    
    # 触发条件配置
    session_timeout_minutes: int = 30  # 会话超时时间
    min_deep_analysis_days: int = 7  # 深度分析最少需要的天数
    
    # 并发控制
    max_concurrent_extractions: int = 10
    batch_size: int = 50

@dataclass
class ConversationData:
    """对话数据"""
    session_id: str
    user_id: str
    messages: List[Dict[str, Any]]
    start_time: datetime
    end_time: Optional[datetime] = None
    technical_context: Dict[str, Any] = None

class ProfileScheduler:
    """优化后的用户画像调度器"""
    
    def __init__(self, config: ScheduleConfig = None, llm_client = None):
        """
        初始化用户画像调度器
        
        Args:
            config: 调度配置
            llm_client: 可选的 LLM 客户端实例，传递给画像提取器
        """
        self.config = config or ScheduleConfig()
        self.scheduler = AsyncIOScheduler()
        self.profile_extractor = create_profile_extractor(llm_client)
        self.analytics_engine = OperationalAnalyticsEngine()
        
        # 活跃会话跟踪
        self.active_sessions: Dict[str, datetime] = {}
        self.pending_extractions: Dict[str, ConversationData] = {}
        
        # 并发控制
        self.extraction_semaphore = asyncio.Semaphore(self.config.max_concurrent_extractions)
        
        # 回调函数
        self.session_end_callbacks: List[Callable] = []
        self.daily_update_callbacks: List[Callable] = []
        self.deep_analysis_callbacks: List[Callable] = []

    def start(self):
        """启动调度器"""
        try:
            if self.config.enable_daily_aggregation:
                self._schedule_daily_aggregation()
            
            if self.config.enable_deep_analysis:
                self._schedule_deep_analysis()
            
            if self.config.enable_operational_reports:
                self._schedule_operational_reports()
            
            # 启动会话超时检查
            self._schedule_session_timeout_check()
            
            self.scheduler.start()
            logger.info("用户画像调度器已启动")
            
        except Exception as e:
            logger.error(f"调度器启动失败: {str(e)}")
            raise

    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown()
            logger.info("用户画像调度器已停止")
        except Exception as e:
            logger.error(f"调度器停止失败: {str(e)}")

    def _schedule_daily_aggregation(self):
        """调度每日聚合任务"""
        hour, minute = map(int, self.config.daily_aggregation_time.split(':'))
        trigger = CronTrigger(hour=hour, minute=minute)
        
        self.scheduler.add_job(
            self._run_daily_aggregation,
            trigger=trigger,
            id='daily_aggregation',
            name='每日用户画像聚合',
            max_instances=1,
            replace_existing=True
        )
        
        logger.info(f"已调度每日聚合任务，执行时间：{self.config.daily_aggregation_time}")

    def _schedule_deep_analysis(self):
        """调度深度分析任务"""
        hour, minute = map(int, self.config.deep_analysis_time.split(':'))
        trigger = CronTrigger(
            day_of_week=self.config.deep_analysis_day,
            hour=hour,
            minute=minute
        )
        
        self.scheduler.add_job(
            self._run_deep_analysis,
            trigger=trigger,
            id='deep_analysis',
            name='用户深度画像分析',
            max_instances=1,
            replace_existing=True
        )
        
        logger.info(f"已调度深度分析任务，执行时间：每周{self.config.deep_analysis_day} {self.config.deep_analysis_time}")

    def _schedule_operational_reports(self):
        """调度运营报告任务"""
        # 每日报告
        daily_trigger = CronTrigger(hour=23, minute=0)
        self.scheduler.add_job(
            self._generate_daily_report,
            trigger=daily_trigger,
            id='daily_report',
            name='每日运营报告',
            max_instances=1,
            replace_existing=True
        )
        
        # 周报告
        weekly_trigger = CronTrigger(day_of_week=6, hour=8, minute=0)  # 周日早上8点
        self.scheduler.add_job(
            self._generate_weekly_report,
            trigger=weekly_trigger,
            id='weekly_report',
            name='周运营报告',
            max_instances=1,
            replace_existing=True
        )
        
        logger.info("已调度运营报告任务")

    def _schedule_session_timeout_check(self):
        """调度会话超时检查"""
        trigger = IntervalTrigger(minutes=5)  # 每5分钟检查一次
        
        self.scheduler.add_job(
            self._check_session_timeouts,
            trigger=trigger,
            id='session_timeout_check',
            name='会话超时检查',
            max_instances=1,
            replace_existing=True
        )

    async def track_session_activity(self, user_id: str, session_id: str, message_data: Dict[str, Any]):
        """跟踪会话活动"""
        try:
            session_key = f"{user_id}:{session_id}"
            self.active_sessions[session_key] = datetime.now()
            
            # 更新或创建会话数据
            if session_key not in self.pending_extractions:
                self.pending_extractions[session_key] = ConversationData(
                    session_id=session_id,
                    user_id=user_id,
                    messages=[],
                    start_time=datetime.now(),
                    technical_context=message_data.get('technical_context', {})
                )
            
            # 添加消息到会话数据
            self.pending_extractions[session_key].messages.append(message_data)
            
            logger.debug(f"跟踪会话活动: {session_key}")
            
        except Exception as e:
            logger.error(f"会话活动跟踪失败: {str(e)}")

    async def trigger_session_end(self, user_id: str, session_id: str):
        """手动触发会话结束"""
        try:
            session_key = f"{user_id}:{session_id}"
            
            if session_key in self.pending_extractions:
                conversation = self.pending_extractions[session_key]
                conversation.end_time = datetime.now()
                
                # 异步处理画像提取
                asyncio.create_task(self._process_session_extraction(conversation))
                
                # 清理跟踪
                self.active_sessions.pop(session_key, None)
                self.pending_extractions.pop(session_key, None)
                
                logger.info(f"手动触发会话结束: {session_key}")
            
        except Exception as e:
            logger.error(f"手动触发会话结束失败: {str(e)}")

    async def _check_session_timeouts(self):
        """检查会话超时"""
        try:
            current_time = datetime.now()
            timeout_threshold = timedelta(minutes=self.config.session_timeout_minutes)
            timeout_sessions = []
            
            for session_key, last_activity in self.active_sessions.items():
                if current_time - last_activity > timeout_threshold:
                    timeout_sessions.append(session_key)
            
            # 处理超时会话
            for session_key in timeout_sessions:
                if session_key in self.pending_extractions:
                    conversation = self.pending_extractions[session_key]
                    conversation.end_time = current_time
                    
                    # 异步处理画像提取
                    asyncio.create_task(self._process_session_extraction(conversation))
                    
                    logger.info(f"会话超时触发画像提取: {session_key}")
                
                # 清理跟踪
                self.active_sessions.pop(session_key, None)
                self.pending_extractions.pop(session_key, None)
            
        except Exception as e:
            logger.error(f"会话超时检查失败: {str(e)}")

    async def _process_session_extraction(self, conversation: ConversationData):
        """处理单次会话画像提取"""
        async with self.extraction_semaphore:
            try:
                if not self.config.enable_session_extraction:
                    return
                
                # 转换对话数据格式
                conversation_history = []
                for msg in conversation.messages:
                    conversation_history.append({
                        'role': msg.get('role', 'user'),
                        'query': msg.get('content', ''),
                        'response': msg.get('response', ''),
                        'created_at': msg.get('timestamp', datetime.now().isoformat()),
                        'metadata': conversation.technical_context
                    })
                
                # 提取会话画像
                result = await self.profile_extractor.extract_session_profile(
                    application_id="airport_service",
                    user_id=conversation.user_id,
                    run_id=conversation.session_id,
                    conversation_history=conversation_history
                )
                
                # 执行回调
                for callback in self.session_end_callbacks:
                    try:
                        await callback(conversation, result)
                    except Exception as e:
                        logger.error(f"会话结束回调执行失败: {str(e)}")
                
                logger.info(f"会话画像提取完成: {conversation.user_id}:{conversation.session_id}")
                
            except Exception as e:
                logger.error(f"会话画像提取失败: {str(e)}")

    async def _run_daily_aggregation(self):
        """运行每日聚合任务"""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            # 获取需要聚合的用户列表
            users_to_process = await self._get_active_users_for_date(yesterday)
            
            logger.info(f"开始每日聚合任务，日期：{yesterday}，用户数：{len(users_to_process)}")
            
            # 批量处理
            for i in range(0, len(users_to_process), self.config.batch_size):
                batch = users_to_process[i:i + self.config.batch_size]
                
                # 并发处理批次
                tasks = [
                    self._process_daily_aggregation(user_id, yesterday)
                    for user_id in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 记录结果
                success_count = sum(1 for r in results if isinstance(r, ProfileUpdateResult) and r.success)
                error_count = len(results) - success_count
                
                logger.info(f"批次处理完成，成功：{success_count}，失败：{error_count}")
            
            logger.info(f"每日聚合任务完成，日期：{yesterday}")
            
        except Exception as e:
            logger.error(f"每日聚合任务失败: {str(e)}")

    async def _process_daily_aggregation(self, user_id: str, date: str) -> ProfileUpdateResult:
        """处理单个用户的每日聚合"""
        async with self.extraction_semaphore:
            try:
                # 获取用户在指定日期的会话画像
                session_profiles = await self._get_session_profiles_for_user_date(user_id, date)
                
                if not session_profiles:
                    return ProfileUpdateResult(
                        user_id=user_id,
                        update_type="daily",
                        success=False,
                        error_message="没有找到会话画像数据"
                    )
                
                # 聚合每日画像
                daily_profile = await self.profile_extractor.extract_daily_profile(
                    user_id=user_id,
                    date=date,
                    session_profiles=session_profiles
                )
                
                if daily_profile:
                    # 执行回调
                    for callback in self.daily_update_callbacks:
                        try:
                            await callback(user_id, date, daily_profile)
                        except Exception as e:
                            logger.error(f"每日更新回调执行失败: {str(e)}")
                    
                    return ProfileUpdateResult(
                        user_id=user_id,
                        update_type="daily",
                        success=True,
                        confidence_score=0.8,
                        processing_time=1.0
                    )
                else:
                    return ProfileUpdateResult(
                        user_id=user_id,
                        update_type="daily",
                        success=False,
                        error_message="每日画像聚合失败"
                    )
                
            except Exception as e:
                logger.error(f"用户每日聚合失败 {user_id}: {str(e)}")
                return ProfileUpdateResult(
                    user_id=user_id,
                    update_type="daily",
                    success=False,
                    error_message=str(e)
                )

    async def _run_deep_analysis(self):
        """运行深度分析任务"""
        try:
            # 获取需要深度分析的用户列表
            users_to_analyze = await self._get_users_for_deep_analysis()
            
            logger.info(f"开始深度分析任务，用户数：{len(users_to_analyze)}")
            
            # 批量处理
            for i in range(0, len(users_to_analyze), self.config.batch_size):
                batch = users_to_analyze[i:i + self.config.batch_size]
                
                tasks = [
                    self._process_deep_analysis(user_id)
                    for user_id in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                success_count = sum(1 for r in results if isinstance(r, ProfileUpdateResult) and r.success)
                error_count = len(results) - success_count
                
                logger.info(f"深度分析批次完成，成功：{success_count}，失败：{error_count}")
            
            logger.info("深度分析任务完成")
            
        except Exception as e:
            logger.error(f"深度分析任务失败: {str(e)}")

    async def _process_deep_analysis(self, user_id: str) -> ProfileUpdateResult:
        """处理单个用户的深度分析"""
        async with self.extraction_semaphore:
            try:
                # 获取用户的每日画像数据（最近30天）
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                daily_profiles = await self._get_daily_profiles_for_user_period(
                    user_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
                )
                
                if len(daily_profiles) < self.config.min_deep_analysis_days:
                    return ProfileUpdateResult(
                        user_id=user_id,
                        update_type="deep_insight",
                        success=False,
                        error_message=f"数据不足，需要至少{self.config.min_deep_analysis_days}天数据"
                    )
                
                # 深度洞察分析
                insight_profile = await self.profile_extractor.extract_insight_profile(
                    user_id=user_id,
                    daily_profiles=daily_profiles,
                    analysis_period=f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                )
                
                if insight_profile:
                    # 执行回调
                    for callback in self.deep_analysis_callbacks:
                        try:
                            await callback(user_id, insight_profile)
                        except Exception as e:
                            logger.error(f"深度分析回调执行失败: {str(e)}")
                    
                    return ProfileUpdateResult(
                        user_id=user_id,
                        update_type="deep_insight",
                        success=True,
                        confidence_score=insight_profile.profile_confidence,
                        data_quality=insight_profile.data_quality_score,
                        processing_time=2.5
                    )
                else:
                    return ProfileUpdateResult(
                        user_id=user_id,
                        update_type="deep_insight",
                        success=False,
                        error_message="深度洞察分析失败"
                    )
                
            except Exception as e:
                logger.error(f"用户深度分析失败 {user_id}: {str(e)}")
                return ProfileUpdateResult(
                    user_id=user_id,
                    update_type="deep_insight",
                    success=False,
                    error_message=str(e)
                )

    async def _generate_daily_report(self):
        """生成每日报告"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            report = await self.analytics_engine.generate_operational_report(today, "daily")
            
            logger.info(f"每日报告已生成: {report.report_id}")
            
        except Exception as e:
            logger.error(f"每日报告生成失败: {str(e)}")

    async def _generate_weekly_report(self):
        """生成周报告"""
        try:
            # 计算本周日期范围
            now = datetime.now()
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=6)
            period = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
            
            report = await self.analytics_engine.generate_operational_report(period, "weekly")
            
            logger.info(f"周报告已生成: {report.report_id}")
            
        except Exception as e:
            logger.error(f"周报告生成失败: {str(e)}")

    # 数据获取方法（需要连接实际数据库）
    async def _get_active_users_for_date(self, date: str) -> List[str]:
        """获取指定日期的活跃用户列表"""
        # 模拟数据
        return [f"user_{i}" for i in range(1, 21)]  # 返回20个用户

    async def _get_users_for_deep_analysis(self) -> List[str]:
        """获取需要深度分析的用户列表"""
        # 模拟数据
        return [f"user_{i}" for i in range(1, 11)]  # 返回10个用户

    async def _get_session_profiles_for_user_date(self, user_id: str, date: str):
        """获取用户指定日期的会话画像"""
        # 这里需要连接到实际的数据库
        return []  # 模拟返回空列表

    async def _get_daily_profiles_for_user_period(self, user_id: str, start_date: str, end_date: str):
        """获取用户指定时间段的每日画像"""
        # 这里需要连接到实际的数据库
        return []  # 模拟返回空列表

    # 回调管理方法
    def add_session_end_callback(self, callback: Callable):
        """添加会话结束回调"""
        self.session_end_callbacks.append(callback)

    def add_daily_update_callback(self, callback: Callable):
        """添加每日更新回调"""
        self.daily_update_callbacks.append(callback)

    def add_deep_analysis_callback(self, callback: Callable):
        """添加深度分析回调"""
        self.deep_analysis_callbacks.append(callback)

    # 手动触发方法
    async def manual_daily_aggregation(self, user_id: str, date: str) -> ProfileUpdateResult:
        """手动触发每日聚合"""
        return await self._process_daily_aggregation(user_id, date)

    async def manual_deep_analysis(self, user_id: str) -> ProfileUpdateResult:
        """手动触发深度分析"""
        return await self._process_deep_analysis(user_id)

    # 监控和统计方法
    def get_active_sessions_count(self) -> int:
        """获取活跃会话数量"""
        return len(self.active_sessions)

    def get_pending_extractions_count(self) -> int:
        """获取待提取会话数量"""
        return len(self.pending_extractions)

    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        jobs = self.scheduler.get_jobs()
        
        return {
            "running": self.scheduler.running,
            "active_sessions": len(self.active_sessions),
            "pending_extractions": len(self.pending_extractions),
            "scheduled_jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
                for job in jobs
            ]
        }


# ============================== 全局实例 ==============================
profile_scheduler = ProfileScheduler()
