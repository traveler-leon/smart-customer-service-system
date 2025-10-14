"""
知识库检索模块配置文件
"""
import os

llm_base_url = os.getenv("LLM_BASE_URL")

if "dashscope" in llm_base_url:
    reranker_add = 'https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank'
elif "bigmodel" in llm_base_url:
    reranker_add = 'https://open.bigmodel.cn/api/paas/v4/rerank'
elif 'siliconflow' in llm_base_url:
    reranker_add = "https://api.siliconflow.cn/v1/rerank"
else:
    reranker_add = llm_base_url+"/v1/rerank"

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
    "reranker_base_url": os.getenv("RERANKER_BASE_URL",reranker_add),
    "reranker_api_key": os.getenv("RERANKER_API_KEY",os.getenv("LLM_API_KEY"))
}