import time
from fastapi import APIRouter, HTTPException, Request
import json
from models import BusinessRecommendRequest, BusinessRecommendResponse, BusinessRecommendItem
from agents.airport_service import graph_manager
from common.logging import get_logger

# 使用专门的商业推荐日志记录器
logger = get_logger("api.business_recommend")
router = APIRouter(prefix="/api/v1/business-recommend", tags=["商业推荐"])
@router.post("/business", response_model=BusinessRecommendResponse)
async def get_business_recommendations(request: BusinessRecommendRequest, http_request: Request):
    """
    获取商业推荐（非流式接口）
    
    基于用户的当前问题和上下文，推荐相关的机场业务
    """
    logger.info(f"收到商业推荐请求 - ThreadID: {request.thread_id}, UserID: {request.user_id}, Query: {request.query or 'None'}, HasImage: {bool(request.image)}")
    
    # 验证必要字段
    if not request.thread_id or not request.user_id:
        logger.error("商业推荐请求缺少必要字段")
        raise HTTPException(status_code=400, detail="thread_id和user_id为必填字段")
    
    # query和image的验证已在模型层面完成，这里不需要额外验证
    
    # 获取请求头中的token
    token = http_request.headers.get("token", "")
    
    # 处理metadata，提取系统参数
    metadata = request.metadata or {}
    Is_translate = metadata.get("Is_translate", False)
    Is_emotion = metadata.get("Is_emotion", False)
    # Is_translate = True
    # Is_emotion = True
    
    try:
        start_time = time.time()
        # 处理图片数据
        image_data = None
        if request.image:
            image_data = {
                "filename": request.image.filename,
                "content_type": request.image.content_type,
                "data": request.image.data
            }
        
        # 构建线程配置
        threads = {
            "configurable": {
                "passenger_id": request.user_id,
                "thread_id": request.thread_id,
                "user_query": request.query or "",
                "image_data": image_data,
                "token": token,
                "Is_translate": Is_translate,
                "Is_emotion": Is_emotion
            }
        } 
        logger.info(f"开始处理商业推荐: {request.query or '图片输入'}")
        result = await graph_manager.process_chat_message(
            message=request.query or "图片识别和商业推荐",
            thread_id=threads,
            graph_id="business_recommend_graph",
        )
        logger.info(f"返回结果类型: {type(result)},{result}")
        recommended_business = json.loads(result)
        processing_time = round(time.time() - start_time, 2)     
        # 构造响应
        response_item = BusinessRecommendItem(
            thread_id=request.thread_id,
            user_id=request.user_id,
            recommended_business=recommended_business,
            processing_time=f"{processing_time}s"
        )
        
        return BusinessRecommendResponse(
            ret_code="000000",
            ret_msg="操作成功",
            item=response_item.dict()
        )
        
    except Exception as e:
        logger.error(f"商业推荐处理异常: {str(e)}", exc_info=True)
        
        # 返回错误响应
        error_item = BusinessRecommendItem(
            thread_id=request.thread_id,
            user_id=request.user_id,
            recommended_business=["轮椅租赁服务", "无人陪伴儿童服务", "特殊餐食申请", "行李寄存服务", "贵宾休息室服务"],
            processing_time="0s"
        )
        
        return BusinessRecommendResponse(
            ret_code="999999",
            ret_msg="商业推荐服务暂时不可用",
            item=error_item.dict()
        )