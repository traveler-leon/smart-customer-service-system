import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
import logging
import statistics
from typing import List, Dict, Optional, Any
from collections import Counter
from langchain_openai import ChatOpenAI

from .user_profile_models import (
    SessionProfile, DailyProfile,
    DailyInteractionMetrics, DailyBehaviorPattern, DailyServiceUsage,
    InsightProfile, LongTermBehaviorPattern, TravelPattern, 
    ServicePreference,Sentiment,ResolutionStatus,ProfileConverterUtils
)
from .extraction_components import (
    SemanticExtractor, SessionMetricsCalculator, DataProfileAnalyzer,
     LongTermSemanticAnalysis
)

logger = logging.getLogger(__name__)


class BehaviorAggregator:
    """行为聚合器 - 基于统计和计算"""
    
    def calculate_daily_interaction_metrics(
        self, 
        session_profiles: List[SessionProfile]
    ) -> DailyInteractionMetrics:
        """计算每日交互指标"""
        total_sessions = len(session_profiles)
        total_turns = sum(s.session_metrics.turn_count for s in session_profiles)
        
        durations = [s.session_metrics.duration_seconds for s in session_profiles 
                    if s.session_metrics.duration_seconds]
        avg_duration = sum(durations) / len(durations) / 60 if durations else 0
        
        avg_depth = total_turns / total_sessions if total_sessions > 0 else 0
        
        # 统计设备分布
        device_dist = {}
        source_dist = {}
        country_dist = {}
        province_dist = {}
        city_dist = {}
        
        for session in session_profiles:
            device = session.technical_context.query_device
            if device:
                device_dist[device] = device_dist.get(device, 0) + 1
            
            source = session.technical_context.query_source
            if source:
                source_dist[source] = source_dist.get(source, 0) + 1
            
            country = session.technical_context.country
            if country:
                country_dist[country] = country_dist.get(country, 0) + 1

            province = session.technical_context.province
            if province:
                province_dist[province] = province_dist.get(province, 0) + 1

            city = session.technical_context.city
            if city:
                city_dist[city] = city_dist.get(city, 0) + 1
        
        return DailyInteractionMetrics(
            total_sessions=total_sessions,
            total_turns=total_turns,
            avg_session_duration=avg_duration,
            avg_session_depth=avg_depth,
            device_distribution=device_dist,
            source_distribution=source_dist,
            country_distribution=country_dist,
            province_distribution=province_dist,
            city_distribution=city_dist
        )
    
    def analyze_daily_behavior_pattern(
        self, 
        session_profiles: List[SessionProfile]
    ) -> DailyBehaviorPattern:
        """分析每日行为模式"""
        if not session_profiles:
            return DailyBehaviorPattern()
        
        languages = [s.content_analysis.language for s in session_profiles]
        dominant_language = max(set(languages), key=languages.count) if languages else "中文"
        
        styles = [s.content_analysis.query_style for s in session_profiles]
        common_styles = list(set(styles))
        
        # 计算情感分数
        sentiment_scores = []
        anxiety_scores = []
        urgency_scores = []
        
        for session in session_profiles:
            sentiment_map = {
                Sentiment.NEGATIVE: -1.0,
                Sentiment.ANXIOUS: -0.5,
                Sentiment.NEUTRAL: 0.0,
                Sentiment.POSITIVE: 0.5,
                Sentiment.SATISFIED: 1.0
            }
            sentiment_scores.append(sentiment_map.get(session.content_analysis.sentiment, 0.0))
            anxiety_scores.append(session.content_analysis.anxiety_score)
            urgency_scores.append(session.content_analysis.urgency_score)
        
        # 聚合关注点和关键词
        all_keywords = []
        topic_counts = {}
        resolved_count = 0
        follow_up_count = 0
        satisfaction_count=0
        
        for session in session_profiles:
            all_keywords.extend(session.content_analysis.keywords)
            for topic in session.content_analysis.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

                        # 统计服务效果
            resolved_count += int(session.content_analysis.resolution_status==ResolutionStatus.RESOLVED)
            if session.content_analysis.resolution_status==ResolutionStatus.NEED_FOLLOW_UP:
                follow_up_count += 1
            if session.content_analysis.satisfaction_score is not None and session.content_analysis.satisfaction_score > 0.5:
                satisfaction_count += 1
        
        frequent_keywords = [item[0] for item in Counter(all_keywords).most_common(10)]
        
        return DailyBehaviorPattern(
            dominant_language=dominant_language,
            common_query_styles=common_styles,
            avg_sentiment_score=sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0,
            avg_anxiety_score=sum(anxiety_scores) / len(anxiety_scores) if anxiety_scores else 0.0,
            avg_urgency_score=sum(urgency_scores) / len(urgency_scores) if urgency_scores else 0.0,
            frequent_keywords=frequent_keywords,
            topic_trends=topic_counts,
            resolution_rate=resolved_count / len(session_profiles) if session_profiles else 0,
            satisfaction_rate=satisfaction_count / len(session_profiles) if session_profiles else 0.0,
            follow_up_rate=follow_up_count / len(session_profiles) if session_profiles else 0
        )
    
    def analyze_daily_service_usage(
        self, 
        session_profiles: List[SessionProfile]
    ) -> DailyServiceUsage:
        """分析每日服务使用"""
        airlines_count = {}
        services_count = {}
        for session in session_profiles:
            # 统计查询
            for airline in session.service_interaction.queried_flights:
                airlines_count[airline] = airlines_count.get(airline, 0) + 1
            
            for service in session.service_interaction.service_usage:
                services_count[service] = services_count.get(service, 0) + 1

        return DailyServiceUsage(
            airlines_queried=airlines_count,
            services_used=services_count,
        )
    
    def analyze_longterm_behavior_pattern(
        self, 
        daily_profiles: List[DailyProfile]
    ) -> LongTermBehaviorPattern:
        """分析长期行为模式"""
        if not daily_profiles:
            return LongTermBehaviorPattern()
        preferred_hours = self._analyze_preferred_contact_hours(daily_profiles)
        return LongTermBehaviorPattern(
            preferred_contact_hours=preferred_hours,
        )
    
    def _analyze_preferred_contact_hours(self, daily_profiles: List[DailyProfile]) -> List[int]:
        """分析偏好联系时段"""
        hour_counts = {}
        total_sessions = 0
        
        for profile in daily_profiles:
            # 从高峰时段数据中提取偏好时间
            peak_hours = profile.interaction_metrics.peak_hours
            sessions = profile.interaction_metrics.total_sessions
            total_sessions += sessions
            
            # 根据会话数加权计算时段偏好
            for hour in peak_hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + sessions
        
        if not hour_counts:
            return []
        
        # 计算每个时段的偏好强度（归一化）
        max_count = max(hour_counts.values()) if hour_counts else 1
        
        # 筛选出明显偏好的时段（超过平均值）
        avg_preference = sum(hour_counts.values()) / len(hour_counts)
        preferred_hours = []
        
        for hour, count in hour_counts.items():
            # 如果该时段的活跃度超过平均值的1.2倍，认为是偏好时段
            if count >= avg_preference * 1.2:
                preferred_hours.append(hour)
        
        # 按偏好强度排序，返回前5个
        preferred_hours.sort(key=lambda h: hour_counts[h], reverse=True)
        return preferred_hours[:5]
    
    def _calculate_comprehensive_behavior_score(self, daily_profiles: List[DailyProfile]) -> Dict[str, float]:
        """计算综合行为评分"""
        if not daily_profiles:
            return {}
        
        # 1. 活跃度一致性
        session_counts = [p.interaction_metrics.total_sessions for p in daily_profiles]
        activity_consistency = 1.0 - (statistics.stdev(session_counts) / (statistics.mean(session_counts) + 0.1))
        
        # 2. 满意度趋势
        satisfaction_scores = [p.behavior_pattern.satisfaction_rate for p in daily_profiles]
        satisfaction_trend = self._calculate_trend(satisfaction_scores)
        
        # 3. 参与深度稳定性
        depth_scores = [p.interaction_metrics.avg_session_depth for p in daily_profiles]
        depth_stability = 1.0 - (statistics.stdev(depth_scores) / (statistics.mean(depth_scores) + 0.1))
        
        return {
            "activity_consistency": max(0, min(activity_consistency, 1.0)),
            "satisfaction_trend": satisfaction_trend,
            "depth_stability": max(0, min(depth_stability, 1.0)),
            "overall_stability": (activity_consistency + depth_stability) / 2
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """计算数值序列的趋势（-1到1，负值表示下降趋势，正值表示上升趋势）"""
        if len(values) < 2:
            return 0.0
        
        # 简单的线性趋势计算
        x = list(range(len(values)))
        n = len(values)
        
        # 计算相关系数
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator_x = sum((x[i] - x_mean) ** 2 for i in range(n))
        denominator_y = sum((values[i] - y_mean) ** 2 for i in range(n))
        
        if denominator_x == 0 or denominator_y == 0:
            return 0.0
        
        correlation = numerator / (denominator_x * denominator_y) ** 0.5
        return max(-1.0, min(1.0, correlation))

class ProfileExtractor:    
    def __init__(self, llm_client: ChatOpenAI):
        """
        初始化用户画像提取器
        
        Args:
            llm_client: 外部传入的 LLM 客户端实例
        """
        self.llm = llm_client
        
        # 初始化组件
        self.semantic_extractor = SemanticExtractor(self.llm)
        self.data_analyzer = DataProfileAnalyzer()
        self.session_calculator = SessionMetricsCalculator()
        self.behavior_aggregator = BehaviorAggregator()
    
    async def extract_session_profile(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> SessionProfile:
        """
        第一步：提取单次会话画像
        语义提取 + 数据统计
        """
        if not conversation_history or len(conversation_history) < 6:
            return SessionProfile()
        try:
            # 1. 语义提取
            session_metrics = self.session_calculator.calculate_session_metrics(conversation_history)
            technical_context = self.data_analyzer.extract_technical_context(conversation_history)
            content_analysis, service_interaction, user_attributes = await self.semantic_extractor.extract_session_semantics(conversation_history,technical_context)
            # 7. 组装完整画像
            return SessionProfile(
                session_metrics=session_metrics,
                technical_context=technical_context,
                content_analysis=content_analysis,
                service_interaction=service_interaction,
                inferred_user_attribute=user_attributes
            )
            
        except Exception as e:
            logger.error(f"会话画像提取失败: {str(e)}")
            return SessionProfile()
    
    async def extract_daily_profile(
        self,
        session_profiles: List[SessionProfile]
    ) -> DailyProfile:
        """
        第二步：聚合每日画像
        基于会话画像数据统计
        """
        try:
            # 1. 计算交互指标
            interaction_metrics = self.behavior_aggregator.calculate_daily_interaction_metrics(session_profiles)
            # 2. 分析行为模式
            behavior_pattern = self.behavior_aggregator.analyze_daily_behavior_pattern(session_profiles)
            # 3. 统计服务使用
            service_usage = self.behavior_aggregator.analyze_daily_service_usage(session_profiles)
            # 5. 计算行为稳定性
            behavior_stability = self._calculate_behavior_stability(session_profiles)
            
            return DailyProfile(
                interaction_metrics=interaction_metrics,
                behavior_pattern=behavior_pattern,
                service_usage=service_usage,
                behavior_stability=behavior_stability,
            )
            
        except Exception as e:
            logger.error(f"每日画像聚合失败: {str(e)}")
            raise
    
    async def extract_insight_profile(
        self,
        user_id: str,
        daily_profiles: List[DailyProfile],
        analysis_period: str
    ) -> InsightProfile:
        """
        第三步：深度洞察分析
        语义分析 + 深度数据挖掘
        """
        try:
            # 1. 长期语义分析
            semantic_analysis = await self.semantic_extractor.extract_longterm_semantics(daily_profiles)
            # 2. 长期行为模式
            behavior_pattern = self.behavior_aggregator.analyze_longterm_behavior_pattern(daily_profiles)
            # 3. 分析出行模式
            travel_pattern = self._analyze_travel_pattern(daily_profiles)            
            # 4. 分析服务偏好
            service_preference = self._analyze_service_preference(daily_profiles)
            # 5. 计算价值评估指标
            value_score, retention_risk, upsell_potential = self._calculate_value_metrics(daily_profiles)
            # 7. 生成推荐策略
            recommended_services = semantic_analysis.personalization_recommendations
            communication_strategy = self._determine_communication_strategy(semantic_analysis, service_preference)
            personalization_level = self._determine_personalization_level(value_score)
            
            return InsightProfile(
                analysis_period=analysis_period,
                primary_traveler_type=ProfileConverterUtils.convert_str_to_traveler_type(semantic_analysis.confirmed_traveler_type),
                behavior_pattern=behavior_pattern,
                travel_pattern=travel_pattern,
                service_preference=service_preference,
                customer_value_score=value_score,
                retention_risk=retention_risk,
                upsell_potential=upsell_potential,
                recommended_services=recommended_services,
                communication_strategy=communication_strategy,
                personalization_level=personalization_level,
                profile_confidence=semantic_analysis.confidence_level
            )
            
        except Exception as e:
            logger.error(f"深度洞察分析失败: {str(e)}")
            # 返回默认的洞察画像
            from .user_profile_models import TravelerType
            return InsightProfile(
                analysis_period="0天",
                primary_traveler_type=TravelerType.LEISURE,
                behavior_pattern=LongTermBehaviorPattern()
            )
    
    def _calculate_behavior_stability(self, session_profiles: List[SessionProfile]) -> float:
        """计算行为稳定性"""
        if len(session_profiles) < 2:
            return 1.0
        
        # 基于情感和风格的一致性计算
        sentiments = [s.content_analysis.sentiment for s in session_profiles]
        styles = [s.content_analysis.style for s in session_profiles]
        
        sentiment_consistency = 1.0 - (len(set(sentiments)) / len(sentiments))
        style_consistency = 1.0 - (len(set(styles)) / len(styles))
        
        return (sentiment_consistency + style_consistency) / 2
    
    def _analyze_travel_pattern(self, daily_profiles: List[DailyProfile]) -> TravelPattern:
        """分析出行模式"""
        all_airlines = {}
        # 统计航空公司,以航班号开头二值码为航司代表
        for profile in daily_profiles:
            for airline, count in profile.service_usage.flights_queried.items():
                all_airlines[airline[:2]] = all_airlines.get(airline[:2], 0) + count
        
        # 排序获取偏好
        preferred_airlines = [item[0] for item in Counter(all_airlines).most_common(3)]
        
        # 出行频率分析
        total_flight_queries = sum(all_airlines.values())
        days_span = len(daily_profiles)
        
        if total_flight_queries / days_span > 2:
            travel_frequency = "high"
        elif total_flight_queries / days_span > 0.5:
            travel_frequency = "medium"
        else:
            travel_frequency = "low"
        
        return TravelPattern(
            preferred_airlines=preferred_airlines,
            travel_frequency=travel_frequency
        )
    
    def _analyze_service_preference(self, daily_profiles: List[DailyProfile]) -> ServicePreference:
        """分析服务偏好"""
        all_services = {}
        
        for profile in daily_profiles:
            for service, count in profile.service_usage.services_used.items():
                all_services[service] = all_services.get(service, 0) + count
        
        # 偏好服务排序
        preferred_services = [item[0] for item in Counter(all_services).most_common(5)]
        
        return ServicePreference(
            preferred_services=preferred_services,
        )
    
    def _calculate_value_metrics(self, daily_profiles: List[DailyProfile]) -> tuple[float, float, float]:
        """计算价值评估指标"""
        total_sessions = sum(p.interaction_metrics.total_sessions for p in daily_profiles)
        days_span = len(daily_profiles)
        avg_satisfaction = sum(p.service_usage.satisfaction_rate for p in daily_profiles) / len(daily_profiles)
        
        value_score = min((total_sessions / 50 + avg_satisfaction + days_span / 30) / 3, 1.0)
        
        # 流失风险
        recent_satisfaction = daily_profiles[-3:] if len(daily_profiles) >= 3 else daily_profiles
        recent_avg_satisfaction = sum(p.service_usage.satisfaction_rate for p in recent_satisfaction) / len(recent_satisfaction)
        retention_risk = max(0, 1 - recent_avg_satisfaction)
        
        # 增值服务潜力
        service_diversity = len(set().union(*[p.service_usage.services_used.keys() for p in daily_profiles]))
        upsell_potential = min(value_score * (service_diversity / 10), 1.0)
        
        return value_score, retention_risk, upsell_potential
    
    def _determine_communication_strategy(
        self, 
        semantic_analysis: LongTermSemanticAnalysis, 
        service_preference: ServicePreference
    ) -> str:
        """确定沟通策略"""
        if service_preference.self_service_tendency > 0.7:
            return "self_service"
        elif service_preference.human_service_preference > 0.7:
            return "personal"
        else:
            return "standard"
    
    def _determine_personalization_level(self, value_score: float) -> str:
        """确定个性化程度"""
        if value_score > 0.7:
            return "high"
        elif value_score > 0.4:
            return "medium"
        else:
            return "low"
    
    def _calculate_data_quality(self, daily_profiles: List[DailyProfile]) -> float:
        """计算数据质量分数"""
        if not daily_profiles:
            return 0.0
        
        # 基于数据完整性和时间跨度计算
        completeness = len(daily_profiles) / 30  # 假设30天为完整周期
        consistency = 1.0  # 可以基于数据一致性计算
        
        return min((completeness + consistency) / 2, 1.0)


# ============================== 全局实例工厂 ==============================
def create_profile_extractor(llm_client: Optional[ChatOpenAI] = None) -> ProfileExtractor:
    """
    创建用户画像提取器实例
    
    Args:
        llm_client: 可选的 LLM 客户端，如果不提供则使用默认配置
        
    Returns:
        ProfileExtractor 实例
    """
    if llm_client is None:
        # 使用系统配置的 LLM 实例
        try:
            import sys
            import os
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
            from agents.airport_service.core import structed_model
            llm_client = structed_model
        except ImportError:
            # 如果导入失败，使用备用配置
            raise ImportError("初始化ProfileExtractor失败，请检查模型配置")
    
    return ProfileExtractor(llm_client)

# 全局实例 - 延迟初始化
profile_extractor = None

def get_profile_extractor(llm_client: Optional[ChatOpenAI] = None) -> ProfileExtractor:
    """
    获取全局画像提取器实例（单例模式）
    
    Args:
        llm_client: 可选的 LLM 客户端
        
    Returns:
        ProfileExtractor 实例
    """
    global profile_extractor
    if profile_extractor is None:
        profile_extractor = create_profile_extractor(llm_client)
    return profile_extractor
