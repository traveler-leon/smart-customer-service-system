"""
记忆管理定时任务调度器
负责用户画像的异步提取和更新
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
    """记忆管理定时任务调度器"""
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        self.processed_users: Set[str] = set()  # 今日已处理的用户
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
        # 每天凌晨2点提取用户画像
        schedule.every().day.at("02:00").do(self._schedule_daily_profile_extraction)
        
        # 每小时检查是否有新用户需要提取画像
        schedule.every().hour.do(self._schedule_hourly_new_user_check)
        
        # 每天凌晨重置处理记录
        schedule.every().day.at("00:01").do(self._reset_daily_records)
        
        logger.info("定时任务已配置")
    
    def _run_scheduler(self):
        """运行调度器主循环"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器运行异常: {e}", exc_info=True)
                time.sleep(60)
    
    def _schedule_daily_profile_extraction(self):
        """调度每日用户画像提取任务"""
        logger.info("开始每日用户画像提取任务")
        
        # 在新线程中运行异步任务
        asyncio.run_coroutine_threadsafe(
            self._daily_profile_extraction(),
            asyncio.new_event_loop()
        )
    
    def _schedule_hourly_new_user_check(self):
        """调度每小时新用户检查任务"""
        logger.info("开始每小时新用户检查任务")
        
        # 在新线程中运行异步任务
        asyncio.run_coroutine_threadsafe(
            self._hourly_new_user_check(),
            asyncio.new_event_loop()
        )
    
    def _reset_daily_records(self):
        """重置每日处理记录"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.processed_users.clear()
            self.last_reset_date = current_date
            logger.info("每日处理记录已重置")
    
    async def _daily_profile_extraction(self):
        """每日用户画像提取主逻辑"""
        try:
            # 获取需要更新画像的用户列表
            users_to_process = await self._get_users_for_profile_update()
            
            logger.info(f"需要处理的用户数量: {len(users_to_process)}")
            
            success_count = 0
            error_count = 0
            
            for user_id in users_to_process:
                if user_id in self.processed_users:
                    logger.debug(f"用户 {user_id} 今日已处理，跳过")
                    continue
                
                try:
                    # 提取用户画像
                    await self._extract_user_profile_safe(user_id)
                    self.processed_users.add(user_id)
                    success_count += 1
                    
                    # 避免过于频繁的处理
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"用户 {user_id} 画像提取失败: {e}")
                    error_count += 1
            
            logger.info(f"每日用户画像提取完成: 成功 {success_count}, 失败 {error_count}")
            
        except Exception as e:
            logger.error(f"每日用户画像提取任务异常: {e}", exc_info=True)
    
    async def _hourly_new_user_check(self):
        """每小时新用户检查逻辑"""
        try:
            # 获取最近一小时有对话的用户
            recent_users = await self._get_recent_active_users(hours=1)
            
            new_users_to_process = []
            for user_id in recent_users:
                if user_id not in self.processed_users:
                    # 检查用户是否有足够的对话历史
                    conversation_count = await self._get_user_conversation_count(user_id)
                    if conversation_count >= 5:  # 至少5次对话才提取画像
                        new_users_to_process.append(user_id)
            
            if new_users_to_process:
                logger.info(f"发现 {len(new_users_to_process)} 个新用户需要提取画像")
                
                for user_id in new_users_to_process:
                    try:
                        await self._extract_user_profile_safe(user_id)
                        self.processed_users.add(user_id)
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"新用户 {user_id} 画像提取失败: {e}")
            
        except Exception as e:
            logger.error(f"每小时新用户检查任务异常: {e}", exc_info=True)
    
    async def _get_users_for_profile_update(self) -> list:
        """
        获取需要更新画像的用户列表
        
        Returns:
            用户ID列表
        """
        try:
            # 这里需要根据实际数据源获取用户列表
            # 可以从对话历史中获取最近活跃的用户
            return await self._get_recent_active_users(hours=24)
            
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}", exc_info=True)
            return []
    
    async def _get_recent_active_users(self, hours: int = 24) -> list:
        """
        获取最近活跃的用户列表
        
        Args:
            hours: 时间范围（小时）
            
        Returns:
            用户ID列表
        """
        try:
            # 这是一个简化的实现
            # 实际项目中可能需要从数据库或其他数据源获取
            
            # 目前从内存中的记忆管理器获取（这只是示例）
            # 在生产环境中，你可能需要：
            # 1. 查询Redis checkpoint中的活跃用户
            # 2. 查询数据库中的最近对话记录
            # 3. 从日志中分析活跃用户
            
            active_users = set()
            
            # 示例：从已知用户列表中获取（你需要根据实际情况调整）
            sample_users = ["alice", "bob", "charlie", "david", "eve"]
            
            for user_id in sample_users:
                try:
                    conversations = await memory_manager.get_conversation_history(
                        user_id=user_id,
                        limit=1
                    )
                    if conversations:
                        # 检查最近是否有对话
                        latest_conversation = conversations[0]
                        time_diff = datetime.now() - latest_conversation.timestamp
                        if time_diff <= timedelta(hours=hours):
                            active_users.add(user_id)
                except Exception:
                    continue
            
            return list(active_users)
            
        except Exception as e:
            logger.error(f"获取活跃用户失败: {e}", exc_info=True)
            return []
    
    async def _get_user_conversation_count(self, user_id: str) -> int:
        """
        获取用户对话数量
        
        Args:
            user_id: 用户ID
            
        Returns:
            对话数量
        """
        try:
            conversations = await memory_manager.get_conversation_history(
                user_id=user_id,
                limit=100
            )
            return len(conversations)
        except Exception:
            return 0
    
    async def _extract_user_profile_safe(self, user_id: str):
        """
        安全地提取用户画像（带错误处理）
        
        Args:
            user_id: 用户ID
        """
        try:
            logger.info(f"开始提取用户画像: {user_id}")
            
            # 检查用户是否已有画像
            existing_profile = await memory_manager.get_user_profile(user_id)
            
            if existing_profile:
                # 检查画像是否需要更新（例如：超过7天）
                days_since_update = (datetime.now() - existing_profile.last_updated).days
                if days_since_update < 7:
                    logger.debug(f"用户 {user_id} 画像较新，跳过更新")
                    return
            
            # 提取用户画像
            profile = await memory_manager.extract_user_profile(user_id)
            
            if profile:
                logger.info(f"用户画像提取成功: {user_id}")
            else:
                logger.warning(f"用户画像提取失败（可能对话历史不足）: {user_id}")
                
        except Exception as e:
            logger.error(f"用户画像提取异常: {user_id}, {e}", exc_info=True)
            raise
    
    async def manual_extract_profile(self, user_id: str) -> bool:
        """
        手动触发用户画像提取
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        try:
            await self._extract_user_profile_safe(user_id)
            self.processed_users.add(user_id)
            return True
        except Exception as e:
            logger.error(f"手动提取用户画像失败: {user_id}, {e}")
            return False


# 全局调度器实例
memory_scheduler = MemoryScheduler()


def start_memory_scheduler():
    """启动记忆管理调度器"""
    memory_scheduler.start()


def stop_memory_scheduler():
    """停止记忆管理调度器"""
    memory_scheduler.stop()


async def trigger_manual_profile_extraction(user_id: str) -> bool:
    """
    手动触发用户画像提取
    
    Args:
        user_id: 用户ID
        
    Returns:
        是否成功
    """
    return await memory_scheduler.manual_extract_profile(user_id)
