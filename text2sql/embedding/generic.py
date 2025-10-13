import os
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional

from ..base.interfaces import AsyncEmbeddingProvider
from common.logging import get_logger

class GenericEmbedding(AsyncEmbeddingProvider):
    """通用异步嵌入模型实现
    
    基于OpenAI兼容接口的通用嵌入模型实现
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化嵌入模型实例
        
        Args:
            config: 配置参数，必须包含：
                - base_url: API端点URL
                - embedding_model: 模型名称
                - api_key: API密钥（可选，默认从环境变量获取）
                其他可选参数：
                - dimensions: 向量维度（默认1536）
                - max_tokens: 最大token数（默认512）
                - name: 提供商名称（用于日志，默认为"Generic"）
                - api_version: API版本（用于Azure OpenAI）
        """
        if not config:
            raise ValueError("配置参数不能为空")
        
        # 必需参数验证
        required_params = ["base_url", "embedding_model"]
        missing_params = [param for param in required_params if not config.get(param)]
        if missing_params:
            raise ValueError(f"缺少必需的配置参数: {missing_params}")
        
        self.config = config
        self.base_url = config["base_url"]
        self.embedding_model = config["embedding_model"]
        self.api_key = config.get("api_key", os.getenv("OPENAI_API_KEY"))
        self.dimensions = config.get("dimensions", 1536)
        self.max_tokens = config.get("max_tokens", 512)
        self.client = None
        
        # 创建logger
        logger_name = config.get("logger_name", "text2sql.embedding.generic")
        self.logger = get_logger(logger_name)
        self.logger.info(f"初始化GenericEmbedding，模型: {self.embedding_model}, 端点: {self.base_url}")
    
    def _ensure_client(self):
        """确保客户端已初始化"""
        if self.client is None:
            if not self.api_key:
                raise ValueError(f"缺少API密钥，请设置api_key配置或OPENAI_API_KEY环境变量")
            
            client_params = {
                "api_key": self.api_key,
                "base_url": self.base_url
            }
                
            self.client = AsyncOpenAI(**client_params)
            self.logger.debug(f"异步客户端已初始化")
    
    async def close(self):
        """关闭客户端资源"""
        # AsyncOpenAI客户端会自动管理资源
        self.client = None
        self.logger.debug(f"异步客户端已重置")
    
    async def generate_embedding(self, data: str, **kwargs) -> Dict[str, Any]:
        """异步生成文本嵌入向量"""
        self._ensure_client()
        
        try:
            # 合并kwargs中的参数
            request_args = {
                "model": self.embedding_model,
                "input": data[:self.max_tokens],
                "encoding_format": "float"
            }
            
            # 如果支持dimensions参数，添加它
            # if self.dimensions:
            #     request_args["dimensions"] = self.dimensions
            
            # 从kwargs中提取OpenAI API支持的参数
            openai_params = ["user", "encoding_format"]
            for param in openai_params:
                if param in kwargs:
                    request_args[param] = kwargs[param]
            
            response = await self.client.embeddings.create(**request_args)
            
            embedding = response.data[0].embedding
            tokens_used = getattr(response.usage, "total_tokens", 0)
            
            self.logger.debug(
                f"成功生成嵌入向量，维度: {len(embedding)}，使用token: {tokens_used}"
            )
            
            return {
                "embedding": embedding,
                "tokens_used": tokens_used
            }
            
        except Exception as e:
            self.logger.error(f"嵌入生成过程中发生错误: {str(e)}", exc_info=True)
            raise
