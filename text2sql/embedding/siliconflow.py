import os
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional

from ..base.interfaces import AsyncEmbeddingProvider
from common.logging import get_logger

# 获取日志记录器
logger = get_logger("text2sql.embedding.openai")

class SiliconflowEmbedding(AsyncEmbeddingProvider):
    """基于硅基流动AI的嵌入模型提供者
    
    支持硅基流动AI的嵌入模型
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", os.getenv("OPENAI_API_KEY"))
        self.base_url = self.config.get("base_url", "https://api.openai.com/v1")
        self.api_version = self.config.get("api_version", None)  # 用于Azure OpenAI
        self.embedding_model = self.config.get("embedding_model", "text-embedding-ada-002")
        self.dimensions = self.config.get("dimensions", 1024)
        self.max_tokens = self.config.get("max_tokens", 512)
        self.client = None
        
        logger.info(f"初始化OpenAI兼容嵌入模型提供者，模型: {self.embedding_model}")
    
    def _ensure_client(self):
        """确保客户端已初始化"""
        if self.client is None:
            client_params = {
                "api_key": self.api_key,
                "base_url": self.base_url
            }
            
            # 对于Azure OpenAI，添加api_version
            if self.api_version:
                client_params["api_version"] = self.api_version
                
            self.client = AsyncOpenAI(**client_params)
            logger.debug("OpenAI兼容异步客户端已初始化")
    
    async def close(self):
        """关闭客户端资源"""
        # AsyncOpenAI客户端会自动管理资源
        self.client = None
        logger.debug("OpenAI兼容异步客户端已重置")
    
    async def generate_embedding(self, data: str, **kwargs) -> List[float]:
        """异步生成文本嵌入向量"""
        self._ensure_client()        
        try:
            # 可能的额外参数
            request_args = {
                "model": self.embedding_model,
                "input": data[:self.max_tokens],
                "encoding_format": "float"
            }

            request_args["dimensions"] = self.dimensions
            print("embedding参数",request_args)
            response = await self.client.embeddings.create(**request_args)
            
            embedding = response.data[0].embedding
            tokens_used = getattr(response.usage, "total_tokens", 0)
            logger.debug(f"成功生成嵌入向量，维度: {len(embedding)}，使用token: {tokens_used}")
            return {"embedding":embedding,"tokens_used":tokens_used}
            
        except Exception as e:
            logger.error(f"嵌入生成过程中发生错误: {str(e)}", exc_info=True)
            raise 