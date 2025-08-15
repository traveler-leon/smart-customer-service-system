"""
记忆管理API接口
包含对话历史查看、专家审核、用户画像等功能
"""
import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field

from agents.airport_service.context_engineering.memory_manager import memory_manager, ConversationMemory
from common.logging import get_logger

logger = get_logger("api.memory_management")

router = APIRouter(prefix="/memory/v1", tags=["记忆管理"])

# ==================== 请求/响应模型 ====================

class ConversationHistoryRequest(BaseModel):
    """对话历史查询请求"""
    user_id: str = Field(..., description="用户ID")
    limit: int = Field(default=50, ge=1, le=200, description="返回数量限制")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")


class ConversationItem(BaseModel):
    """对话项模型"""
    conversation_id: str
    user_id: str
    thread_id: str
    query: str
    response: str
    timestamp: str
    metadata: dict
    is_expert_approved: bool
    quality_score: Optional[float]
    tags: List[str]


class ConversationHistoryResponse(BaseModel):
    """对话历史响应"""
    ret_code: str
    ret_msg: str
    data: dict


class ExpertReviewRequest(BaseModel):
    """单个专家审核请求"""
    memory_id: str = Field(..., description="记忆ID")
    query: str = Field(..., description="原始用户查询")
    expert_approved: bool = Field(..., description="是否审核通过")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="质量评分")
    corrected_response: Optional[str] = Field(None, description="专家修正的回答内容")
    review_notes: Optional[str] = Field(None, description="审核备注")
    expert_id: Optional[str] = Field(None, description="审核专家ID")


class BatchExpertReviewRequest(BaseModel):
    """批量专家审核请求"""
    review_items: List[ExpertReviewRequest] = Field(..., description="审核项目列表", max_items=1000)
    

class UserProfileResponse(BaseModel):
    """用户画像响应"""
    ret_code: str
    ret_msg: str
    data: dict


class ExampleSearchRequest(BaseModel):
    """优质示例搜索请求"""
    query: str = Field(..., description="搜索查询")
    limit: int = Field(default=5, ge=1, le=20, description="返回数量")
    min_quality_score: float = Field(default=0.8, ge=0.0, le=1.0, description="最低质量评分")


class UserFeedbackRequest(BaseModel):
    """用户反馈请求"""
    response: str = Field(..., description="系统回复内容")
    user_approved: int = Field(..., description="用户反馈类型：1=点赞，-1=点踩")



@router.get("/conversations/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    user_id: Optional[str] = Query(None, description="用户ID"),
    agent_id: Optional[str] = Query(None, description="智能体ID"),
    run_id: Optional[str] = Query(None, description="会话ID"),
    application_id: Optional[str] = Query(None, description="应用ID"),
    expert_verified: Optional[bool] = Query(None, description="是否专家校验"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
):
    """
    获取对话历史 - 支持多种查询条件组合
    """
    logger.info(f"获取对话历史: user_id={user_id}, agent_id={agent_id}, run_id={run_id}")
    
    try:
        # 这样更符合前端的预期行为
        if not any([user_id, agent_id, run_id, application_id]):
            logger.warning("未提供任何查询条件，返回空结果")
            return ConversationHistoryResponse(
                ret_code="000000",
                ret_msg="操作成功（未提供查询条件）",
                data={
                    "total_count": 0,
                    "conversations": [],
                    "query_params": {
                        "user_id": user_id,
                        "agent_id": agent_id,
                        "run_id": run_id,
                        "application_id": application_id,
                        "expert_verified": expert_verified,
                        "limit": limit,
                        "start_date": start_date,
                        "end_date": end_date
                    }
                }
            )
        
        # 解析日期
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                # 将naive datetime转换为UTC时间，方便与数据库中的时间比较
                from datetime import timezone
                start_datetime = start_datetime.replace(tzinfo=timezone.utc)
            except ValueError:
                raise HTTPException(status_code=400, detail="开始日期格式错误，请使用 YYYY-MM-DD 格式")
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)  # 设置为当天结束
                # 将naive datetime转换为UTC时间，方便与数据库中的时间比较
                from datetime import timezone
                end_datetime = end_datetime.replace(tzinfo=timezone.utc)
            except ValueError:
                raise HTTPException(status_code=400, detail="结束日期格式错误，请使用 YYYY-MM-DD 格式")
        
        # 获取对话历史
        conversations = await memory_manager.get_conversation_history(
            user_id=user_id,
            agent_id=agent_id, 
            run_id=run_id,   
            application_id=application_id,
            expert_verified=expert_verified,
            limit=limit,
            start_date=start_datetime,
            end_date=end_datetime
        )

        return ConversationHistoryResponse(
            ret_code="000000",
            ret_msg="操作成功",
            data={
                "total_count": len(conversations),
                "conversations": conversations,
                "query_params": {
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "application_id": application_id,
                    "expert_verified": expert_verified,
                    "limit": limit,
                    "start_date": start_date,
                    "end_date": end_date
                }
            }
        )
        
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}", exc_info=True)
        return ConversationHistoryResponse(
            ret_code="999999",
            ret_msg=f"获取对话历史失败: {str(e)}",
            data={}
        )


@router.post("/conversations/expert-review")
async def expert_review_conversation(request: ExpertReviewRequest):
    """
    专家审核单个对话 - 使用 mem0 update API
    支持修改回答内容、质量评分、审核备注等
    """
    logger.info(f"专家审核对话: memory_id={request.memory_id}, approved={request.expert_approved}")
    
    try:
        success = await memory_manager.expert_review_conversation(
            memory_id=request.memory_id,
            query=request.query,
            expert_approved=request.expert_approved,
            quality_score=request.quality_score,
            corrected_response=request.corrected_response,
            expert_id=request.expert_id
        )
        
        if success:
            return {
                "ret_code": "000000",
                "ret_msg": "专家审核成功",
                "data": {
                    "memory_id": request.memory_id,
                    "expert_approved": request.expert_approved,
                    "quality_score": request.quality_score,
                    "response_corrected": bool(request.corrected_response),
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {
                "ret_code": "999998",
                "ret_msg": "专家审核失败",
                "data": {"memory_id": request.memory_id}
            }
            
    except Exception as e:
        logger.error(f"专家审核失败: {e}", exc_info=True)
        return {
            "ret_code": "999999",
            "ret_msg": f"专家审核失败: {str(e)}",
            "data": {"memory_id": request.memory_id}
        }


@router.post("/conversations/batch-expert-review")
async def batch_expert_review(request: BatchExpertReviewRequest):
    """
    批量专家审核 - 使用 mem0 批量更新API
    支持一次性审核最多1000个对话记录
    """
    logger.info(f"批量专家审核: {len(request.review_items)} 个项目")
    
    try:
        # 转换为内部格式
        review_items = []
        for item in request.review_items:
            review_items.append({
                "memory_id": item.memory_id,
                "query": item.query,
                "expert_approved": item.expert_approved,
                "quality_score": item.quality_score,
                "corrected_response": item.corrected_response,
                "review_notes": item.review_notes,
                "expert_id": item.expert_id
            })
        
        result = await memory_manager.batch_expert_review(review_items)
        
        return {
            "ret_code": "000000",
            "ret_msg": "批量专家审核完成",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"批量专家审核失败: {e}", exc_info=True)
        return {
            "ret_code": "999999",
            "ret_msg": f"批量专家审核失败: {str(e)}",
            "data": {"error": str(e)}
        }

@router.get("/profile/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: str):
    """
    获取用户画像
    """
    logger.info(f"获取用户画像: user_id={user_id}")
    
    try:
        user_profile = await memory_manager.get_user_profile(user_id)
        
        if user_profile:
            return UserProfileResponse(
                ret_code="000000",
                ret_msg="操作成功",
                data={
                    "user_id": user_id,
                    "profile": user_profile.to_dict(),
                    "has_profile": True
                }
            )
        else:
            return UserProfileResponse(
                ret_code="000001",
                ret_msg="用户画像不存在",
                data={
                    "user_id": user_id,
                    "profile": None,
                    "has_profile": False
                }
            )
    
    except Exception as e:
        logger.error(f"获取用户画像失败: {e}", exc_info=True)
        return UserProfileResponse(
            ret_code="999999",
            ret_msg=f"获取用户画像失败: {str(e)}",
            data={}
        )


@router.post("/profile/{user_id}/extract")
async def extract_user_profile(user_id: str):
    """
    提取用户画像
    从对话历史中分析并生成用户画像
    """
    logger.info(f"提取用户画像: user_id={user_id}")
    
    try:
        user_profile = await memory_manager.extract_user_profile(user_id)
        
        if user_profile:
            return UserProfileResponse(
                ret_code="000000",
                ret_msg="用户画像提取成功",
                data={
                    "user_id": user_id,
                    "profile": user_profile.to_dict(),
                    "extraction_completed": True
                }
            )
        else:
            return UserProfileResponse(
                ret_code="000001",
                ret_msg="用户画像提取失败，可能是对话历史不足",
                data={
                    "user_id": user_id,
                    "profile": None,
                    "extraction_completed": False
                }
            )
    
    except Exception as e:
        logger.error(f"提取用户画像失败: {e}", exc_info=True)
        return UserProfileResponse(
            ret_code="999999",
            ret_msg=f"提取用户画像失败: {str(e)}",
            data={}
        )


@router.get("/conversations/search")
async def search_conversations(
    query: str = Query(..., description="搜索查询"),
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    agent_name: Optional[str] = Query(None, description="智能体名称筛选"),
    application_name: Optional[str] = Query(None, description="应用名称筛选"),
    expert_verified: Optional[bool] = Query(None, description="专家校验状态筛选"),
    min_quality_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="最低质量评分"),
    limit: int = Query(default=10, ge=1, le=50, description="返回数量限制")
):
    """
    基于相似度搜索对话记录
    支持多重筛选条件
    """
    logger.info(f"相似度搜索对话: query={query}, filters={locals()}")
    
    try:
        results = await memory_manager.search_conversations(
            query=query,
            user_id=user_id,
            agent_name=agent_name,
            application_name=application_name,
            expert_verified=expert_verified,
            min_quality_score=min_quality_score,
            limit=limit
        )
        
        return {
            "ret_code": "000000",
            "ret_msg": "操作成功",
            "data": {
                "query": query,
                "total_count": len(results),
                "conversations": results,
                "search_params": {
                    "user_id": user_id,
                    "agent_name": agent_name,
                    "application_name": application_name,
                    "expert_verified": expert_verified,
                    "min_quality_score": min_quality_score,
                    "limit": limit
                }
            }
        }
        
    except Exception as e:
        logger.error(f"相似度搜索失败: {e}", exc_info=True)
        return {
            "ret_code": "999999",
            "ret_msg": f"搜索失败: {str(e)}",
            "data": {}
        }


@router.post("/examples/search")
async def search_expert_examples(request: ExampleSearchRequest):
    """
    搜索专家审核的优质QA示例
    用于增强LLM的prompt
    """
    logger.info(f"搜索优质QA示例: query={request.query}")
    
    try:
        examples = await memory_manager.get_expert_approved_examples(
            query=request.query,
            limit=request.limit,
            min_quality_score=request.min_quality_score
        )
        
        return {
            "ret_code": "000000",
            "ret_msg": "操作成功",
            "data": {
                "query": request.query,
                "examples": examples,
                "count": len(examples),
                "search_params": {
                    "limit": request.limit,
                    "min_quality_score": request.min_quality_score
                }
            }
        }
        
    except Exception as e:
        logger.error(f"搜索优质QA示例失败: {e}", exc_info=True)
        return {
            "ret_code": "999999",
            "ret_msg": f"搜索失败: {str(e)}",
            "data": {}
        }


class SmartFilterRequest(BaseModel):
    """智能记忆筛选请求"""
    query: str = Field(..., description="搜索查询")
    user_id: Optional[str] = Field(None, description="用户ID筛选")
    agent_name: Optional[str] = Field(None, description="智能体名称筛选")
    application_name: Optional[str] = Field(None, description="应用名称筛选")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量")
    min_quality_score: float = Field(default=0.7, ge=0.0, le=1.0, description="最低质量评分")
    similarity_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="相似度权重")
    time_weight: float = Field(default=0.2, ge=0.0, le=1.0, description="时间权重")
    quality_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="质量权重")
    time_decay_days: int = Field(default=30, ge=1, le=365, description="时间衰减周期(天)")


@router.post("/conversations/smart-filter")
async def smart_filter_memories(request: SmartFilterRequest):
    """
    智能记忆筛选 - 基于多因子综合评分
    
    根据向量相似度、时间遗忘因子、专家评分等多个因素进行加权排序，
    返回最符合条件的TopK记忆
    """
    logger.info(f"智能记忆筛选: query={request.query}, weights=[sim:{request.similarity_weight}, time:{request.time_weight}, quality:{request.quality_weight}]")
    
    try:
        # 验证权重和
        total_weight = request.similarity_weight + request.time_weight + request.quality_weight
        if abs(total_weight - 1.0) > 0.1:  # 允许10%的误差
            logger.warning(f"权重和不等于1.0: {total_weight}, 系统将自动归一化")
        
        results = await memory_manager.get_smart_filtered_memories(
            query=request.query,
            user_id=request.user_id,
            agent_name=request.agent_name,
            application_name=request.application_name,
            limit=request.limit,
            min_quality_score=request.min_quality_score,
            similarity_weight=request.similarity_weight,
            time_weight=request.time_weight,
            quality_weight=request.quality_weight,
            time_decay_days=request.time_decay_days
        )
        
        # 统计信息
        stats = {
            "total_count": len(results),
            "avg_composite_score": 0.0,
            "avg_similarity_score": 0.0,
            "avg_time_score": 0.0,
            "avg_quality_score": 0.0,
        }
        
        if results:
            stats["avg_composite_score"] = sum(r['composite_score'] for r in results) / len(results)
            stats["avg_similarity_score"] = sum(r['similarity_score'] for r in results) / len(results)
            stats["avg_time_score"] = sum(r['time_score'] for r in results) / len(results)
            stats["avg_quality_score"] = sum(r['quality_score'] for r in results) / len(results)
        
        return {
            "ret_code": "000000",
            "ret_msg": "智能筛选成功",
            "data": {
                "query": request.query,
                "memories": results,
                "stats": stats,
                "filter_params": {
                    "user_id": request.user_id,
                    "agent_name": request.agent_name,
                    "application_name": request.application_name,
                    "limit": request.limit,
                    "min_quality_score": request.min_quality_score,
                    "weights": {
                        "similarity": request.similarity_weight,
                        "time": request.time_weight,
                        "quality": request.quality_weight
                    },
                    "time_decay_days": request.time_decay_days
                }
            }
        }
        
    except Exception as e:
        logger.error(f"智能记忆筛选失败: {e}", exc_info=True)
        return {
            "ret_code": "999999",
            "ret_msg": f"智能筛选失败: {str(e)}",
            "data": {}
        }


@router.get("/stats/{user_id}")
async def get_memory_stats(user_id: str):
    """
    获取用户记忆统计信息
    """
    logger.info(f"获取记忆统计: user_id={user_id}")
    
    try:
        # 获取对话历史
        conversations = await memory_manager.get_conversation_history(
            user_id=user_id,
            limit=1000  # 获取更多数据用于统计
        )
        
        # 统计信息
        total_conversations = len(conversations)
        approved_conversations = sum(1 for conv in conversations if conv.get('expert_verified', False))
        
        # 按日期统计
        date_stats = {}
        agent_stats = {}
        for conv in conversations:
            # 处理日期统计
            created_at = conv.get('created_at', '')
            if created_at:
                try:
                    # 处理ISO格式日期
                    if 'T' in created_at:
                        date_key = created_at.split('T')[0]
                    else:
                        date_key = created_at[:10]
                    
                    if date_key not in date_stats:
                        date_stats[date_key] = {"total": 0, "approved": 0}
                    date_stats[date_key]["total"] += 1
                    if conv.get('expert_verified', False):
                        date_stats[date_key]["approved"] += 1
                except Exception:
                    pass  # 忽略日期解析错误
            
            # 按智能体统计
            agent_name = conv.get('agent_name', 'unknown')
            if agent_name not in agent_stats:
                agent_stats[agent_name] = {"total": 0, "approved": 0}
            agent_stats[agent_name]["total"] += 1
            if conv.get('expert_verified', False):
                agent_stats[agent_name]["approved"] += 1
        
        return {
            "ret_code": "000000",
            "ret_msg": "操作成功",
            "data": {
                "user_id": user_id,
                "total_conversations": total_conversations,
                "approved_conversations": approved_conversations,
                "approval_rate": approved_conversations / total_conversations if total_conversations > 0 else 0,
                "date_stats": date_stats,
                "agent_stats": agent_stats,
                "generated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"获取记忆统计失败: {e}", exc_info=True)
        return {
            "ret_code": "999999",
            "ret_msg": f"获取统计失败: {str(e)}",
            "data": {}
        }


@router.post("/conversations/user-feedback")
async def user_feedback_conversation(request: UserFeedbackRequest):
    """
    用户对对话进行反馈 - 点赞或点踩
    
    Args:
        request: 用户反馈请求，包含系统回复内容和反馈类型
        
    Returns:
        操作结果
    """
    logger.info(f"用户反馈: response='{request.response[:50]}...', approved={request.user_approved}")
    
    try:
        # 验证反馈类型
        if request.user_approved not in [0, 1]:
            return {
                "ret_code": "400001",
                "ret_msg": "无效的反馈类型，必须是 0（点踩）或 1（点赞）",
                "data": {}
            }
        
        # 调用底层处理函数
        success = await memory_manager.handle_user_feedback(
            response=request.response,
            user_approved=request.user_approved
        )
        
        if success:
            feedback_text = "点赞" if request.user_approved == 1 else "点踩"
            return {
                "ret_code": "000000",
                "ret_msg": f"用户{feedback_text}成功",
                "data": {
                    "response": request.response[:100] + "..." if len(request.response) > 100 else request.response,
                    "user_approved": request.user_approved,
                    "feedback_text": feedback_text,
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {
                "ret_code": "999998",
                "ret_msg": "用户反馈处理失败",
                "data": {
                    "response": request.response[:100] + "..." if len(request.response) > 100 else request.response,
                    "user_approved": request.user_approved
                }
            }
            
    except Exception as e:
        logger.error(f"用户反馈失败: {e}", exc_info=True)
        return {
            "ret_code": "999999",
            "ret_msg": f"用户反馈失败: {str(e)}",
            "data": {
                "response": request.response[:100] + "..." if len(request.response) > 100 else request.response,
                "user_approved": request.user_approved
            }
        }
