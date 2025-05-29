"""
状态定义模块
"""

from typing import Dict, List, TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState
from typing import Union

from typing import List, Optional
from pydantic import BaseModel, Field

from typing import List, Optional
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    # 基本行为画像
    preferred_language: Optional[str] = Field(None, description="首选语言，用户希望使用的语言")
    frequent_destinations: Optional[List[str]] = Field(None, description="常去目的地，用户经常前往的城市或机场")
    seating_preferences: Optional[str] = Field(None, description="座位偏好，例如靠窗、靠过道等")
    meal_preferences: Optional[str] = Field(None, description="膳食偏好，例如素食、清真等")
    accessibility_needs: Optional[List[str]] = Field(None, description="无障碍需求，例如轮椅协助")
    loyalty_program_status: Optional[str] = Field(None, description="常旅客计划状态，例如金卡、银卡")
    communication_tone_preference: Optional[str] = Field(None, description="沟通语气偏好，例如正式、轻松")
    preferred_contact_channel: Optional[str] = Field(None, description="首选联系方式，例如微信、电话")
    name_or_nickname: Optional[str] = Field(None, description="用户希望被称呼的名字或昵称")

    # 性格画像
    personality_type: Optional[str] = Field(None, description="用户性格类型，例如外向、理性、冷静等")
    emotional_tendency: Optional[str] = Field(None, description="情绪倾向，例如焦虑、温和、急躁等")
    communication_style: Optional[str] = Field(None, description="沟通风格，例如详细、简洁、理性等")
    decision_making_style: Optional[str] = Field(None, description="决策风格，例如犹豫型、果断型、依赖建议型等")

class Episode(BaseModel):  
    """从智能体的视角记录一个事件。借助事后视角来保存记忆，记录智能体在事件中的关键内部思考过程，以便其随着时间学习和成长。"""

    observation: str = Field(
        ..., 
        description="上下文与情境——发生了什么"
    )
    thoughts: str = Field(
        ...,
        description="智能体在该事件中的内部推理过程和观察，是如何得出正确行动和结果的.\"我……\"",
    )
    action: str = Field(
        ...,
        description="执行了什么、如何执行、使用了什么格式。（包括对成功关键点的说明）。我……",
    )
    result: str = Field(
        ...,
        description="结果与回顾。你做得好的是什么？下次可以改进的是什么？我……",
    )

class TranslationResult(BaseModel):
    """翻译结果模型"""
    language: str = Field(description="检测到的语言类型")
    original_text: str = Field(description="用户输入的原始内容")
    translated_text: str = Field(description="翻译成的中文内容")



def dict_merge(old_dict, new_dict):
    """合并字典，处理状态更新"""
    if not old_dict:
        return new_dict
    if not new_dict:
        return old_dict
    return {**old_dict, **new_dict}

class AirportMainServiceState(MessagesState):
    """机场客服系统状态定义"""
    # 用户信息
    user_base_info: Annotated[Dict, dict_merge] = {}
    user_profile_info: Optional[UserProfile] = None
    # 当前查询
    current_tool_query: Optional[str] = None
    translator_result: Optional[TranslationResult] = None
    # 情感识别
    emotion_result:Dict = {}
    # 上下文信息
    kb_context_docs: str = ""
    db_context_docs: Dict = {}
    chart_config: Dict = {}