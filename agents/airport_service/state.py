"""
状态定义模块
"""
from typing import Dict, Annotated, Optional, List, Literal
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langgraph.prebuilt.chat_agent_executor import AgentState
from pydantic import BaseModel, Field
from dataclasses import dataclass
from langchain_core.messages import AnyMessage



class TranslationResult(BaseModel):
    """翻译结果模型"""
    language: str = Field(description="检测到的语言类型")
    original_text: str = Field(description="用户输入的原始内容")
    translated_text: str = Field(description="翻译成的中文内容")

class RetrievalResult(BaseModel):
    """统一的检索结果模型"""
    source: Literal["expert_qa", "knowledge_base", "flight","none"] = Field(
        description="检索来源类型：expert_qa(专家问答), knowledge_base(知识库), none(无结果)"
    )
    content: Optional[str] = Field(
        default=None, 
        description="检索到的文本内容"
    )
    score: Optional[float] = Field(
        default=0.0, 
        description="检索结果的相似度分数"
    )
    images: Optional[str] = Field(
        default=None, 
        description="相关图片列表（如果有）"
    )
    sql: Optional[str] = Field(
        default=None, 
        description="相关SQL（如果有）"
    )
    query_list: Optional[List[str]] = Field(
        default=None, 
        description="相关查询列表（如果有）"
    )

def dict_merge(old_dict, new_dict):
    """合并字典，处理状态更新"""
    if not old_dict:
        return new_dict
    if not new_dict:
        return old_dict
    return {**old_dict, **new_dict}

class AirportMainServiceState(MessagesState):
    """机场客服系统状态定义"""  
    user_query: Optional[str] = None
    router: Optional[str] = None
    translator_result: Optional[TranslationResult] = None
    emotion_result: Optional[Dict] = None
    pre_retrieval_result: Optional[RetrievalResult] = None
    retrieval_result: Optional[RetrievalResult] = None  # 统一的检索结果
    chart_config: Optional[Dict] = None
    metadata: Optional[Dict] = None

class BusinessServiceState(AgentState):
    pass

class BusinessRecommendState(MessagesState):
    """机场商业推荐服务状态定义"""
    user_query: Optional[str] = None
    translator_result: Optional[TranslationResult] = None
    emotion_result: Optional[Dict] = None
    retrieval_result: Optional[RetrievalResult] = None  # 统一的检索结果
    chart_config: Optional[Dict] = None
    metadata: Optional[Dict] = None

class QuestionRecommendState(MessagesState):
    """机场问题推荐服务状态定义"""
    user_query: Optional[str] = None
    translator_result: Optional[TranslationResult] = None
    emotion_result: Optional[Dict] = None
    retrieval_result: Optional[RetrievalResult] = None  # 统一的检索结果
    db_context_docs: Optional[Dict] = None
    metadata: Optional[Dict] = None
    conversation_memories: Optional[str] = None


@dataclass
class AirportMainServiceContextSchema:
    user_name: str


