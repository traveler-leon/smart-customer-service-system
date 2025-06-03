import os
import asyncio
from typing import List, Dict, Any, Union
from openai import AsyncOpenAI

from ..base.interfaces import AsyncLLMProvider
from common.logging import get_logger

# 获取日志记录器
logger = get_logger("text2sql.llm.qwen")

class SiliconflowLLM(AsyncLLMProvider):
    """硅基流动AI异步LLM实现
    
    基于OpenAI兼容接口的硅基流动大语言模型
    支持通过硅基流动AI提供的兼容接口访问
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.temperature = self.config.get("temperature", 0.7)
        self.api_key = self.config.get("api_key", os.getenv("OPENAI_API_KEY"))
        self.base_url = self.config.get("base_url", "https://api.siliconflow.cn/v1")
        self.model = self.config.get("model", "Qwen/Qwen2.5-72B-Instruct")
        self.max_tokens = self.config.get("max_tokens", 20000)
        self.client = None
        
        logger.info(f"初始化硅基流动LLM提供者，模型: {self.model}")
    
    def _ensure_client(self):
        """确保客户端已初始化"""
        if self.client is None:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.debug("硅基流动AI异步客户端已初始化")
    
    async def close(self):
        """关闭异步会话"""
        # AsyncOpenAI 客户端会自动管理会话，不需要手动关闭
        self.client = None
        logger.debug("硅基流动AI异步客户端已重置")
    
    def system_message(self, message: str) -> Dict[str, str]:
        """创建系统消息"""
        return {"role": "system", "content": message}
    
    def user_message(self, message: str) -> Dict[str, str]:
        """创建用户消息"""
        return {"role": "user", "content": message}
    
    def assistant_message(self, message: str) -> Dict[str, str]:
        """创建助手消息"""
        return {"role": "assistant", "content": message}
    
    async def submit_prompt(self, prompt: Union[str, List[Dict[str, str]]], **kwargs) -> str:
        """异步提交提示并返回响应"""
        self._ensure_client()
        
        if prompt is None or (isinstance(prompt, str) and len(prompt) == 0):
            raise ValueError("提示不能为空")
        
        # 转换字符串提示为消息格式
        if isinstance(prompt, str):
            messages = [self.user_message(prompt)]
        else:
            messages = prompt
        
        
        try:
            # 使用 AsyncOpenAI 客户端调用 API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )
            
            content = response.choices[0].message.content
            input_tokens_used = getattr(response.usage, "prompt_tokens", 0)
            output_tokens_used = getattr(response.usage, "completion_tokens", 0)
            logger.debug(f"成功生成LLM响应，使用token: {input_tokens_used} + {output_tokens_used}")
            return {"content":content,"input_tokens_used":input_tokens_used,"output_tokens_used":output_tokens_used}
            
        except Exception as e:
            logger.error(f"LLM响应生成过程中发生错误: {str(e)}", exc_info=True)
            raise
