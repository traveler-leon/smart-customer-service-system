import os
from typing import List, Dict, Any, Union, Optional
from openai import AsyncOpenAI

from ..base.interfaces import AsyncLLMProvider
from common.logging import get_logger

class GenericLLM(AsyncLLMProvider):
    """通用异步LLM实现
    基于OpenAI兼容接口的通用大语言模型实现
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化LLM实例
        
        Args:
            config: 配置参数，必须包含：
                - base_url: API端点URL
                - model: 模型名称
                - api_key: API密钥（可选，默认从环境变量获取）
                其他可选参数：
                - temperature: 温度参数（默认0.7）
                - max_tokens: 最大token数（默认20000）
                - name: 提供商名称（用于日志，默认为"Generic"）
        """
        if not config:
            raise ValueError("配置参数不能为空")
        
        # 必需参数验证
        required_params = ["base_url", "model"]
        missing_params = [param for param in required_params if not config.get(param)]
        if missing_params:
            raise ValueError(f"缺少必需的配置参数: {missing_params}")
        
        self.config = config
        self.base_url = config["base_url"]
        self.model = config["model"]
        self.api_key = config.get("api_key", os.getenv("OPENAI_API_KEY"))
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 20000)
        self.client = None
        
        # 创建logger
        logger_name = config.get("logger_name", "text2sql.llm.generic")
        self.logger = get_logger(logger_name)
        self.logger.info(f"初始化GenericLLM，模型: {self.model}, 端点: {self.base_url}")
    
    def _ensure_client(self):
        """确保客户端已初始化"""
        if self.client is None:
            if not self.api_key:
                raise ValueError(f"缺少API密钥，请设置api_key配置或OPENAI_API_KEY环境变量")
            
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.logger.debug(f"GenericLLM异步客户端已初始化")
    
    async def close(self):
        """关闭异步会话"""
        # AsyncOpenAI 客户端会自动管理会话，不需要手动关闭
        self.client = None
        self.logger.debug(f"异步客户端已重置")
    
    def system_message(self, message: str) -> Dict[str, str]:
        """创建系统消息"""
        return {"role": "system", "content": message}
    
    def user_message(self, message: str) -> Dict[str, str]:
        """创建用户消息"""
        return {"role": "user", "content": message}
    
    def assistant_message(self, message: str) -> Dict[str, str]:
        """创建助手消息"""
        return {"role": "assistant", "content": message}
    
    async def submit_prompt(self, prompt: Union[str, List[Dict[str, str]]], **kwargs) -> Dict[str, Any]:
        """异步提交提示并返回响应"""
        self._ensure_client()
        
        if prompt is None or (isinstance(prompt, str) and len(prompt) == 0):
            raise ValueError("提示不能为空")
        
        # 转换字符串提示为消息格式
        if isinstance(prompt, str):
            messages = [self.user_message(prompt)]
        else:
            messages = prompt
        
        # 合并kwargs中的参数
        api_params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        
        # 从kwargs中提取OpenAI API支持的参数
        openai_params = ["max_tokens", "top_p", "frequency_penalty", "presence_penalty", "stop"]
        for param in openai_params:
            if param in kwargs:
                api_params[param] = kwargs[param]
        
        try:
            # 使用 AsyncOpenAI 客户端调用 API
            response = await self.client.chat.completions.create(**api_params)
            
            content = response.choices[0].message.content
            input_tokens_used = getattr(response.usage, "prompt_tokens", 0)
            output_tokens_used = getattr(response.usage, "completion_tokens", 0)
            
            self.logger.debug(
                f"成功生成LLM响应，使用token: {input_tokens_used} + {output_tokens_used}"
            )
            
            return {
                "content": content,
                "input_tokens_used": input_tokens_used,
                "output_tokens_used": output_tokens_used
            }
            
        except Exception as e:
            self.logger.error(f"LLM响应生成过程中发生错误: {str(e)}", exc_info=True)
            raise
