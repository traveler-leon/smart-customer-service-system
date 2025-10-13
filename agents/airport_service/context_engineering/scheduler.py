"""
记忆管理定时任务调度器
负责每日画像聚合和深度画像分析的定时调度
注意：会话画像由前端主动触发，不需要定时调度
"""
import asyncio
from datetime import datetime, timedelta
from typing import Set, Dict, Any
import schedule
import threading
import time

from .memory_manager import memory_manager
from common.logging import get_logger

logger = get_logger("memory_scheduler")


class MemoryScheduler:
    """
    记忆管理定时任务调度器
    
    功能：
    - 每日凌晨2点：执行每日画像聚合
    - 每周一凌晨3点：执行深度画像分析
    - 会话画像不在此处调度，由前端主动触发
    """
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        self.processed_users: Set[str] = set()  # 今日已处理的用户（防重复）
        self.last_reset_date = datetime.now().date()
    
    def start(self):
        """启动定时任务调度器"""
        if self.is_running:
            logger.warning("调度器已在运行中")
            return
        
        self.is_running = True
        
        # 配置定时任务
        self._setup_schedules()
        
        # 启动调度器线程
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("记忆管理调度器已启动")
    
    def stop(self):
        """停止定时任务调度器"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("记忆管理调度器已停止")
    
    def _setup_schedules(self):
        """配置定时任务"""
        schedule.every().day.at("02:00").do(self._schedule_daily_profile_aggregation)
        schedule.every().monday.at("03:00").do(self._schedule_deep_insight_analysis)
        schedule.every().day.at("00:01").do(self._reset_daily_records)
        
        logger.info("定时任务已配置：每日画像聚合(02:00)、深度画像分析(周一03:00)")
    
    def _run_scheduler(self):
        """运行调度器主循环"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器运行异常: {e}", exc_info=True)
                time.sleep(60)
    
    def _schedule_daily_profile_aggregation(self):
        """调度每日画像聚合任务"""
        logger.info("开始每日画像聚合任务")
        
        # 在新线程中运行异步任务
        asyncio.run_coroutine_threadsafe(
            self._daily_profile_aggregation(),
            asyncio.new_event_loop()
        )
    
    def _schedule_deep_insight_analysis(self):
        """调度深度画像分析任务"""
        logger.info("开始深度画像分析任务")
        
        # 在新线程中运行异步任务
        asyncio.run_coroutine_threadsafe(
            self._deep_insight_analysis(),
            asyncio.new_event_loop()
        )
    
    def _reset_daily_records(self):
        """重置每日处理记录"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.processed_users.clear()
            self.last_reset_date = current_date
            logger.info("每日处理记录已重置")
    
    async def _daily_profile_aggregation(self):
        """每日画像聚合主逻辑"""
        try:
            # 获取需要进行每日聚合的用户列表
            users_to_process = await self._get_users_for_daily_aggregation()
            
            logger.info(f"需要进行每日聚合的用户数量: {len(users_to_process)}")
            
            success_count = 0
            error_count = 0
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            for user_id in users_to_process:
                if user_id in self.processed_users:
                    logger.debug(f"用户 {user_id} 今日已处理，跳过")
                    continue
                
                try:
                    # 触发每日画像聚合
                    result = await memory_manager.trigger_daily_profile_aggregation(
                        application_id="airport_service",
                        user_id=user_id,
                        date=yesterday
                    )
                    
                    if result and result.get("success"):
                        self.processed_users.add(user_id)
                        success_count += 1
                        logger.info(f"用户 {user_id} 每日画像聚合成功")
                    else:
                        error_count += 1
                        logger.warning(f"用户 {user_id} 每日画像聚合失败: {result.get('error') if result else '未知错误'}")
                    
                    # 避免过于频繁的处理
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"用户 {user_id} 每日画像聚合异常: {e}")
                    error_count += 1
            
            logger.info(f"每日画像聚合完成: 成功 {success_count}, 失败 {error_count}")
            
        except Exception as e:
            logger.error(f"每日画像聚合任务异常: {e}", exc_info=True)
    
    async def _deep_insight_analysis(self):
        """深度画像分析主逻辑"""
        try:
            # 获取需要进行深度分析的用户列表
            users_to_process = await self._get_users_for_deep_analysis()
            
            logger.info(f"需要进行深度分析的用户数量: {len(users_to_process)}")
            
            success_count = 0
            error_count = 0
            
            for user_id in users_to_process:
                try:
                    # 触发深度洞察分析
                    result = await memory_manager.trigger_deep_insight_analysis(
                        user_id=user_id,
                        application_id="airport_service",
                        days=30
                    )
                    
                    if result and result.get("success"):
                        success_count += 1
                        logger.info(f"用户 {user_id} 深度画像分析成功")
                    else:
                        error_count += 1
                        logger.warning(f"用户 {user_id} 深度画像分析失败: {result.get('error') if result else '未知错误'}")
                    
                    # 避免过于频繁的处理
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"用户 {user_id} 深度画像分析异常: {e}")
                    error_count += 1
            
            logger.info(f"深度画像分析完成: 成功 {success_count}, 失败 {error_count}")
            
        except Exception as e:
            logger.error(f"深度画像分析任务异常: {e}", exc_info=True)
    
    async def _get_users_for_daily_aggregation(self) -> list:
        """
        获取需要进行每日聚合的用户列表
        
        Returns:
            用户ID列表
        """
        try:
            # 获取昨天有会话画像的用户
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            users = await self._get_users_with_sessions_on_date(yesterday)
            return users
            
        except Exception as e:
            logger.error(f"获取每日聚合用户列表失败: {e}", exc_info=True)
            return []
    
    async def _get_users_for_deep_analysis(self) -> list:
        """
        获取需要进行深度分析的用户列表
        
        Returns:
            用户ID列表
        """
        try:
            # 获取最近30天有活动且数据充足的用户
            users = await self._get_users_with_sufficient_data(days=30)
            return users
            
        except Exception as e:
            logger.error(f"获取深度分析用户列表失败: {e}", exc_info=True)
            return []
    
    async def _get_users_with_sessions_on_date(self, date: str) -> list:
        """
        获取指定日期有会话画像的用户列表
        
        Args:
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            用户ID列表
        """
        try:
            # 获取指定日期的会话画像
            session_profiles = await memory_manager.get_session_profiles(
                day=date,
                limit=1000  # 设置一个较大的限制
            )
            
            # 提取唯一的用户ID
            user_ids = list(set([profile.get("user_id") for profile in session_profiles if profile.get("user_id")]))
            
            logger.info(f"找到 {len(user_ids)} 个用户在 {date} 有会话画像")
            return user_ids
            
        except Exception as e:
            logger.error(f"获取指定日期会话用户失败: {e}", exc_info=True)
            return []
    
    async def _get_users_with_sufficient_data(self, days: int = 30) -> list:
        """
        获取数据充足的用户列表（用于深度分析）
        
        Args:
            days: 数据时间范围（天）
            
        Returns:
            用户ID列表
        """
        try:
            # 获取最近有每日画像的用户
            sufficient_users = []
            
            # 检查最近days天有每日画像的用户
            for i in range(days):
                date = (datetime.now() - timedelta(days=i+1)).strftime("%Y-%m-%d")
                daily_profiles = await memory_manager.get_daily_profiles(
                    date=date,
                    limit=100
                )
                
                for profile_data in daily_profiles:
                    user_id = profile_data.get("user_id")
                    if user_id and user_id not in sufficient_users:
                        # 检查用户是否有足够的数据（至少7天的记录）
                        user_daily_count = await self._count_user_daily_profiles(user_id, days)
                        if user_daily_count >= 7:
                            sufficient_users.append(user_id)
            
            logger.info(f"找到 {len(sufficient_users)} 个用户数据充足，可进行深度分析")
            return sufficient_users
            
        except Exception as e:
            logger.error(f"获取数据充足用户失败: {e}", exc_info=True)
            return []
    
    async def _count_user_daily_profiles(self, user_id: str, days: int) -> int:
        """
        统计用户的每日画像数量
        
        Args:
            user_id: 用户ID
            days: 统计天数
            
        Returns:
            每日画像数量
        """
        try:
            daily_profiles = await memory_manager.get_period_daily_profiles(
                user_id=user_id,
                application_id="airport_service",
                days=days
            )
            return len(daily_profiles)
        except Exception:
            return 0
    
    async def manual_trigger_daily_aggregation(self, user_id: str, date: str) -> bool:
        """
        手动触发每日画像聚合
        
        Args:
            user_id: 用户ID
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            是否成功
        """
        try:
            result = await memory_manager.trigger_daily_profile_aggregation(
                application_id="airport_service",
                user_id=user_id,
                date=date
            )
            
            if result and result.get("success"):
                logger.info(f"手动触发每日聚合成功: {user_id}, {date}")
                return True
            else:
                logger.warning(f"手动触发每日聚合失败: {user_id}, {date}")
                return False
                
        except Exception as e:
            logger.error(f"手动触发每日聚合异常: {user_id}, {date}, {e}")
            return False
    
    async def manual_trigger_deep_analysis(self, user_id: str, days: int = 30) -> bool:
        """
        手动触发深度画像分析
        
        Args:
            user_id: 用户ID
            days: 分析天数
            
        Returns:
            是否成功
        """
        try:
            result = await memory_manager.trigger_deep_insight_analysis(
                user_id=user_id,
                application_id="airport_service",
                days=days
            )
            
            if result and result.get("success"):
                logger.info(f"手动触发深度分析成功: {user_id}")
                return True
            else:
                logger.warning(f"手动触发深度分析失败: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"手动触发深度分析异常: {user_id}, {e}")
            return False


# 全局调度器实例
memory_scheduler = MemoryScheduler()


def start_memory_scheduler():
    """启动记忆管理调度器"""
    memory_scheduler.start()


def stop_memory_scheduler():
    """停止记忆管理调度器"""
    memory_scheduler.stop()


async def trigger_manual_daily_aggregation(user_id: str, date: str) -> bool:
    """
    手动触发每日画像聚合
    
    Args:
        user_id: 用户ID
        date: 日期 (YYYY-MM-DD)
        
    Returns:
        是否成功
    """
    return await memory_scheduler.manual_trigger_daily_aggregation(user_id, date)

async def trigger_manual_deep_analysis(user_id: str, days: int = 30) -> bool:
    """
    手动触发深度画像分析
    
    Args:
        user_id: 用户ID
        days: 分析天数
        
    Returns:
        是否成功
    """
    return await memory_scheduler.manual_trigger_deep_analysis(user_id, days)
