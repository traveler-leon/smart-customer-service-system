import os
import asyncio
from typing import List, Dict, Any, Union
import aiohttp

from ..base.interfaces import AsyncLLMProvider

class QwenLLM(AsyncLLMProvider):
    """千问AI异步LLM实现"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.temperature = self.config.get("temperature", 0.7)
        self.api_key = self.config.get("api_key", os.getenv("OPENAI_API_KEY"))
        self.base_url = self.config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.session = None
    
    async def _ensure_session(self):
        """确保HTTP会话已初始化"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
    
    async def close(self):
        """关闭异步会话"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def system_message(self, message: str) -> Dict[str, str]:
        """创建系统消息"""
        return {"role": "system", "content": message}
    
    def user_message(self, message: str) -> Dict[str, str]:
        """创建用户消息"""
        return {"role": "user", "content": message}
    
    def assistant_message(self, message: str) -> Dict[str, str]:
        """创建助手消息"""
        return {"role": "assistant", "content": message}
    
    async def generate_embedding(self, data: str, **kwargs) -> List[float]:
        """异步生成文本嵌入向量"""
        await self._ensure_session()
        
        model = kwargs.get("embedding_model", self.config.get("embedding_model", "bge-large-zh"))
        
        url = f"{self.base_url}/embeddings"
        payload = {
            "model": model,
            "input": data
        }
        
        async with self.session.post(url, json=payload) as response:
            result = await response.json()
            
            if response.status != 200:
                raise Exception(f"嵌入生成失败: {result.get('error', {}).get('message', 'Unknown error')}")
            
            return result["data"][0]["embedding"]
    
    async def submit_prompt(self, prompt: Union[str, List[Dict[str, str]]], **kwargs) -> str:
        """异步提交提示并返回响应"""
        await self._ensure_session()
        
        if prompt is None or (isinstance(prompt, str) and len(prompt) == 0):
            raise ValueError("提示不能为空")
        
        # 转换字符串提示为消息格式
        if isinstance(prompt, str):
            messages = [self.user_message(prompt)]
        else:
            messages = prompt
        
        # 计算token数量（近似）
        num_tokens = 0
        for message in messages:
            num_tokens += len(message["content"]) / 4
        
        # 确定模型
        model = kwargs.get("model", self.config.get("model", None))
        engine = kwargs.get("engine", self.config.get("engine", None))
        
        if model is None and engine is None:
            # 根据token数量自动选择模型
            if num_tokens > 3500:
                model = "qwen-long"
            else:
                model = "qwen-plus"
        
        # 构建请求体
        payload = {
            "model": model if model else engine,
            "messages": messages,
            "temperature": self.temperature,
        }
        
        # 异步API调用
        url = f"{self.base_url}/chat/completions"
        
        async with self.session.post(url, json=payload) as response:
            result = await response.json()
            
            if response.status != 200:
                raise Exception(f"LLM响应失败: {result.get('error', {}).get('message', 'Unknown error')}")
            
            return result["choices"][0]["message"]["content"]
