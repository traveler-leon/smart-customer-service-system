"""
知识库检索模块配置文件
"""
import os
# 知识库默认配置
TEXT2KB_CONFIG = {
    "kb_address": os.environ.get("KB_ADDRESS"),  # 替换为实际地址
    "kb_api_key": os.environ.get("KB_API_KEY"),
    "kb_dataset_name": os.environ.get("KB_DATASET_NAME"),
    "kb_similarity_threshold": os.environ.get("KB_SIMILARITY_THRESHOLD"),
    "kb_vector_similarity_weight": os.environ.get("KB_VACTOR_SIMILARITY_WEIGHT"),
    "kb_topK": os.environ.get("KB_TOPK"),
    "kb_key_words": os.environ.get("KB_KEY_WORDS")
}