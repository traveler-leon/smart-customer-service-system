"""
通用验证器模块

提供项目中常用的数据验证功能
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class ValidationError(Exception):
    """验证错误异常"""
    pass


class Validator:
    """通用验证器类"""
    
    @staticmethod
    def is_not_empty(value: Any, field_name: str = "字段") -> Any:
        """
        验证值不为空
        
        Args:
            value: 要验证的值
            field_name: 字段名称
            
        Returns:
            验证通过的值
            
        Raises:
            ValidationError: 验证失败
        """
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise ValidationError(f"{field_name}不能为空")
        return value
    
    @staticmethod
    def is_string(value: Any, field_name: str = "字段", 
                  min_length: Optional[int] = None, 
                  max_length: Optional[int] = None) -> str:
        """
        验证字符串类型和长度
        
        Args:
            value: 要验证的值
            field_name: 字段名称
            min_length: 最小长度
            max_length: 最大长度
            
        Returns:
            验证通过的字符串
            
        Raises:
            ValidationError: 验证失败
        """
        if not isinstance(value, str):
            raise ValidationError(f"{field_name}必须是字符串类型")
        
        if min_length is not None and len(value) < min_length:
            raise ValidationError(f"{field_name}长度不能少于{min_length}个字符")
        
        if max_length is not None and len(value) > max_length:
            raise ValidationError(f"{field_name}长度不能超过{max_length}个字符")
        
        return value
    
    @staticmethod
    def is_integer(value: Any, field_name: str = "字段",
                   min_value: Optional[int] = None,
                   max_value: Optional[int] = None) -> int:
        """
        验证整数类型和范围
        
        Args:
            value: 要验证的值
            field_name: 字段名称
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            验证通过的整数
            
        Raises:
            ValidationError: 验证失败
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name}必须是整数")
        
        if min_value is not None and int_value < min_value:
            raise ValidationError(f"{field_name}不能小于{min_value}")
        
        if max_value is not None and int_value > max_value:
            raise ValidationError(f"{field_name}不能大于{max_value}")
        
        return int_value
    
    @staticmethod
    def is_float(value: Any, field_name: str = "字段",
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None) -> float:
        """
        验证浮点数类型和范围
        
        Args:
            value: 要验证的值
            field_name: 字段名称
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            验证通过的浮点数
            
        Raises:
            ValidationError: 验证失败
        """
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name}必须是数字")
        
        if min_value is not None and float_value < min_value:
            raise ValidationError(f"{field_name}不能小于{min_value}")
        
        if max_value is not None and float_value > max_value:
            raise ValidationError(f"{field_name}不能大于{max_value}")
        
        return float_value
    
    @staticmethod
    def is_email(value: str, field_name: str = "邮箱") -> str:
        """
        验证邮箱格式
        
        Args:
            value: 要验证的邮箱
            field_name: 字段名称
            
        Returns:
            验证通过的邮箱
            
        Raises:
            ValidationError: 验证失败
        """
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValidationError(f"{field_name}格式不正确")
        return value
    
    @staticmethod
    def is_url(value: str, field_name: str = "URL") -> str:
        """
        验证URL格式
        
        Args:
            value: 要验证的URL
            field_name: 字段名称
            
        Returns:
            验证通过的URL
            
        Raises:
            ValidationError: 验证失败
        """
        url_pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
        if not re.match(url_pattern, value):
            raise ValidationError(f"{field_name}格式不正确")
        return value
    
    @staticmethod
    def is_phone(value: str, field_name: str = "手机号") -> str:
        """
        验证手机号格式（中国大陆）
        
        Args:
            value: 要验证的手机号
            field_name: 字段名称
            
        Returns:
            验证通过的手机号
            
        Raises:
            ValidationError: 验证失败
        """
        phone_pattern = r'^1[3-9]\d{9}$'
        if not re.match(phone_pattern, value):
            raise ValidationError(f"{field_name}格式不正确")
        return value
    
    @staticmethod
    def is_json(value: str, field_name: str = "JSON") -> Dict[str, Any]:
        """
        验证JSON格式
        
        Args:
            value: 要验证的JSON字符串
            field_name: 字段名称
            
        Returns:
            解析后的字典
            
        Raises:
            ValidationError: 验证失败
        """
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise ValidationError(f"{field_name}不是有效的JSON格式")
    
    @staticmethod
    def is_in_choices(value: Any, choices: List[Any], field_name: str = "字段") -> Any:
        """
        验证值在选择列表中
        
        Args:
            value: 要验证的值
            choices: 可选值列表
            field_name: 字段名称
            
        Returns:
            验证通过的值
            
        Raises:
            ValidationError: 验证失败
        """
        if value not in choices:
            raise ValidationError(f"{field_name}必须是以下值之一: {choices}")
        return value
    
    @staticmethod
    def is_datetime(value: str, field_name: str = "日期时间", 
                    format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        """
        验证日期时间格式
        
        Args:
            value: 要验证的日期时间字符串
            field_name: 字段名称
            format_str: 日期时间格式
            
        Returns:
            解析后的datetime对象
            
        Raises:
            ValidationError: 验证失败
        """
        try:
            return datetime.strptime(value, format_str)
        except ValueError:
            raise ValidationError(f"{field_name}格式不正确，应为: {format_str}")
    
    @staticmethod
    def validate_dict(data: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证字典数据
        
        Args:
            data: 要验证的数据
            schema: 验证模式
            
        Returns:
            验证通过的数据
            
        Raises:
            ValidationError: 验证失败
        """
        result = {}
        
        for field_name, field_schema in schema.items():
            value = data.get(field_name)
            
            # 检查必填字段
            if field_schema.get("required", False) and value is None:
                raise ValidationError(f"缺少必填字段: {field_name}")
            
            # 如果值为None且不是必填，跳过验证
            if value is None:
                continue
            
            # 根据类型进行验证
            field_type = field_schema.get("type")
            if field_type == "string":
                result[field_name] = Validator.is_string(
                    value, field_name,
                    field_schema.get("min_length"),
                    field_schema.get("max_length")
                )
            elif field_type == "integer":
                result[field_name] = Validator.is_integer(
                    value, field_name,
                    field_schema.get("min_value"),
                    field_schema.get("max_value")
                )
            elif field_type == "float":
                result[field_name] = Validator.is_float(
                    value, field_name,
                    field_schema.get("min_value"),
                    field_schema.get("max_value")
                )
            elif field_type == "email":
                result[field_name] = Validator.is_email(value, field_name)
            elif field_type == "url":
                result[field_name] = Validator.is_url(value, field_name)
            elif field_type == "phone":
                result[field_name] = Validator.is_phone(value, field_name)
            elif field_type == "json":
                result[field_name] = Validator.is_json(value, field_name)
            elif field_type == "datetime":
                result[field_name] = Validator.is_datetime(
                    value, field_name, field_schema.get("format", "%Y-%m-%d %H:%M:%S")
                )
            elif field_type == "choice":
                result[field_name] = Validator.is_in_choices(
                    value, field_schema.get("choices", []), field_name
                )
            else:
                result[field_name] = value
        
        return result
