import os
import base64
import time
import uuid
from typing import Optional, Dict, Any
from fastapi import HTTPException
from common.logging import get_logger

logger = get_logger("image_handler")

class ImageHandler:
    """图片处理工具类，用于处理图片上传、保存和URL生成"""
    
    def __init__(self, 
                 upload_dir: str = "static/uploads",
                 allowed_types: list = None,
                 max_size: int = 10 * 1024 * 1024):  # 10MB
        """
        初始化图片处理器
        
        Args:
            upload_dir: 上传目录
            allowed_types: 允许的图片类型
            max_size: 最大文件大小（字节）
        """
        self.upload_dir = upload_dir
        self.allowed_types = allowed_types or [
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
        ]
        self.max_size = max_size
        
        # 确保上传目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def validate_image_data(self, image_data: Dict[str, Any]) -> bool:
        """
        验证图片数据格式
        
        Args:
            image_data: 图片数据字典
            
        Returns:
            bool: 验证结果
        """
        if not isinstance(image_data, dict):
            return False
            
        required_fields = ['filename', 'content_type', 'data']
        for field in required_fields:
            if field not in image_data:
                logger.warning(f"图片数据缺少必要字段: {field}")
                return False
        
        # 检查文件类型
        content_type = image_data.get('content_type', '').lower()
        if content_type not in self.allowed_types:
            logger.warning(f"不支持的图片类型: {content_type}")
            return False
        
        # 检查base64数据
        base64_data = image_data.get('data', '')
        if not base64_data:
            logger.warning("图片数据为空")
            return False
            
        try:
            # 验证base64格式并检查文件大小
            decoded_data = base64.b64decode(base64_data)
            if len(decoded_data) > self.max_size:
                logger.warning(f"图片文件过大: {len(decoded_data)} bytes, 最大允许: {self.max_size} bytes")
                return False
        except Exception as e:
            logger.warning(f"Base64解码失败: {str(e)}")
            return False
            
        return True
    
    def generate_unique_filename(self, original_filename: str) -> str:
        """
        生成唯一的文件名
        
        Args:
            original_filename: 原始文件名
            
        Returns:
            str: 唯一文件名
        """
        # 确保文件名安全
        safe_filename = os.path.basename(original_filename)
        
        # 获取文件扩展名
        name, ext = os.path.splitext(safe_filename)
        if not ext:
            ext = '.jpg'  # 默认扩展名
        
        # 生成唯一标识
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        
        # 构建唯一文件名
        unique_filename = f"{timestamp}_{unique_id}_{name}{ext}"
        
        return unique_filename
    
    def save_image(self, image_data: Dict[str, Any]) -> str:
        """
        保存图片到本地
        
        Args:
            image_data: 图片数据字典
            
        Returns:
            str: 保存的文件路径
            
        Raises:
            ValueError: 图片数据验证失败
            IOError: 文件保存失败
        """
        # 验证图片数据
        if not self.validate_image_data(image_data):
            raise ValueError("图片数据验证失败")
        
        try:
            # 生成唯一文件名
            original_filename = image_data['filename']
            unique_filename = self.generate_unique_filename(original_filename)
            
            # 构建完整文件路径
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # 解码并保存图片
            base64_data = image_data['data']
            image_binary = base64.b64decode(base64_data)
            
            with open(file_path, 'wb') as f:
                f.write(image_binary)
            
            logger.info(f"✅ 图片已保存: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"❌ 图片保存失败: {str(e)}", exc_info=True)
            raise IOError(f"图片保存失败: {str(e)}")
    
    def generate_url(self, file_path: str, base_url: str) -> str:
        """
        生成图片访问URL
        
        Args:
            file_path: 文件路径
            base_url: 基础URL
            
        Returns:
            str: 图片访问URL
        """
        # 获取相对于upload_dir的路径
        filename = os.path.basename(file_path)
        
        # 构建访问URL
        url = f"{base_url.rstrip('/')}/static/uploads/{filename}"
        
        return url
    
    def process_image(self, image_data: Dict[str, Any], base_url: str) -> Dict[str, str]:
        """
        处理图片上传（验证、保存、生成URL）
        
        Args:
            image_data: 图片数据字典
            base_url: 基础URL
            
        Returns:
            Dict[str, str]: 包含文件路径和URL的字典
            
        Raises:
            ValueError: 图片处理失败
        """
        try:
            # 保存图片
            file_path = self.save_image(image_data)
            
            # 生成访问URL
            image_url = self.generate_url(file_path, base_url)
            
            return {
                'file_path': file_path,
                'image_url': image_url,
                'filename': os.path.basename(file_path)
            }
            
        except Exception as e:
            logger.error(f"❌ 图片处理失败: {str(e)}", exc_info=True)
            raise ValueError(f"图片处理失败: {str(e)}")
    
    def delete_image(self, file_path: str) -> bool:
        """
        删除图片文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 删除结果
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"✅ 图片已删除: {file_path}")
                return True
            else:
                logger.warning(f"⚠️ 图片文件不存在: {file_path}")
                return False
        except Exception as e:
            logger.error(f"❌ 图片删除失败: {str(e)}", exc_info=True)
            return False


# 创建默认的图片处理器实例
default_image_handler = ImageHandler() 