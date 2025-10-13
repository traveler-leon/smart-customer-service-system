"""
统一用户画像模型
整合原有的user_profile_model.py和user_profile_model_extended.py
提供清晰的三层画像架构
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Union
from datetime import datetime
from enum import Enum

# ============================== 基础枚举定义 ==============================
class TravelerType(str, Enum):
    """旅客类型枚举"""
    BUSINESS = "商旅人士"
    LEISURE = "休闲旅客"
    FIRST_TIME = "首次乘机"
    FREQUENT = "常旅客"
    FAMILY = "家庭出行"
    STUDENT = "学生出行"
    TRANSIT = "中转旅客"

class UserRole(str, Enum):
    """用户角色枚举"""
    PASSENGER = "乘机人本人"
    FAMILY_FRIEND = "亲友代问"
    PICK_UP = "接送机人员"
    AGENT = "代理人"
    STAFF = "机场工作人员"

class SpendingPower(str, Enum):
    """消费能力枚举"""
    HIGH = "高价值客户"
    MEDIUM = "中等消费"
    PRICE_SENSITIVE = "价格敏感"
    UNKNOWN = "未知"

class QueryStyle(str, Enum):
    """提问风格枚举"""
    CONCISE = "简洁型"
    DETAILED = "详细型"
    URGENT = "紧急型"
    CASUAL = "随意型"
    PROFESSIONAL = "专业型"

class Sentiment(str, Enum):
    """情感倾向枚举"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANXIOUS = "anxious"
    SATISFIED = "satisfied"

class ResolutionStatus(str, Enum):
    """问题解决状态枚举"""
    RESOLVED = "已解决"
    PARTIALLY_RESOLVED = "部分解决"
    NOT_RESOLVED = "未解决"
    NEED_FOLLOW_UP = "需要跟进"
# ============================== 基础组件模型 ==============================
class SessionMetrics(BaseModel):
    """会话基础指标"""
    start_time: datetime = Field(..., description="会话开始时间")
    end_time: datetime = Field(..., description="会话结束时间")
    day: str = Field(..., description="会话日期")
    duration_seconds: int = Field(..., description="会话持续时间（秒）")
    turn_count: int = Field(0, description="会话轮次数")
    user_messages_count: int = Field(0, description="用户消息数量")
    system_responses_count: int = Field(0, description="系统回复数量")
    avg_response_time: float = Field(0.0, description="平均响应时间（秒）")

class TechnicalContext(BaseModel):
    """技术环境信息"""
    source: Optional[str] = Field(None, description="咨询来源 (微信、电话、网站、小程序)")
    device: Optional[str] = Field(None, description="设备类型 (手机、电脑、平板)")
    ip: Optional[str] = Field(None, description="IP地址")
    country: Optional[str] = Field(None, description="国家")
    province: Optional[str] = Field(None, description="省份")
    city: Optional[str] = Field(None, description="城市")
    district: Optional[str] = Field(None, description="区县")
    latitude: Optional[float] = Field(None, description="经度")
    longitude: Optional[float] = Field(None, description="纬度")
    network_type: Optional[str] = Field(None, description="网络类型（wifi、4g、5g、其他）")

class ContentAnalysis(BaseModel):
    language: str = Field(default="中文",description="本地对话主要使用语言。如果是多语种混合，选择占主导的语言。选项：中文、英文、其他")
    style: QueryStyle = Field(default=QueryStyle.CASUAL,description=f"用户提问风格：可选值有：{list(QueryStyle._value2member_map_.keys())}")
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL,description=f"整体情感倾向：可选值有：{list(Sentiment._value2member_map_.keys())}")
    anxiety_score: float = Field(default=0.0, ge=0.0, le=1.0,description="焦虑指数(0-1)：0=无焦虑，0.3=轻微焦虑，0.6=中度焦虑，0.9=高度焦虑")
    urgency_score: float = Field(default=0.0, ge=0.0, le=1.0,description="紧急程度(0-1)：0=不紧急，0.3=一般紧急，0.6=比较紧急，0.9=非常紧急")
    satisfaction_score: float = Field(default=0.0, ge=0.0, le=1.0,description="满意度(0-1)：0.1=非常不满意，0.3=不满意，0.5=一般，0.7=满意，0.9=非常满意；无法判断时为null")
    keywords: List[str] = Field(default_factory=list,description="对话中提到的关键词，包括专业术语、地名、时间、服务名称等")
    topics: List[str] = Field(default_factory=list,description="对话中讨论的主要话题，如：航班查询、服务预订、政策咨询、问题投诉等")
    resolution_status: str = Field(default=ResolutionStatus.NOT_RESOLVED,description=f"问题解决状态，必须是以下之一：{list(ResolutionStatus._value2member_map_.keys())}")
    

class FlightInfo(BaseModel):
    flight_number: Optional[str] = Field(None,description="标准航班号格式，如 CA1234, MU5678。如果用户提到航班但格式不标准，请尝试标准化")
    @field_validator('flight_number')
    def validate_flight_number(cls, v):
        """验证航班号格式"""
        if v and any(c.isalpha() for c in v) and any(c.isdigit() for c in v):
            # 简单验证：至少包含字母和数字
                return None
        return v
    
class ServiceUsage(BaseModel):
    service_name: str = Field(description="具体服务名称，如'轮椅租赁'、'快速通道'、'行李托运'、'餐饮预订'等")
    usage_intent: str = Field(description="用户意图，必须是以下之一：咨询、预订、取消、投诉、查询状态、修改")
    service_status: str = Field(description="服务状态：已完成、进行中、待处理、已取消，如果无法确定则为null")
    
    @field_validator('usage_intent')
    def validate_usage_intent(cls, v):
        """验证使用意图"""
        valid_intents = ['咨询', '预订', '取消', '投诉', '查询状态', '修改']
        if v not in valid_intents:
            raise ValueError(f'使用意图必须是以下之一: {", ".join(valid_intents)}')
        return v


class ServiceInteraction(BaseModel):    
    flights: Optional[List[FlightInfo]] = Field(default_factory=list,description="对话中明确提到的所有航班信息。即使用户只是咨询也要记录。如果没有提到任何航班，返回空列表")
    services: Optional[List[ServiceUsage]] = Field(default_factory=list,description="用户讨论、咨询或使用的所有机场服务。包括已使用的、计划使用的和咨询的服务")
    
    @property
    def queried_flights(self) -> List[str]:
        """查询的航班列表"""
        return list(set([f.flight_number for f in self.flights_mentioned if f.flight_number]))
    
    @property
    def service_usage(self) -> List[str]:
        """使用的服务列表"""
        return [s.service_name for s in self.services_discussed]


# 用户属性推断的简单模型
class UserAttributeInference(BaseModel):
    """用户属性推断结果"""
    traveler_type: TravelerType = Field(TravelerType.LEISURE,description=f"推断的旅客类型：{list(TravelerType._value2member_map_.keys())}")
    role: UserRole = Field(UserRole.PASSENGER,description=f"推断的用户角色：{list(UserRole._value2member_map_.keys())}")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0,description="推断置信度(0-1)")

# ============================== 第一层：单次会话画像 ==============================
class SessionProfile(BaseModel):    
    session_metrics: SessionMetrics = Field(..., description="会话指标数据，由系统自动计算")
    technical_context: TechnicalContext = Field(default_factory=TechnicalContext, description="技术环境信息，由系统自动提取")
    content_analysis: ContentAnalysis = Field(description="内容分析结果，包含语言风格、情感状态、用户关注点等。")
    service_interaction: ServiceInteraction = Field(description="服务交互记录，包含航班、服务。")
    inferred_user_attribute: UserAttributeInference = Field(description="推断的旅客类型和用户角色，基于对话语境判断，无法确定时为null")

# ============================== 第二层：每日统计画像 ==============================
class DailyInteractionMetrics(BaseModel):
    """每日交互统计"""
    total_sessions: int = Field(0, description="总会话次数")
    total_turns: int = Field(0, description="总交互轮次")
    avg_session_duration: float = Field(0.0, description="平均会话时长（分钟）")
    avg_session_depth: float = Field(0.0, description="平均会话深度（轮次）")
    peak_hours: List[int] = Field(default_factory=list, description="高峰时段")
    
    # 设备和渠道分布
    device_distribution: Dict[str, int] = Field(default_factory=dict, description="设备分布统计")
    source_distribution: Dict[str, int] = Field(default_factory=dict, description="来源渠道分布")
    country_distribution: Dict[str, int] = Field(default_factory=dict, description="国家分布")
    province_distribution: Dict[str, int] = Field(default_factory=dict, description="省份分布")
    city_distribution: Dict[str, int] = Field(default_factory=dict, description="城市分布")

class DailyBehaviorPattern(BaseModel):
    """每日行为模式"""
    dominant_language: str = Field("中文", description="主要使用语言")
    common_query_styles: List[QueryStyle] = Field(default_factory=list, description="常见提问风格")
    avg_sentiment_score: float = Field(0.0, description="平均情感分数")
    avg_anxiety_score: float = Field(0.0, description="平均焦虑指数")
    avg_urgency_score: float = Field(0.0, description="平均紧急度")
    
    # 内容特征
    frequent_keywords: List[str] = Field(default_factory=list, description="高频关键词")
    topic_trends: Dict[str, int] = Field(default_factory=dict, description="话题趋势")

        # 服务效果
    resolution_rate: float = Field(0.0, description="问题解决率")
    satisfaction_rate: float = Field(0.0, description="满意度")
    follow_up_rate: float = Field(0.0, description="需要跟进比例")

class DailyServiceUsage(BaseModel):
    """每日服务使用情况"""
    flights_queried: Dict[str, int] = Field(default_factory=dict, description="查询航班统计")
    services_used: Dict[str, int] = Field(default_factory=dict, description="使用服务统计")
    

class DailyProfile(BaseModel):
    """每日统计画像"""
    interaction_metrics: DailyInteractionMetrics = Field(..., description="交互指标")
    behavior_pattern: DailyBehaviorPattern = Field(default_factory=DailyBehaviorPattern, description="行为模式")
    service_usage: DailyServiceUsage = Field(default_factory=DailyServiceUsage, description="服务使用")
    behavior_stability: float = Field(0.0, description="行为稳定性指数")

# ============================== 第三层：深度洞察画像 ==============================
class LongTermBehaviorPattern(BaseModel):
    """长期行为模式"""
    preferred_contact_hours: List[int] = Field(default_factory=list, description="偏好联系时段")    

class TravelPattern(BaseModel):
    """出行模式分析"""
    preferred_airlines: List[str] = Field(default_factory=list, description="偏好航空公司")
    travel_frequency: str = Field("unknown", description="出行频率 (high/medium/low)")

class ServicePreference(BaseModel):
    """服务偏好分析"""
    preferred_services: List[str] = Field(default_factory=list, description="偏好服务")

class InsightProfile(BaseModel):
    """深度洞察画像"""
    analysis_period: str = Field(..., description="分析周期")
    # 核心标签
    primary_traveler_type: TravelerType = Field(..., description="主要旅客类型") 
    # 深度分析
    behavior_pattern: LongTermBehaviorPattern = Field(..., description="长期行为模式")
    travel_pattern: TravelPattern = Field(default_factory=TravelPattern, description="出行模式")
    service_preference: ServicePreference = Field(default_factory=ServicePreference, description="服务偏好")
    
    # 价值评估
    customer_value_score: float = Field(0.0, ge=0.0, le=1.0, description="客户价值分数")
    retention_risk: float = Field(0.0, ge=0.0, le=1.0, description="流失风险")
    upsell_potential: float = Field(0.0, ge=0.0, le=1.0, description="增值服务潜力")
    
    # 推荐策略
    recommended_services: List[str] = Field(default_factory=list, description="推荐服务")
    communication_strategy: str = Field("standard", description="沟通策略")
    personalization_level: str = Field("medium", description="个性化程度")
    
    # 置信度和质量
    profile_confidence: float = Field(0.0, ge=0.0, le=1.0, description="画像置信度")

# ============================== 完整用户画像聚合模型 ==============================
class CompleteUserProfile(BaseModel):
    """完整用户画像（聚合所有层级）"""
    user_id: str = Field(..., description="用户唯一标识")
    
    # 基础信息
    first_interaction: datetime = Field(..., description="首次交互时间")
    last_interaction: datetime = Field(..., description="最近交互时间")
    total_sessions: int = Field(0, description="总会话数")
    profile_version: str = Field("1.0", description="画像版本")
    
    # 三层画像
    recent_sessions: List[SessionProfile] = Field(default_factory=list, description="最近会话画像")
    daily_profiles: List[DailyProfile] = Field(default_factory=list, description="每日统计画像")
    insight_profile: Optional[InsightProfile] = Field(None, description="深度洞察画像")
    
    # 实时状态
    current_status: str = Field("inactive", description="当前状态")
    risk_flags: List[str] = Field(default_factory=list, description="风险标识")
    opportunities: List[str] = Field(default_factory=list, description="机会标识")
    
    # 元数据
    last_profile_update: datetime = Field(default_factory=datetime.now, description="画像最后更新时间")
    data_completeness: float = Field(0.0, ge=0.0, le=1.0, description="数据完整度")

# ============================== 画像提取和更新机制 ==============================
class ProfileExtractionTrigger(BaseModel):
    """画像提取触发器"""
    trigger_type: str = Field(..., description="触发类型：session_end, daily_batch, weekly_analysis")
    user_id: str = Field(..., description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID（如果是会话结束触发）")
    trigger_time: datetime = Field(default_factory=datetime.now, description="触发时间")
    data_range: Optional[Dict[str, str]] = Field(None, description="数据范围（开始和结束时间）")

class ProfileUpdateResult(BaseModel):
    """画像更新结果"""
    user_id: str = Field(..., description="用户ID")
    update_type: str = Field(..., description="更新类型：session, daily, insight")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")
    updated_fields: List[str] = Field(default_factory=list, description="更新的字段")
    confidence_score: float = Field(0.0, description="画像置信度")
    data_quality: float = Field(0.0, description="数据质量分数")
    processing_time: float = Field(0.0, description="处理耗时（秒）")
    timestamp: datetime = Field(default_factory=datetime.now, description="更新时间")

# ============================== 运营分析辅助模型 ==============================
class BusinessInsight(BaseModel):
    """业务洞察"""
    insight_type: str = Field(..., description="洞察类型")
    title: str = Field(..., description="洞察标题")
    description: str = Field(..., description="洞察描述")
    impact_level: str = Field("medium", description="影响级别：high/medium/low")
    affected_users: int = Field(0, description="影响用户数")
    recommended_actions: List[str] = Field(default_factory=list, description="建议行动")
    metrics: Dict[str, Union[str, int, float]] = Field(default_factory=dict, description="相关指标")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

class OperationalReport(BaseModel):
    """运营报告"""
    report_id: str = Field(..., description="报告ID")
    period: str = Field(..., description="报告周期")
    report_type: str = Field(..., description="报告类型：daily/weekly/monthly")
    
    # 核心指标
    total_users: int = Field(0, description="总用户数")
    active_users: int = Field(0, description="活跃用户数")
    new_users: int = Field(0, description="新增用户数")
    retention_rate: float = Field(0.0, description="用户留存率")
    
    # 服务质量
    avg_satisfaction: float = Field(0.0, description="平均满意度")
    resolution_rate: float = Field(0.0, description="问题解决率")
    response_time: float = Field(0.0, description="平均响应时间")
    
    # 业务洞察
    key_insights: List[BusinessInsight] = Field(default_factory=list, description="关键洞察")
    trends: Dict[str, str] = Field(default_factory=dict, description="趋势分析")
    recommendations: List[str] = Field(default_factory=list, description="改进建议")
    
    # 元数据
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")
    data_sources: List[str] = Field(default_factory=list, description="数据来源")
    confidence_level: float = Field(0.0, description="报告可信度")


# ============================== 语义分析相关模型 ==============================
class LongTermSemanticAnalysis(BaseModel):
    """
    长期语义分析结果
    
    基于用户长期行为数据进行深度语义分析，提取用户的核心特征、需求和推荐策略。
    用于机场客服系统的个性化服务和精准推荐。
    """
    confirmed_traveler_type: str = Field(
        default="休闲旅客", 
        description="确认的旅客类型。基于长期行为模式推断，可选值：商务旅客、休闲旅客、中转旅客、首次乘机、常旅客"
    )
    core_needs: List[str] = Field(
        default_factory=list, 
        description="核心需求列表。从用户行为数据中提取的主要关注点，如：时间效率、服务质量、价格优惠、便民服务等"
    )
    behavioral_insights: List[str] = Field(
        default_factory=list, 
        description="行为洞察。对用户行为模式的深度理解，如：沟通风格偏好、决策习惯、服务使用倾向等"
    )
    personalization_recommendations: List[str] = Field(
        default_factory=list, 
        description="个性化推荐策略。基于用户画像的服务推荐和沟通建议，如：推荐特定服务、优化沟通方式、潜在需求挖掘等"
    )
    confidence_level: float = Field(
        default=0.0, 
        ge=0.0, le=1.0, 
        description="分析置信度(0-1)。基于数据量、行为一致性和推断支撑度评估。0.8以上为高置信度，0.5-0.8为中等，0.5以下为低置信度"
    )
    data_completeness: float = Field(
        default=0.0, 
        ge=0.0, le=1.0, 
        description="数据完整性(0-1)。评估当前数据覆盖的行为维度和时间跨度充足性。1.0表示数据非常完整，0.5表示基本够用，0.3以下建议收集更多数据"
    )


# ============================== 工具类 ==============================
class ProfileConverterUtils:
    """画像数据转换工具类"""
    
    @staticmethod
    def convert_str_to_traveler_type(traveler_type_str: str) -> TravelerType:
        """将字符串转换为TravelerType枚举"""
        mapping = {
            "商务旅客": TravelerType.BUSINESS,
            "休闲旅客": TravelerType.LEISURE,
            "中转旅客": TravelerType.TRANSIT,
            "学生旅客": TravelerType.STUDENT,
            "常旅客": TravelerType.FREQUENT,
            "家庭出行": TravelerType.FAMILY,
            "首次乘机": TravelerType.FIRST_TIME,
            "business": TravelerType.BUSINESS,
            "leisure": TravelerType.LEISURE,
            "transfer": TravelerType.TRANSIT,
            "student": TravelerType.STUDENT,
            "frequent": TravelerType.FREQUENT,
            "family": TravelerType.FAMILY,
            "first_time": TravelerType.FIRST_TIME,
        }
        return mapping.get(traveler_type_str, TravelerType.LEISURE)
    
    @staticmethod
    def convert_str_to_user_role(user_role_str: str) -> UserRole:
        """将字符串转换为UserRole枚举"""
        mapping = {
            "乘机人本人": UserRole.PASSENGER,
            "代理人": UserRole.AGENT,
            "家属朋友": UserRole.FAMILY_FRIEND,
            "企业助理": UserRole.CORPORATE_ASSISTANT,
            "passenger": UserRole.PASSENGER,
            "agent": UserRole.AGENT,
            "family": UserRole.FAMILY_FRIEND,
            "assistant": UserRole.CORPORATE_ASSISTANT
        }
        return mapping.get(user_role_str, UserRole.PASSENGER)
    
    @staticmethod
    def convert_str_to_spending_power(spending_power_str: str) -> 'SpendingPower':
        """将字符串转换为SpendingPower枚举"""
        mapping = {
            "高消费": SpendingPower.HIGH,
            "中等消费": SpendingPower.MEDIUM,
            "低消费": SpendingPower.LOW,
            "high": SpendingPower.HIGH,
            "medium": SpendingPower.MEDIUM,
            "low": SpendingPower.LOW
        }
        return mapping.get(spending_power_str, SpendingPower.MEDIUM)


# ============================== 支出能力枚举 ==============================
class SpendingPower(str, Enum):
    """支出能力"""
    HIGH = "高消费"
    MEDIUM = "中等消费"
    LOW = "低消费"


