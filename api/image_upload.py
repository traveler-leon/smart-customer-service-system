from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional
import json
import base64
from common.image_handler import default_image_handler
from common.logging import get_logger

logger = get_logger("image_upload")

image_router = APIRouter(prefix="/api/v1/images", tags=["图片上传"])

@image_router.post("/upload")
async def upload_image(request: Request, file: UploadFile = File(...)):
    """
    标准文件上传接口
    支持multipart/form-data格式的文件上传
    """
    try:
        # 检查文件类型
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图片文件上传")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 转换为base64格式，以便使用统一的图片处理工具类
        base64_data = base64.b64encode(file_content).decode('utf-8')
        
        # 构造图片数据字典
        image_data = {
            "filename": file.filename,
            "content_type": file.content_type,
            "data": base64_data
        }
        
        # 获取基础URL
        base_url = str(request.base_url)
        
        # 使用图片处理工具类
        result = default_image_handler.process_image(image_data, base_url)
        
        logger.info(f"✅ 文件上传成功: {result['image_url']}")
        
        return JSONResponse(content={
            "success": True,
            "message": "图片上传成功",
            "data": {
                "filename": result['filename'],
                "url": result['image_url'],
                "file_path": result['file_path']
            }
        })
        
    except ValueError as e:
        logger.error(f"❌ 图片验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ 图片上传失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="图片上传失败")

@image_router.post("/upload-base64")
async def upload_image_base64(request: Request):
    """
    Base64格式图片上传接口
    支持JSON格式的base64图片数据
    """
    try:
        # 获取请求体
        body = await request.json()
        
        # 验证必要字段
        if "image" not in body:
            raise HTTPException(status_code=400, detail="缺少图片数据")
        
        image_data = body["image"]
        
        # 获取基础URL
        base_url = str(request.base_url)
        
        # 使用图片处理工具类
        result = default_image_handler.process_image(image_data, base_url)
        
        logger.info(f"✅ Base64图片上传成功: {result['image_url']}")
        
        return JSONResponse(content={
            "success": True,
            "message": "图片上传成功",
            "data": {
                "filename": result['filename'],
                "url": result['image_url'],
                "file_path": result['file_path']
            }
        })
        
    except ValueError as e:
        logger.error(f"❌ 图片验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ 图片上传失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="图片上传失败")

@image_router.delete("/delete")
async def delete_image(file_path: str):
    """
    删除图片接口
    """
    try:
        # 安全检查：确保文件路径在允许的目录内
        if not file_path.startswith("static/uploads/"):
            raise HTTPException(status_code=400, detail="无效的文件路径")
        
        # 使用图片处理工具类删除文件
        success = default_image_handler.delete_image(file_path)
        
        if success:
            return JSONResponse(content={
                "success": True,
                "message": "图片删除成功"
            })
        else:
            raise HTTPException(status_code=404, detail="图片文件不存在")
            
    except Exception as e:
        logger.error(f"❌ 图片删除失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="图片删除失败") 