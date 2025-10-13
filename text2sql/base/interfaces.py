from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import pandas as pd

class AsyncEmbeddingProvider(ABC):
    """异步嵌入模型提供者接口"""
    
    @abstractmethod
    async def generate_embedding(self, data: str, **kwargs) -> List[float]:
        """异步生成文本嵌入向量"""
        pass

class AsyncLLMProvider(ABC):
    """异步大语言模型提供者接口"""
    
    @abstractmethod
    async def submit_prompt(self, prompt: Union[str, List[Dict[str, str]]], **kwargs) -> str:
        """异步提交提示并返回响应"""
        pass

class AsyncVectorStore(ABC):
    """异步向量存储接口"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """异步初始化向量存储"""
        pass
        
    @abstractmethod
    async def close(self) -> None:
        """异步关闭向量存储连接"""
        pass
    
    @abstractmethod
    async def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """异步添加问题和SQL的映射"""
        pass
    
    @abstractmethod
    async def add_ddl(self, ddl: str, **kwargs) -> str:
        """异步添加DDL语句"""
        pass
    
    @abstractmethod
    async def add_documentation(self, documentation: str, **kwargs) -> str:
        """异步添加文档"""
        pass
    
    @abstractmethod
    async def get_similar_question_sql(self, question: str, **kwargs) -> List[Dict[str, str]]:
        """异步获取类似问题的SQL"""
        pass
    
    @abstractmethod
    async def get_related_ddl(self, question: str, **kwargs) -> List[str]:
        """异步获取相关DDL语句"""
        pass
    
    @abstractmethod
    async def get_related_documentation(self, question: str, **kwargs) -> List[str]:
        """异步获取相关文档"""
        pass
    
    @abstractmethod
    async def get_training_data(self, **kwargs) -> pd.DataFrame:
        """异步获取训练数据"""
        pass
    
    @abstractmethod
    async def remove_training_data(self, id: str, **kwargs) -> bool:
        """异步移除训练数据"""
        pass
    
    @abstractmethod
    async def remove_collection(self, collection_name: str) -> bool:
        """异步重置集合"""
        pass

class AsyncDBConnector(ABC):
    """异步数据库连接器接口"""
    
    @abstractmethod
    async def connect(self, **kwargs) -> Any:
        """异步连接到数据库"""
        pass
    
    @abstractmethod
    async def run_sql(self, sql: str, **kwargs) -> Any:
        """异步执行SQL查询"""
        pass
    
    @abstractmethod
    async def get_schema(self, **kwargs) -> str:
        """异步获取数据库模式"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """异步关闭数据库连接"""
        pass


class AsyncPlugin(ABC):
    """异步插件接口"""
    
    @abstractmethod
    async def initialize(self, smart_sql) -> None:
        """异步初始化插件"""
        pass
    
    @abstractmethod
    async def on_before_generate_sql(self, question: str, **kwargs) -> str:
        """异步SQL生成前钩子"""
        pass
    
    @abstractmethod
    async def on_after_generate_sql(self, question: str, sql: str, **kwargs) -> str:
        """异步SQL生成后钩子"""
        pass
    
    @abstractmethod
    async def on_error(self, error: Exception, **kwargs) -> None:
        """异步错误处理钩子"""
        pass
