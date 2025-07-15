import time
from fastapi import APIRouter, HTTPException, Request
import json
from models import QuestionRecommendRequest, QuestionRecommendResponse, QuestionRecommendItem
from agents.airport_service import graph_manager
from common.logging import get_logger

# 使用专门的问题推荐日志记录器
logger = get_logger("api.question_recommend")
router = APIRouter(prefix="/api/v1/question-recommend", tags=["问题推荐"])
@router.post("/questions", response_model=QuestionRecommendResponse)
async def get_question_recommendations(request: QuestionRecommendRequest, http_request: Request):
    """
    获取问题推荐（非流式接口）
    
    基于用户的当前问题和上下文，推荐相关的后续问题
    """
    logger.info(f"收到问题推荐请求 - ThreadID: {request.thread_id}, UserID: {request.user_id}, Query: {request.query or 'None'}, HasImage: {bool(request.image)}")
    
    # 验证必要字段
    if not request.thread_id or not request.user_id:
        logger.error("问题推荐请求缺少必要字段")
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
        logger.info(f"开始处理问题推荐: {request.query or '图片输入'}")
        result = await graph_manager.process_chat_message(
            message=request.query or "图片识别和问题推荐",
            thread_id=threads,
            graph_id="question_recommend_graph",
        )
        logger.info(f"返回结果类型: {type(result)},{result}")
        recommended_questions = json.loads(result)
        processing_time = round(time.time() - start_time, 2)     
        # 构造响应
        response_item = QuestionRecommendItem(
            thread_id=request.thread_id,
            user_id=request.user_id,
            recommended_questions=recommended_questions,
            processing_time=f"{processing_time}s"
        )
        
        return QuestionRecommendResponse(
            ret_code="000000",
            ret_msg="操作成功",
            item=response_item.dict()
        )
        
    except Exception as e:
        logger.error(f"问题推荐处理异常: {str(e)}", exc_info=True)
        
        # 返回错误响应
        error_item = QuestionRecommendItem(
            thread_id=request.thread_id,
            user_id=request.user_id,
            recommended_questions=["是否可以携带小刀上飞机？", "充电宝可以放在随身行李里吗？", "充电宝的安全检查要求是什么？"],
            processing_time="0s"
        )
        
        return QuestionRecommendResponse(
            ret_code="999999",
            ret_msg="问题推荐服务暂时不可用",
            item=error_item.dict()
        )