"""
知识库检索模块配置文件
"""
import os
# 知识库默认配置
TEXT2KB_CONFIG = {
    "kb_address": os.getenv("KB_ADDRESS"),  # 替换为实际地址
    "kb_api_key": os.getenv("KB_API_KEY"),
    "kb_dataset_name": os.getenv("KB_DATASET_NAME"),
    "kb_similarity_threshold": os.getenv("KB_SIMILARITY_THRESHOLD"),
    "kb_vector_similarity_weight": os.getenv("KB_VACTOR_SIMILARITY_WEIGHT"),
    "kb_topK": os.getenv("KB_TOPK"),
    "kb_key_words": os.getenv("KB_KEY_WORDS"),
    "reranker_model": os.getenv("RERANKER_MODEL"),
    "reranker_address": os.getenv("RERANKER_ADDRESS")
}