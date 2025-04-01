import hashlib
import os
import re
import uuid
from typing import Union

from .exceptions import ImproperlyConfigured, ValidationError
from common.logging import get_logger

# 获取text2sql模块的日志记录器
logger = get_logger("text2sql")

def validate_config_path(path):
    logger.debug(f"正在验证配置文件路径: {path}")
    if not os.path.exists(path):
        logger.error(f"配置文件不存在: {path}")
        raise ImproperlyConfigured(
            f'No such configuration file: {path}'
        )

    if not os.path.isfile(path):
        logger.error(f"配置路径不是文件: {path}")
        raise ImproperlyConfigured(
            f'Config should be a file: {path}'
        )

    if not os.access(path, os.R_OK):
        logger.error(f"无法读取配置文件，请检查权限: {path}")
        raise ImproperlyConfigured(
            f'Cannot read the config file. Please grant read privileges: {path}'
        )
    
    logger.info(f"配置文件验证通过: {path}")


def sanitize_model_name(model_name):
    logger.debug(f"正在清理模型名称: {model_name}")
    try:
        model_name = model_name.lower()

        # Replace spaces with a hyphen
        model_name = model_name.replace(" ", "-")

        if '-' in model_name:
            # remove double hyphones
            model_name = re.sub(r"-+", "-", model_name)
            if '_' in model_name:
                # If name contains both underscores and hyphen replace all underscores with hyphens
                model_name = re.sub(r'_', '-', model_name)

        # Remove special characters only allow underscore
        model_name = re.sub(r"[^a-zA-Z0-9-_]", "", model_name)

        # Remove hyphen or underscore if any at the last or first
        if model_name[-1] in ("-", "_"):
            model_name = model_name[:-1]
        if model_name[0] in ("-", "_"):
            model_name = model_name[1:]

        logger.debug(f"模型名称清理完成: {model_name}")
        return model_name
    except Exception as e:
        logger.error(f"模型名称清理失败: {str(e)}")
        raise ValidationError(e)


def deterministic_uuid(content: Union[str, bytes]) -> str:
    """Creates deterministic UUID on hash value of string or byte content.

    Args:
        content: String or byte representation of data.

    Returns:
        UUID of the content.
    """
    logger.debug("正在生成确定性UUID")
    try:
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        elif isinstance(content, bytes):
            content_bytes = content
        else:
            logger.error(f"不支持的内容类型: {type(content)}")
            raise ValueError(f"Content type {type(content)} not supported !")

        hash_object = hashlib.sha256(content_bytes)
        hash_hex = hash_object.hexdigest()
        namespace = uuid.UUID("00000000-0000-0000-0000-000000000000")
        content_uuid = str(uuid.uuid5(namespace, hash_hex))

        logger.debug(f"UUID生成成功: {content_uuid}")
        return content_uuid
    except Exception as e:
        logger.error(f"UUID生成失败: {str(e)}")
        raise