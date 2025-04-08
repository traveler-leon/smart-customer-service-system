"""
LLM工具函数
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


class LLMUtil:
    """LLM工具类"""
    
    def __init__(self, model_name="gpt-3.5-turbo-16k", temperature=0.3):
        """初始化LLM工具"""
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
        )
    
    def invoke(self, 
               messages: List[Dict[str, str]], 
               system_prompt: Optional[str] = None,
               output_format: Optional[str] = None):
        """调用LLM"""
        formatted_messages = []
        
        # 添加系统提示
        if system_prompt:
            formatted_messages.append(SystemMessage(content=system_prompt))
        
        # 添加聊天历史
        for message in messages:
            if message["role"] == "user":
                formatted_messages.append(HumanMessage(content=message["content"]))
            elif message["role"] == "assistant":
                formatted_messages.append(AIMessage(content=message["content"]))
            elif message["role"] == "system":
                formatted_messages.append(SystemMessage(content=message["content"]))
        
        # 如果需要格式化输出，添加格式说明
        if output_format:
            if formatted_messages[-1].type == "human":
                formatted_messages[-1] = HumanMessage(
                    content=f"{formatted_messages[-1].content}\n\n请以{output_format}格式返回结果。"
                )
            else:
                formatted_messages.append(SystemMessage(
                    content=f"请以{output_format}格式返回结果。"
                ))
        
        # 调用LLM
        response = self.llm.invoke(formatted_messages)
        return response.content
    
    def parse_json_response(self, text, default=None):
        """尝试解析JSON响应，如果失败则返回默认值"""
        try:
            # 查找文本中的JSON部分
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                return json.loads(json_str)
            return default
        except Exception:
            return default


# 创建默认LLM实例
default_llm = LLMUtil() 