"""
用户画像系统 - 重构版本
提供统一的入口和向后兼容性
"""

# 导入重构后的核心组件
from .user_profile_models import (
    # 基础枚举
    TravelerType, UserRole, SpendingPower, QueryStyle, Sentiment,
    # 核心画像模型
    SessionProfile, DailyProfile, InsightProfile, CompleteUserProfile,UserAttributeInference,
    # 组件模型
    SessionMetrics, TechnicalContext, ContentAnalysis, ServiceInteraction
    , ProfileUpdateResult, BusinessInsight, OperationalReport,
)

from .extraction_components import (
    SemanticExtractor, SessionMetricsCalculator, DataProfileAnalyzer
)

from .profile_extractor import ProfileExtractor, profile_extractor
from .operational_analytics import OperationalAnalyticsEngine, operational_analytics_engine
from .profile_scheduler import ProfileScheduler, ScheduleConfig, profile_scheduler

__all__ = [
    # 模型
    'TravelerType', 'UserRole', 'SpendingPower', 'QueryStyle', 'Sentiment',
    'SessionProfile', 'DailyProfile', 'InsightProfile', 'CompleteUserProfile',
    'SessionMetrics', 'TechnicalContext', 'ContentAnalysis', 'ServiceInteraction',
    'ProfileUpdateResult', 'BusinessInsight', 'OperationalReport',
    'LongTermSemanticAnalysis', 'ProfileConverterUtils',
    
    # 向后兼容别名
    'SingleSessionProfile', 'DailyStatisticsProfile', 'DeepInsightProfile',
    
    # 核心组件
    'ProfileExtractor', 'profile_extractor',
    'OperationalAnalyticsEngine', 'operational_analytics_engine', 
    'ProfileScheduler', 'profile_scheduler',
    'ScheduleConfig',
    
    # 工具组件
    'SemanticExtractor', 'SessionMetricsCalculator', 'DataProfileAnalyzer'
]

# 版本信息
__version__ = "2.0.0"
__description__ = "机场智能客服用户画像系统"
