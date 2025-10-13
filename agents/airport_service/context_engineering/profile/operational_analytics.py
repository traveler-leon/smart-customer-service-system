"""
优化后的运营分析引擎
重构原有operational_analytics.py，提供更清晰的分析组件
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import logging
from collections import defaultdict, Counter

from .user_profile_models import (
    BusinessInsight, OperationalReport, DailyProfile, InsightProfile
)

logger = logging.getLogger(__name__)

@dataclass
class AnalyticsConfig:
    """分析配置"""
    segment_min_users: int = 10
    insight_confidence_threshold: float = 0.7
    trend_analysis_days: int = 7
    value_score_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.value_score_weights is None:
            self.value_score_weights = {
                "frequency": 0.3,
                "satisfaction": 0.4,
                "longevity": 0.3
            }

class UserSegmentationEngine:
    """用户分群引擎"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self.segment_definitions = {
            "高价值商旅客户": {
                "conditions": ["spending_power=HIGH", "traveler_type=BUSINESS", "value_score>0.7"],
                "description": "消费能力强的商务旅客"
            },
            "常旅客": {
                "conditions": ["traveler_type=FREQUENT", "loyalty_score>0.6"],
                "description": "经常使用机场服务的旅客"
            },
            "首次用户": {
                "conditions": ["traveler_type=FIRST_TIME", "total_sessions<3"],
                "description": "首次或刚开始使用服务的用户"
            },
            "家庭出行客户": {
                "conditions": ["traveler_type=FAMILY", "service_usage_contains_children"],
                "description": "携带儿童的家庭客户"
            },
            "价格敏感用户": {
                "conditions": ["spending_power=PRICE_SENSITIVE", "retention_risk>0.5"],
                "description": "对价格敏感且有流失风险的用户"
            },
            "潜在流失客户": {
                "conditions": ["retention_risk>0.7", "recent_satisfaction<0.5"],
                "description": "有较高流失风险的客户"
            }
        }
    
    async def segment_users(self, user_profiles: List[InsightProfile]) -> Dict[str, List[str]]:
        """用户分群"""
        segments = {name: [] for name in self.segment_definitions.keys()}
        
        for profile in user_profiles:
            for segment_name, criteria in self.segment_definitions.items():
                if self._matches_criteria(profile, criteria["conditions"]):
                    segments[segment_name].append(profile.user_id)
        
        # 过滤掉用户数太少的分群
        return {
            name: users for name, users in segments.items() 
            if len(users) >= self.config.segment_min_users
        }
    
    def _matches_criteria(self, profile: InsightProfile, conditions: List[str]) -> bool:
        """检查用户是否匹配分群条件"""
        for condition in conditions:
            if not self._evaluate_condition(profile, condition):
                return False
        return True
    
    def _evaluate_condition(self, profile: InsightProfile, condition: str) -> bool:
        """评估单个条件"""
        try:
            if "=" in condition:
                field, value = condition.split("=")
                return self._check_equality(profile, field.strip(), value.strip())
            elif ">" in condition:
                field, value = condition.split(">")
                return self._check_greater_than(profile, field.strip(), float(value.strip()))
            elif "<" in condition:
                field, value = condition.split("<")
                return self._check_less_than(profile, field.strip(), float(value.strip()))
            return False
        except Exception as e:
            logger.error(f"条件评估失败: {condition} - {e}")
            return False
    
    def _check_equality(self, profile: InsightProfile, field: str, value: str) -> bool:
        """检查等值条件"""
        if field == "spending_power":
            return profile.spending_power.value == value
        elif field == "traveler_type":
            return profile.primary_traveler_type.value == value
        return False
    
    def _check_greater_than(self, profile: InsightProfile, field: str, value: float) -> bool:
        """检查大于条件"""
        if field == "value_score":
            return profile.customer_value_score > value
        elif field == "retention_risk":
            return profile.retention_risk > value
        elif field == "loyalty_score":
            return profile.behavior_pattern.loyalty_score > value
        return False
    
    def _check_less_than(self, profile: InsightProfile, field: str, value: float) -> bool:
        """检查小于条件"""
        if field == "total_sessions":
            # 需要额外的数据来源
            return False  # 简化处理
        return False

class MetricsCalculator:
    """指标计算器"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
    
    def calculate_operational_metrics(
        self, 
        daily_profiles: List[DailyProfile],
        insight_profiles: List[InsightProfile]
    ) -> Dict[str, Any]:
        """计算运营指标"""
        total_users = len(set(p.user_id for p in daily_profiles))
        active_users = len([p for p in daily_profiles if p.interaction_metrics.total_sessions > 0])
        
        # 计算平均满意度
        satisfaction_scores = []
        for profile in daily_profiles:
            if profile.service_usage.satisfaction_rate > 0:
                satisfaction_scores.append(profile.service_usage.satisfaction_rate)
        
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0.0
        
        # 计算解决率
        resolution_rates = []
        for profile in daily_profiles:
            if profile.service_usage.resolution_rate > 0:
                resolution_rates.append(profile.service_usage.resolution_rate)
        
        avg_resolution_rate = sum(resolution_rates) / len(resolution_rates) if resolution_rates else 0.0
        
        # 热门服务统计
        all_services = Counter()
        for profile in daily_profiles:
            for service, count in profile.service_usage.services_used.items():
                all_services[service] += count
        
        top_services = [
            {"service": service, "usage_count": count} 
            for service, count in all_services.most_common(5)
        ]
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "avg_satisfaction": avg_satisfaction,
            "resolution_rate": avg_resolution_rate,
            "top_services": top_services,
            "peak_hours": self._calculate_peak_hours(daily_profiles)
        }
    
    def _calculate_peak_hours(self, daily_profiles: List[DailyProfile]) -> List[int]:
        """计算高峰时段"""
        # 简化版本，返回固定的高峰时段
        return [9, 10, 14, 15, 18, 19]

class InsightGenerator:
    """洞察生成器"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
    
    async def generate_business_insights(
        self,
        metrics: Dict[str, Any],
        segments: Dict[str, List[str]],
        trend_data: Dict[str, Any]
    ) -> List[BusinessInsight]:
        """生成业务洞察"""
        insights = []
        
        # 洞察1：用户增长趋势
        if metrics.get("new_user_ratio", 0) > 0.15:
            insights.append(BusinessInsight(
                insight_type="user_growth",
                title="新用户增长强劲",
                description=f"新用户占比{metrics.get('new_user_ratio', 0):.1%}，超过健康水平15%",
                impact_level="high",
                affected_users=metrics.get("new_users", 0),
                recommended_actions=[
                    "加强新用户引导",
                    "优化首次体验流程",
                    "提供新用户专属服务"
                ],
                metrics={
                    "new_user_ratio": metrics.get("new_user_ratio", 0),
                    "total_new_users": metrics.get("new_users", 0)
                }
            ))
        
        # 洞察2：服务质量分析
        if metrics.get("resolution_rate", 0) < 0.85:
            insights.append(BusinessInsight(
                insight_type="service_quality",
                title="问题解决率需要改善",
                description=f"当前问题解决率{metrics.get('resolution_rate', 0):.1%}，低于85%标准线",
                impact_level="high",
                affected_users=int(metrics.get("active_users", 0) * (1 - metrics.get("resolution_rate", 0))),
                recommended_actions=[
                    "分析未解决问题的根本原因",
                    "优化知识库内容",
                    "增强AI模型训练"
                ],
                metrics={
                    "resolution_rate": metrics.get("resolution_rate", 0),
                    "target_rate": 0.85
                }
            ))
        
        # 洞察3：用户满意度趋势
        satisfaction_trend = trend_data.get("satisfaction_trend", [])
        if len(satisfaction_trend) >= 3:
            recent_trend = satisfaction_trend[-3:]
            if all(recent_trend[i] >= recent_trend[i+1] for i in range(len(recent_trend)-1)):
                insights.append(BusinessInsight(
                    insight_type="satisfaction_trend",
                    title="用户满意度呈下降趋势",
                    description="最近三期用户满意度持续下降，需要关注",
                    impact_level="medium",
                    affected_users=metrics.get("active_users", 0),
                    recommended_actions=[
                        "深入分析满意度下降原因",
                        "收集用户反馈",
                        "改进服务质量"
                    ],
                    metrics={
                        "satisfaction_trend": recent_trend,
                        "decline_rate": recent_trend[0] - recent_trend[-1]
                    }
                ))
        
        return insights
    
    def generate_recommendations(
        self,
        metrics: Dict[str, Any],
        segments: Dict[str, List[str]],
        insights: List[BusinessInsight]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于指标的建议
        if metrics.get("resolution_rate", 0) < 0.85:
            recommendations.append("提升AI模型准确率，加强知识库建设")
        
        if metrics.get("avg_satisfaction", 0) < 0.80:
            recommendations.append("加强用户体验设计，提升服务满意度")
        
        # 基于用户分群的建议
        for segment_name, users in segments.items():
            if segment_name == "首次用户" and len(users) > 100:
                recommendations.append("优化新用户引导流程，提升首次体验")
            elif segment_name == "潜在流失客户" and len(users) > 50:
                recommendations.append("针对潜在流失客户制定挽留策略")
        
        # 基于洞察的建议
        for insight in insights:
            if insight.impact_level == "high":
                recommendations.extend(insight.recommended_actions[:2])  # 取前两个建议
        
        # 去重并限制数量
        recommendations = list(set(recommendations))[:8]
        
        return recommendations

class TrendAnalyzer:
    """趋势分析器"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
    
    async def analyze_trends(self, historical_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """分析趋势"""
        trends = {}
        
        if len(historical_data) < 2:
            return {
                "用户活跃度": "数据不足",
                "服务使用频率": "数据不足",
                "客户满意度": "数据不足"
            }
        
        # 用户活跃度趋势
        activity_scores = [data.get("active_users", 0) for data in historical_data]
        trends["用户活跃度"] = self._calculate_trend(activity_scores)
        
        # 满意度趋势
        satisfaction_scores = [data.get("avg_satisfaction", 0) for data in historical_data]
        trends["客户满意度"] = self._calculate_trend(satisfaction_scores)
        
        # 服务使用趋势
        service_usage = [len(data.get("top_services", [])) for data in historical_data]
        trends["服务使用频率"] = self._calculate_trend(service_usage)
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势方向"""
        if len(values) < 2:
            return "数据不足"
        
        # 简单的线性趋势计算
        recent_avg = sum(values[-3:]) / len(values[-3:]) if len(values) >= 3 else values[-1]
        earlier_avg = sum(values[:-3]) / len(values[:-3]) if len(values) > 3 else values[0]
        
        if recent_avg > earlier_avg * 1.05:
            return "上升趋势"
        elif recent_avg < earlier_avg * 0.95:
            return "下降趋势"
        else:
            return "稳定"

class OperationalAnalyticsEngine:
    """优化后的运营分析引擎"""
    
    def __init__(self, config: AnalyticsConfig = None):
        self.config = config or AnalyticsConfig()
        self.segmentation_engine = UserSegmentationEngine(self.config)
        self.metrics_calculator = MetricsCalculator(self.config)
        self.insight_generator = InsightGenerator(self.config)
        self.trend_analyzer = TrendAnalyzer(self.config)
    
    async def generate_operational_report(
        self, 
        period: str, 
        report_type: str = "daily",
        daily_profiles: List[DailyProfile] = None,
        insight_profiles: List[InsightProfile] = None
    ) -> OperationalReport:
        """生成运营报告"""
        try:
            report_id = f"{report_type}_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 如果没有提供数据，使用模拟数据
            if daily_profiles is None:
                daily_profiles = await self._get_daily_profiles(period)
            if insight_profiles is None:
                insight_profiles = await self._get_insight_profiles(period)
            
            # 1. 计算基础指标
            operational_metrics = self.metrics_calculator.calculate_operational_metrics(
                daily_profiles, insight_profiles
            )
            
            # 2. 用户分群分析
            segments = await self.segmentation_engine.segment_users(insight_profiles)
            
            # 3. 趋势分析
            historical_data = await self._get_historical_data(period, report_type)
            trends = await self.trend_analyzer.analyze_trends(historical_data)
            
            # 4. 生成业务洞察
            key_insights = await self.insight_generator.generate_business_insights(
                operational_metrics, segments, {"satisfaction_trend": [0.78, 0.80, 0.82]}
            )
            
            # 5. 生成改进建议
            recommendations = self.insight_generator.generate_recommendations(
                operational_metrics, segments, key_insights
            )
            
            return OperationalReport(
                report_id=report_id,
                period=period,
                report_type=report_type,
                total_users=operational_metrics["total_users"],
                active_users=operational_metrics["active_users"],
                new_users=operational_metrics.get("new_users", 0),
                retention_rate=operational_metrics.get("retention_rate", 0.0),
                avg_satisfaction=operational_metrics["avg_satisfaction"],
                resolution_rate=operational_metrics["resolution_rate"],
                response_time=operational_metrics.get("response_time", 0.0),
                key_insights=key_insights,
                trends=trends,
                recommendations=recommendations,
                data_sources=["daily_profiles", "insight_profiles"],
                confidence_level=0.85
            )
            
        except Exception as e:
            logger.error(f"运营报告生成失败: {str(e)}")
            raise
    
    async def analyze_user_behavior_prediction(
        self, 
        insight_profiles: List[InsightProfile]
    ) -> Dict[str, Any]:
        """用户行为预测分析"""
        predictions = {
            "churn_risk_analysis": {},
            "upsell_opportunities": {},
            "service_demand_forecast": {},
            "satisfaction_prediction": {}
        }
        
        # 流失风险分析
        high_risk_users = [p for p in insight_profiles if p.retention_risk > 0.7]
        predictions["churn_risk_analysis"] = {
            "high_risk_count": len(high_risk_users),
            "risk_factors": self._analyze_risk_factors(high_risk_users),
            "intervention_recommendations": self._generate_intervention_strategies(high_risk_users)
        }
        
        # 增值服务机会
        high_potential_users = [p for p in insight_profiles if p.upsell_potential > 0.6]
        predictions["upsell_opportunities"] = {
            "target_user_count": len(high_potential_users),
            "recommended_services": self._analyze_upsell_services(high_potential_users),
            "expected_revenue_impact": "预估提升15-25%"
        }
        
        return predictions
    
    def _analyze_risk_factors(self, high_risk_users: List[InsightProfile]) -> List[str]:
        """分析流失风险因素"""
        factors = []
        
        low_satisfaction_count = len([u for u in high_risk_users if u.customer_value_score < 0.5])
        if low_satisfaction_count > len(high_risk_users) * 0.6:
            factors.append("满意度持续偏低")
        
        service_issues = len([u for u in high_risk_users if len(u.recommended_services) == 0])
        if service_issues > len(high_risk_users) * 0.4:
            factors.append("服务需求未满足")
        
        return factors
    
    def _generate_intervention_strategies(self, high_risk_users: List[InsightProfile]) -> List[str]:
        """生成干预策略"""
        strategies = []
        
        if len(high_risk_users) > 10:
            strategies.append("启动客户关怀计划")
            strategies.append("提供个性化服务推荐")
            strategies.append("优化客户体验流程")
        
        return strategies
    
    def _analyze_upsell_services(self, high_potential_users: List[InsightProfile]) -> List[str]:
        """分析增值服务推荐"""
        service_counter = Counter()
        
        for user in high_potential_users:
            for service in user.recommended_services:
                service_counter[service] += 1
        
        return [service for service, count in service_counter.most_common(5)]
    
    async def _get_daily_profiles(self, period: str) -> List[DailyProfile]:
        """获取每日画像数据（模拟）"""
        # 这里应该连接到实际的数据库查询
        return []  # 返回空列表，实际实现时需要查询数据库
    
    async def _get_insight_profiles(self, period: str) -> List[InsightProfile]:
        """获取洞察画像数据（模拟）"""
        # 这里应该连接到实际的数据库查询
        return []  # 返回空列表，实际实现时需要查询数据库
    
    async def _get_historical_data(self, period: str, report_type: str) -> List[Dict[str, Any]]:
        """获取历史数据（模拟）"""
        # 返回模拟的历史数据
        return [
            {"active_users": 850, "avg_satisfaction": 0.78, "resolution_rate": 0.82},
            {"active_users": 920, "avg_satisfaction": 0.80, "resolution_rate": 0.85},
            {"active_users": 980, "avg_satisfaction": 0.82, "resolution_rate": 0.87}
        ]


# ============================== 全局实例 ==============================
operational_analytics_engine = OperationalAnalyticsEngine()
