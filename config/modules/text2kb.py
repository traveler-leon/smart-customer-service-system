"""
知识库检索模块配置文件
"""
import os
# 知识库默认配置
TEXT2KB_CONFIG = {
    "kb_address": os.environ.get("KB_ADDRESS"),  # 替换为实际地址
    "kb_api_key": os.environ.get("KB_API_KEY")
}