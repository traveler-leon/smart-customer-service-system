"""
用户画像提取 API 接口
基于 memory_manager 的画像提取服务
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from agents.airport_service.context_engineering.memory_manager import memory_manager

logger = logging.getLogger(__name__)

# 创建路由器
profile_router = APIRouter(prefix="/api/profile", tags=["用户画像"])

# ============================== 请求/响应模型 ==============================

class SessionExtractionRequest(BaseModel):
    """会话画像提取请求"""
    application_id: str = Field(..., description="应用ID")
    user_id: str = Field(..., description="用户ID")
    run_id: str = Field(..., description="会话ID")

class DailyAggregationRequest(BaseModel):
    """每日聚合请求"""
    user_id: str = Field(..., description="用户ID")
    date: str = Field(..., description="日期 (YYYY-MM-DD)")

class DeepAnalysisRequest(BaseModel):
    """深度分析请求"""
    user_id: str = Field(..., description="用户ID")
    days: int = Field(30, description="分析天数")

class BatchExtractionRequest(BaseModel):
    """批量提取请求"""
    application_id: str = Field(..., description="应用ID")
    user_sessions: List[Dict[str, str]] = Field(..., description="用户会话列表")

class ProfileResponse(BaseModel):
    """画像响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# ============================== API 接口 ==============================

@profile_router.post("/extract/session", response_model=ProfileResponse)
async def extract_session_profile(request: SessionExtractionRequest):
    """
    提取单次会话画像（第一步）
    
    用于会话结束后立即触发的画像提取
    """
    try:
        # 初始化记忆管理器
        if not memory_manager._initialized:
            await memory_manager.initialize()
        
        # 触发会话画像提取
        result = await memory_manager.trigger_session_profile_extraction(
            application_id=request.application_id,
            user_id=request.user_id,
            run_id=request.run_id
        )
        
        if result and result.get("success"):
            return ProfileResponse(
                success=True,
                message="会话画像提取成功",
                data=result
            )
        else:
            error_msg = result.get("error", "未知错误") if result else "提取结果为空"
            return ProfileResponse(
                success=False,
                message="会话画像提取失败",
                error=error_msg
            )
            
    except Exception as e:
        logger.error(f"会话画像提取API异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务错误: {str(e)}")

@profile_router.post("/extract/session/async", response_model=ProfileResponse)
async def extract_session_profile_async(
    request: SessionExtractionRequest, 
    background_tasks: BackgroundTasks
):
    """
    异步提取单次会话画像
    
    适用于不需要立即返回结果的场景
    """
    try:
        # 添加后台任务
        background_tasks.add_task(
            _async_session_extraction,
            request.application_id,
            request.user_id,
            request.run_id
        )
        
        return ProfileResponse(
            success=True,
            message="会话画像提取任务已提交",
            data={
                "application_id": request.application_id,
                "user_id": request.user_id,
                "run_id": request.run_id,
                "status": "processing"
            }
        )
        
    except Exception as e:
        logger.error(f"异步会话画像提取API异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务错误: {str(e)}")

@profile_router.post("/aggregate/daily", response_model=ProfileResponse)
async def aggregate_daily_profile(request: DailyAggregationRequest):
    """
    聚合每日画像（第二步）
    
    用于每日定时任务触发的画像聚合
    """
    try:
        # 初始化记忆管理器
        if not memory_manager._initialized:
            await memory_manager.initialize()
        
        # 触发每日聚合
        result = await memory_manager.trigger_daily_profile_aggregation(
            user_id=request.user_id,
            date=request.date
        )
        
        if result and result.get("success"):
            return ProfileResponse(
                success=True,
                message="每日画像聚合成功",
                data=result
            )
        else:
            error_msg = result.get("error", "未知错误") if result else "聚合结果为空"
            return ProfileResponse(
                success=False,
                message="每日画像聚合失败",
                error=error_msg
            )
            
    except Exception as e:
        logger.error(f"每日聚合API异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务错误: {str(e)}")

@profile_router.post("/analyze/deep", response_model=ProfileResponse)
async def analyze_deep_insight(request: DeepAnalysisRequest):
    """
    深度洞察分析（第三步）
    
    用于长周期的用户画像深度分析
    """
    try:
        # 初始化记忆管理器
        if not memory_manager._initialized:
            await memory_manager.initialize()
        
        # 触发深度分析
        result = await memory_manager.trigger_deep_insight_analysis(
            user_id=request.user_id,
            days=request.days
        )
        
        if result and result.get("success"):
            return ProfileResponse(
                success=True,
                message="深度洞察分析成功",
                data=result
            )
        else:
            error_msg = result.get("error", "未知错误") if result else "分析结果为空"
            return ProfileResponse(
                success=False,
                message="深度洞察分析失败",
                error=error_msg
            )
            
    except Exception as e:
        logger.error(f"深度分析API异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务错误: {str(e)}")

@profile_router.post("/extract/batch", response_model=ProfileResponse)
async def batch_extract_profiles(
    request: BatchExtractionRequest,
    background_tasks: BackgroundTasks
):
    """
    批量提取画像
    
    适用于批量处理多个用户会话的场景
    """
    try:
        # 添加后台批量任务
        background_tasks.add_task(
            _async_batch_extraction,
            request.application_id,
            request.user_sessions
        )
        
        return ProfileResponse(
            success=True,
            message=f"批量画像提取任务已提交，共{len(request.user_sessions)}个会话",
            data={
                "application_id": request.application_id,
                "batch_size": len(request.user_sessions),
                "status": "processing"
            }
        )
        
    except Exception as e:
        logger.error(f"批量提取API异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务错误: {str(e)}")

@profile_router.get("/query/{user_id}", response_model=ProfileResponse)
async def query_user_profile(user_id: str):
    """
    查询用户画像
    
    获取用户的完整画像信息
    """
    try:
        # 初始化记忆管理器
        if not memory_manager._initialized:
            await memory_manager.initialize()
        
        # 查询用户画像
        user_profile = await memory_manager.get_user_profile(user_id)
        
        if user_profile:
            return ProfileResponse(
                success=True,
                message="用户画像查询成功",
                data={
                    "user_id": user_profile.user_id,
                    "profile_data": user_profile.profile_data,
                    "preferences": user_profile.preferences,
                    "behavioral_patterns": user_profile.behavioral_patterns,
                    "last_updated": user_profile.last_updated.isoformat(),
                    "extraction_source": user_profile.extraction_source
                }
            )
        else:
            return ProfileResponse(
                success=False,
                message="未找到用户画像",
                error="用户画像不存在或尚未生成"
            )
            
    except Exception as e:
        logger.error(f"画像查询API异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务错误: {str(e)}")

@profile_router.get("/conversation/{application_id}/{user_id}/{run_id}")
async def get_conversation_history(
    application_id: str,
    user_id: str,
    run_id: str,
    limit: int = 50
):
    """
    获取会话历史
    
    用于查看特定会话的对话记录
    """
    try:
        # 初始化记忆管理器
        if not memory_manager._initialized:
            await memory_manager.initialize()
        
        # 获取会话历史
        conversation_history = await memory_manager.get_conversation_history(
            application_id=application_id,
            user_id=user_id,
            run_id=run_id,
            limit=limit
        )
        
        return ProfileResponse(
            success=True,
            message=f"获取到{len(conversation_history)}条会话记录",
            data={
                "application_id": application_id,
                "user_id": user_id,
                "run_id": run_id,
                "conversation_count": len(conversation_history),
                "conversations": conversation_history
            }
        )
        
    except Exception as e:
        logger.error(f"会话历史查询API异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务错误: {str(e)}")

@profile_router.post("/trigger/auto")
async def trigger_auto_extraction(
    user_id: str,
    application_id: str = "airport_service",
    background_tasks: BackgroundTasks = None
):
    """
    触发自动画像提取
    
    根据用户当前状态自动决定执行哪些画像提取步骤
    """
    try:
        # 添加自动化后台任务
        if background_tasks:
            background_tasks.add_task(
                _auto_profile_extraction,
                user_id,
                application_id
            )
        
        return ProfileResponse(
            success=True,
            message="自动画像提取任务已提交",
            data={
                "user_id": user_id,
                "application_id": application_id,
                "extraction_type": "auto",
                "status": "processing"
            }
        )
        
    except Exception as e:
        logger.error(f"自动提取API异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务错误: {str(e)}")

# ============================== 后台任务函数 ==============================

async def _async_session_extraction(application_id: str, user_id: str, run_id: str):
    """异步会话画像提取任务"""
    try:
        # 初始化记忆管理器
        if not memory_manager._initialized:
            await memory_manager.initialize()
        
        # 执行提取
        result = await memory_manager.trigger_session_profile_extraction(
            application_id=application_id,
            user_id=user_id,
            run_id=run_id
        )
        
        logger.info(f"异步会话画像提取完成: {user_id}:{run_id}, 结果: {result}")
        
    except Exception as e:
        logger.error(f"异步会话画像提取失败: {user_id}:{run_id} - {str(e)}")

async def _async_batch_extraction(application_id: str, user_sessions: List[Dict[str, str]]):
    """异步批量画像提取任务"""
    try:
        # 初始化记忆管理器
        if not memory_manager._initialized:
            await memory_manager.initialize()
        
        success_count = 0
        failed_count = 0
        
        # 逐个处理会话
        for session in user_sessions:
            try:
                result = await memory_manager.trigger_session_profile_extraction(
                    application_id=application_id,
                    user_id=session["user_id"],
                    run_id=session["run_id"]
                )
                
                if result and result.get("success"):
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as session_error:
                logger.error(f"单个会话提取失败: {session} - {str(session_error)}")
                failed_count += 1
        
        logger.info(f"批量画像提取完成: 成功{success_count}, 失败{failed_count}")
        
    except Exception as e:
        logger.error(f"批量画像提取失败: {str(e)}")

async def _auto_profile_extraction(user_id: str, application_id: str):
    """自动化画像提取任务"""
    try:
        # 初始化记忆管理器
        if not memory_manager._initialized:
            await memory_manager.initialize()
        
        # 检查用户最近的活动情况，决定执行哪些步骤
        # 这里简化为执行每日聚合和深度分析
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 执行每日聚合
        daily_result = await memory_manager.trigger_daily_profile_aggregation(
            user_id=user_id,
            date=today
        )
        
        # 如果是周一，执行深度分析
        if datetime.now().weekday() == 0:
            deep_result = await memory_manager.trigger_deep_insight_analysis(
                user_id=user_id,
                days=30
            )
        else:
            deep_result = None
        
        logger.info(f"自动画像提取完成: {user_id}, 每日聚合: {daily_result}, 深度分析: {deep_result}")
        
    except Exception as e:
        logger.error(f"自动画像提取失败: {user_id} - {str(e)}")

# ============================== 健康检查和状态接口 ==============================

@profile_router.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查记忆管理器状态
        if not memory_manager._initialized:
            await memory_manager.initialize()
        
        return {
            "status": "healthy",
            "service": "user_profile_extraction",
            "memory_manager_initialized": memory_manager._initialized,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=503, detail="服务不可用")

@profile_router.get("/status")
async def service_status():
    """服务状态"""
    try:
        return {
            "service_name": "用户画像提取服务",
            "version": "1.0.0",
            "description": "基于 TrustCall 和 memory_manager 的三步走用户画像提取系统",
            "features": [
                "会话画像提取（实时）",
                "每日画像聚合（定时）", 
                "深度洞察分析（周期性）",
                "批量处理支持",
                "异步任务处理"
            ],
            "endpoints": {
                "extract_session": "/api/profile/extract/session",
                "aggregate_daily": "/api/profile/aggregate/daily",
                "analyze_deep": "/api/profile/analyze/deep",
                "batch_extract": "/api/profile/extract/batch",
                "query_profile": "/api/profile/query/{user_id}",
                "auto_extract": "/api/profile/trigger/auto"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"状态查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务错误")
