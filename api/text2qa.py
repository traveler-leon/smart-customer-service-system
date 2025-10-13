"""
简化的text2qa API接口
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field
import base64

from agents.airport_service.context_engineering.memory_manager import memory_manager
from common.logging import get_logger
logger = get_logger("api.simple_text2qa")


# 创建路由器
router = APIRouter(prefix="/text2qa", tags=["text2qa"])

# 导入图片相关模型
from models.schemas import ImageData

# Pydantic模型
class QAPair(BaseModel):
    question: str = Field(..., description="问题")
    answer: str = Field(..., description="答案")
    tags: Optional[List[str]] = Field(default=[], description="标签列表")
    images: Optional[List[ImageData]] = Field(default=[], description="图片数据列表")
    services: Optional[List[str]] = Field(default=[], description="服务列表")
    extra_fields: Optional[Dict[str, Any]] = Field(default={}, description="扩展字段")

class QAPairBatch(BaseModel):
    qa_pairs: List[QAPair] = Field(..., description="QA对列表")

class QAResponse(BaseModel):
    id: str
    question: str
    answer: str
    tags: List[str]
    images: Optional[List[str]] = []  # 简化为data URL字符串列表
    services: Optional[List[str]] = []
    extra_fields: Optional[Dict[str, Any]] = {}
    created_at: float

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Any = None


def process_images(images: List[ImageData]) -> Dict[str, Any]:
    """
    处理图片数据，生成data URL格式
    
    Args:
        images: 图片数据列表
        
    Returns:
        image_urls: 图片data URL列表
    """
    if not images:
        return []
    
    image_urls = []
    
    for image_data in images:
        try:
            image_type = image_data.content_type.split('/')[-1] if '/' in image_data.content_type else 'jpeg'
            data_url = f"data:image/{image_type};base64,{image_data.data}"
            # 保存URL和完整信息
            image_urls.append(data_url)
            
        except Exception as e:
            logger.error(f"处理图片失败: {str(e)}")
            continue
    
    return image_urls


@router.post("/qa", response_model=APIResponse)
async def add_qa_pair(qa_pair: QAPair, request: Request):
    """添加单个QA对 - 先添加到专家库，再添加到Redis"""
    try:
        # 确保记忆管理器已初始化
        await memory_manager.initialize()
        
        # 处理图片数据
        image_result = process_images(qa_pair.images or [])
        
        # 1. 先添加到专家库
        expert_memory_id = await memory_manager.add_expert_qa(
            question=qa_pair.question,
            answer=qa_pair.answer,
            expert_id=qa_pair.extra_fields.get("expert_id", "") if qa_pair.extra_fields else "",
            application_id=qa_pair.extra_fields.get("application_id", "主智能客服") if qa_pair.extra_fields else "主智能客服",
            metadata={
                "tags": "||".join(qa_pair.tags) if qa_pair.tags and isinstance(qa_pair.tags, list) else "",
                "images": "||".join(image_result) if image_result and isinstance(image_result, list) else "",
                "services": "||".join(qa_pair.services) if qa_pair.services and isinstance(qa_pair.services, list) else "",
                **(qa_pair.extra_fields or {})
            }
        )
        
        return APIResponse(
            success=True,
            message="QA对添加成功",
            data={
                "expert_memory_id": expert_memory_id,
                "processed_images": image_result["image_urls"]
            }
        )
    except Exception as e:
        logger.error(f"添加QA对失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/qa/batch", response_model=APIResponse)
async def add_qa_pairs_batch(qa_batch: QAPairBatch, request: Request):
    """批量添加QA对 - 先添加到专家库，再添加到Redis"""
    try:
        # 确保记忆管理器已初始化
        await memory_manager.initialize()
        
        expert_memory_ids = []
        redis_qa_ids = []
        failed_count = 0
        all_processed_images = []
        
        # 1. 先批量添加到专家库
        for qa_pair in qa_batch.qa_pairs:
            try:
                # 处理图片数据
                image_result = process_images(qa_pair.images or [])
                all_processed_images.append(image_result)
                expert_memory_id = await memory_manager.add_expert_qa(
                    question=qa_pair.question,
                    answer=qa_pair.answer,
                    expert_id=qa_pair.extra_fields.get("expert_id", "") if qa_pair.extra_fields else "",
                    application_id=qa_pair.extra_fields.get("application_id", "simple_text2qa") if qa_pair.extra_fields else "simple_text2qa",
                    metadata={
                        "tags": "||".join(qa_pair.tags) if qa_pair.tags and isinstance(qa_pair.tags, list) else "",
                        "images": "||".join(image_result) if image_result and isinstance(image_result, list) else "",
                        "services": "||".join(qa_pair.services) if qa_pair.services and isinstance(qa_pair.services, list) else "",
                        **(qa_pair.extra_fields or {})
                    }
                )
                expert_memory_ids.append(expert_memory_id)
            except Exception as single_error:
                logger.error(f"添加单个专家QA失败: {str(single_error)}")
                failed_count += 1
                expert_memory_ids.append(None)
                all_processed_images.append([])
        
        success_count = len(qa_batch.qa_pairs) - failed_count
        
        return APIResponse(
            success=True,
            message=f"批量添加完成，成功{success_count}个，失败{failed_count}个QA对",
            data={
                "expert_memory_ids": expert_memory_ids,
                "success_count": success_count,
                "failed_count": failed_count,
                "processed_images": all_processed_images
            }
        )
    except Exception as e:
        logger.error(f"批量添加QA对失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/qa", response_model=APIResponse)
async def get_all_qa():
    """获取所有QA对 - 返回完整的专家QA列表"""
    try:
        # 确保记忆管理器已初始化
        await memory_manager.initialize()
        
        # 获取所有专家QA
        expert_results = await memory_manager.get_expert_qa_list(
            limit=100000
        )
        
        if expert_results:
            # 转换为标准的QAResponse格式
            qa_list = []
            for expert_qa in expert_results:
                # 处理images字段 - 解析多个data URL
                images_value = expert_qa.get('images', '')
                images_list = []
                if images_value and images_value.strip():
                    # 如果有图片data URL，按||分隔符分割解析多个图片
                    images_list = [img.strip() for img in images_value.split('||') if img.strip()]
                
                qa_response = QAResponse(
                    id=expert_qa.get('memory_id', ''),
                    question=expert_qa.get('question', ''),
                    answer=expert_qa.get('answer', ''),
                    tags=expert_qa.get('tags', '').split('||') if expert_qa.get('tags') else [],
                    images=images_list,
                    services=expert_qa.get('services', '').split('||') if expert_qa.get('services') else [],
                    extra_fields={
                        "expert_id": expert_qa.get('expert_id', ''),
                        "application_id": expert_qa.get('application_id', '')
                    },
                    created_at=0  # 专家QA不使用时间戳
                ).model_dump()
                qa_list.append(qa_response)
            
            return APIResponse(
                success=True,
                message=f"获取所有QA对成功，共{len(qa_list)}条",
                data=qa_list
            )
        else:
            return APIResponse(
                success=True,
                message="暂无QA对",
                data=[]
            )
            
    except Exception as e:
        logger.error(f"获取所有QA对失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class DeleteQARequest(BaseModel):
    id: str = Field(..., description="专家库memory_id")
    query: str = Field(..., description="问题内容，用于生成Redis哈希ID")

@router.delete("/qa", response_model=APIResponse)
async def delete_qa_pair(request: DeleteQARequest):
    """删除QA对 - 同时从专家库和Redis删除"""
    try:
        # 确保记忆管理器已初始化
        await memory_manager.initialize()
        
        expert_deleted = False
        redis_deleted = False
        
        # 1. 从专家库删除（使用memory_id）
        try:
            expert_deleted = await memory_manager.delete_expert_qa(request.id)
        except Exception as expert_error:
            logger.error(f"从专家库删除失败: {str(expert_error)}")
        
        except Exception as redis_error:
            logger.error(f"从Redis删除失败: {str(redis_error)}")
        
        # 判断删除结果
        if not expert_deleted and not redis_deleted:
            raise HTTPException(status_code=404, detail="QA对删除失败，可能不存在")
        
        result_data = {
            "expert_memory_id": request.id,
            "expert_deleted": expert_deleted,
            "redis_deleted": redis_deleted
        }
        
        return APIResponse(
            success=True,
            message=f"QA对删除完成，专家库{'成功' if expert_deleted else '失败'}，Redis{'成功' if redis_deleted else '失败'}",
            data=result_data
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除QA对失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/count", response_model=APIResponse)
async def get_qa_count():
    """获取QA对总数 - 统计专家库和Redis的总数"""
    try:
        # 确保记忆管理器已初始化
        await memory_manager.initialize()
        
        # 1. 统计专家库QA数量
        expert_count = 0
        try:
            expert_results = await memory_manager.get_expert_qa_list(
                application_id="simple_text2qa",
                limit=10000  # 设置一个很大的限制来获取所有结果
            )
            expert_count = len(expert_results)
        except Exception as expert_error:
            logger.error(f"统计专家库QA失败: {str(expert_error)}")
                
        return APIResponse(
            success=True,
            message="获取QA对总数成功",
            data={
                "expert_count": expert_count,
            }
        )
    except Exception as e:
        logger.error(f"获取QA对总数失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ping", response_model=APIResponse)
async def ping():
    """健康检查 - 检查专家库和Redis的连接状态"""
    try:
        # 检查专家库连接状态
        expert_alive = False
        try:
            await memory_manager.initialize()
            expert_alive = True
        except Exception as expert_error:
            logger.error(f"专家库连接检查失败: {str(expert_error)}")
        
        return APIResponse(
            success=True,
            message="健康检查完成",
            data={
                "expert_memory_alive": expert_alive,
            }
        )
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qa/with-upload", response_model=APIResponse)
async def add_qa_with_file_upload(
    request: Request,
    question: str,
    answer: str,
    tags: Optional[str] = "",
    services: Optional[str] = "",
    expert_id: Optional[str] = "",
    application_id: Optional[str] = "主智能客服",
    files: List[UploadFile] = File(default=[])
):
    """
    通过文件上传的方式添加带图片的QA对
    支持多文件上传
    """
    try:
        # 处理上传的文件
        image_data_list = []
        if files:
            for file in files:
                if not file.content_type.startswith('image/'):
                    continue  # 跳过非图片文件
                
                file_content = await file.read()
                base64_data = base64.b64encode(file_content).decode('utf-8')
                
                image_data = ImageData(
                    filename=file.filename,
                    content_type=file.content_type,
                    data=base64_data
                )
                image_data_list.append(image_data)
        
        # 构建QAPair对象
        qa_pair = QAPair(
            question=question,
            answer=answer,
            tags=tags.split(',') if tags else [],
            images=image_data_list,
            services=services.split(',') if services else [],
            extra_fields={
                "expert_id": expert_id,
                "application_id": application_id
            }
        )
        
        # 调用现有的添加QA对功能
        return await add_qa_pair(qa_pair, request)
        
    except Exception as e:
        logger.error(f"添加QA对（文件上传）失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
