import asyncio
from datetime import datetime
from typing import List, Dict, Any
import logging
import aiohttp

from trustcall import create_extractor
from langchain_openai import ChatOpenAI

from .user_profile_models import (
    SessionProfile, SessionMetrics, TechnicalContext, 
    ContentAnalysis, ServiceInteraction, UserAttributeInference,
    DailyProfile, DailyInteractionMetrics, DailyBehaviorPattern, DailyServiceUsage,
    LongTermSemanticAnalysis
)

logger = logging.getLogger(__name__)

class SemanticExtractor:   
    def __init__(self, llm_client: ChatOpenAI):
        self.llm = llm_client
        
        self.content_extractor = create_extractor(
            self.llm,
            tools=[ContentAnalysis],
            tool_choice="ContentAnalysis",
            enable_inserts=False
        )
        
        self.service_extractor = create_extractor(
            self.llm,
            tools=[ServiceInteraction],
            tool_choice="ServiceInteraction", 
            enable_inserts=False
        )
        
        self.attribute_extractor = create_extractor(
            self.llm,
            tools=[UserAttributeInference],
            tool_choice="UserAttributeInference",
            enable_inserts=False
        )
        
        # 长期语义分析提取器
        self.longterm_extractor = create_extractor(
            self.llm,
            tools=[LongTermSemanticAnalysis],
            tool_choice="LongTermSemanticAnalysis",
            enable_inserts=False
        )
    
    async def extract_session_semantics(
        self, 
        conversation_history: List[Dict[str, Any]],
        technical_context: TechnicalContext
    ):
        """提取完整的会话语义信息"""
        try:
            conversation_text = self._format_conversation(conversation_history)
            
            # 并行提取内容分析和服务交互
            content_task = self._extract_content_analysis(conversation_text)
            service_task = self._extract_service_interaction(conversation_text)
            attribute_task = self._extract_user_attributes(conversation_text, technical_context)
            
            content_analysis, service_interaction, user_attributes = await asyncio.gather(
                content_task, service_task, attribute_task
            )
            
            return content_analysis, service_interaction, user_attributes
            
        except Exception as e:
            logger.error(f"会话语义提取失败: {str(e)}")
            return None, None, None
    
    async def _extract_content_analysis(self, conversation_text: str) -> ContentAnalysis:
        """提取内容分析"""
        prompt = f"""
        从以下机场客服对话中分析用户的语言风格、情感状态和关注点等重要信息，提取结构化信息。
        对话内容：
        <conversation>
        {conversation_text}
        </conversation>

        请分析：
        1. 语言和交流风格：使用的语言、提问风格、整体情感倾向
        2. 情感状态量化：焦虑程度、紧急程度、满意度（基于具体表现给出0-1分数）
        3. 用户关注点：主要关注什么、有什么痛点、期望什么
        4. 内容特征：关键词、讨论话题、问题分类

        注意：
        - 情感分数要客观，基于具体的语言表现
        - 关注点要从用户实际表达中提取，不要臆测
        - 所有枚举值必须精确匹配模型定义
        """
        
        result = await asyncio.to_thread(
            self.content_extractor.invoke,
            {"messages": [{"role": "user", "content": prompt}]}
        )
        
        return result["responses"][0] if result and result.get("responses") else ContentAnalysis()
    
    async def _extract_service_interaction(self, conversation_text: str) -> ServiceInteraction:
        """提取服务交互信息"""
        prompt = f"""
        从以下机场客服对话中提取结构化的服务交互信息。
        对话内容：
        <conversation>
        {conversation_text}
        </conversation>

        请详细提取：
        1. 航班信息：航班号
        2. 服务使用：服务名称、类别、使用意图、状态
        3. 问题识别：问题描述、分类、严重性、解决状态、满意度

        注意：
        - 航班号要符合标准格式（如CA1234）
        - 所有分类必须从预定义选项中选择
        - 保持用户原始表达，不要过度解释
        """
        
        result = await asyncio.to_thread(
            self.service_extractor.invoke,
            {"messages": [{"role": "user", "content": prompt}]}
        )
        
        return result["responses"][0] if result and result.get("responses") else ServiceInteraction()
    
    async def _extract_user_attributes(self, conversation_text: str,technical_context: TechnicalContext) -> Dict[str, Any]:
        """提取用户属性推断"""
        prompt = f"""
        基于以下机场客服对话，推断用户的基本属性。

        ##对话内容：
        <conversation>
        {conversation_text}
        </conversation>
        ##当前用户的技术环境信息：
        <technical_context>
        {technical_context.model_dump_json()}
        </technical_context>

        请基于对话语境推断：
        1. 旅客类型：基于出行模式、服务需求、表达方式判断
        2. 用户角色：基于对话语境、责任关系判断
        4. 推断置信度：基于信息清晰度综合评估

        注意：
        - 只有有明确依据时才进行推断
        - 如果无法确定，对应字段返回null
        - 置信度要反映推断的可靠程度
        """
        
        result = await asyncio.to_thread(
            self.attribute_extractor.invoke,
            {"messages": [{"role": "user", "content": prompt}]}
        )
        return result["responses"][0] if result and result.get("responses") else UserAttributeInference()
    
    async def extract_longterm_semantics(self, daily_profiles: List[DailyProfile]) -> 'LongTermSemanticAnalysis':
        """
        提取长期语义分析 - 使用结构化提取
        
        Args:
            daily_profiles: 每日画像列表
            
        Returns:
            LongTermSemanticAnalysis: 长期语义分析结果
        """
        if not daily_profiles:
            logger.warning("没有每日画像数据进行长期语义分析")
            return self._create_default_longterm_analysis()
        
        try:
            # 聚合所有每日画像的内容进行分析
            aggregated_data = self._aggregate_daily_profiles_for_analysis(daily_profiles)
            
            # 构建结构化分析的prompt
            analysis_prompt = f"""
            基于以下用户的长期行为数据进行深度语义分析，提取结构化信息：
            
            ## 分析数据概览：
            - 分析周期：{len(daily_profiles)} 天
            - 总会话数：{aggregated_data['total_sessions']}
            - 平均每日会话：{aggregated_data['total_sessions'] / len(daily_profiles):.1f}
            
            ## 行为模式汇总：
            - 主要使用语言：{aggregated_data['dominant_languages']}
            - 常见查询风格：{aggregated_data['common_styles']}
            - 平均情感分数：{aggregated_data['avg_sentiment']:.2f}
            - 高频关键词：{aggregated_data['frequent_keywords']}
            - 话题分布：{aggregated_data['topic_distribution']}
            
            ## 服务使用情况：
            - 常查询航班：{aggregated_data['frequent_flights']}
            - 常用服务：{aggregated_data['frequent_services']}
            - 平均满意度：{aggregated_data['avg_satisfaction']:.2f}
            
            ## 分析要求：
            请基于以上数据进行深度语义分析，提取结构化信息：
            
            1. **确认的旅客类型**：基于长期行为模式推断用户的主要旅客类型
               - 商务旅客：频繁出行，关注效率，使用高端服务
               - 休闲旅客：偶尔出行，关注价格和体验
               - 中转旅客：主要关注转机服务和时间安排
               - 首次乘机：询问基础流程，表现出不确定性
               - 常旅客：熟悉流程，关注会员权益
            
            2. **核心需求列表**：从行为数据中提取的用户核心关注点
               - 基于高频关键词和话题分布
               - 考虑服务使用偏好
               - 反映真实的用户痛点
            
            3. **行为洞察**：对用户行为模式的深度理解
               - 沟通风格特征
               - 服务偏好趋势
               - 决策模式分析
            
            4. **个性化推荐**：针对该用户的服务推荐策略
               - 基于使用习惯的服务推荐
               - 沟通方式建议
               - 潜在需求挖掘
            
            5. **置信度评估**：分析结果的可信度（0-1）
               - 数据量是否充足
               - 行为模式是否一致
               - 推断是否有足够支撑
            
            6. **数据完整性**：当前数据的完整程度（0-1）
               - 覆盖的行为维度
               - 时间跨度充足性
               - 数据质量评估
            
            注意：
            - 所有推断必须有数据支撑，避免过度推测
            - 优先基于客观行为数据而非主观判断
            - 如果数据不足，应当降低置信度
            """
            
            # 使用结构化提取器
            result = await asyncio.to_thread(
                self.longterm_extractor.invoke,
                {"messages": [{"role": "user", "content": analysis_prompt}]}
            )
            
            longterm_analysis = result["responses"][0] if result and result.get("responses") else self._create_default_longterm_analysis()
            
            logger.info(f"长期语义分析完成，置信度: {longterm_analysis.confidence_level:.2f}")
            return longterm_analysis
            
        except Exception as e:
            logger.error(f"长期语义分析失败: {str(e)}")
            return self._create_default_longterm_analysis()
    
    def _aggregate_daily_profiles_for_analysis(self, daily_profiles: List[DailyProfile]) -> Dict[str, Any]:
        """聚合每日画像数据用于分析"""
        total_sessions = sum(p.interaction_metrics.total_sessions for p in daily_profiles)
        
        # 聚合语言分布
        language_counts = {}
        for profile in daily_profiles:
            lang = profile.behavior_pattern.dominant_language
            language_counts[lang] = language_counts.get(lang, 0) + profile.interaction_metrics.total_sessions
        
        dominant_languages = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # 聚合查询风格
        all_styles = []
        for profile in daily_profiles:
            all_styles.extend(profile.behavior_pattern.common_query_styles)
        common_styles = list(set(all_styles))[:5]
        
        # 计算平均情感分数
        sentiment_scores = [p.behavior_pattern.avg_sentiment_score for p in daily_profiles]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        
        # 聚合关注点
        all_keywords = []
        topic_counts = {}
        
        for profile in daily_profiles:
            all_keywords.extend(profile.behavior_pattern.frequent_keywords)
            for topic, count in profile.behavior_pattern.topic_trends.items():
                topic_counts[topic] = topic_counts.get(topic, 0) + count
        
        from collections import Counter
        frequent_keywords = [item[0] for item in Counter(all_keywords).most_common(15)]
        
        # 聚合服务使用
        flight_counts = {}
        service_counts = {}
        satisfaction_scores = []
        
        for profile in daily_profiles:
            for flight, count in profile.service_usage.flights_queried.items():
                flight_counts[flight] = flight_counts.get(flight, 0) + count
            
            for service, count in profile.service_usage.services_used.items():
                service_counts[service] = service_counts.get(service, 0) + count
            
            satisfaction_scores.append(profile.behavior_pattern.satisfaction_rate)
        
        frequent_flights = [item[0] for item in Counter(flight_counts).most_common(5)]
        frequent_services = [item[0] for item in Counter(service_counts).most_common(8)]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0.0
        
        return {
            'total_sessions': total_sessions,
            'dominant_languages': dominant_languages,
            'common_styles': common_styles,
            'avg_sentiment': avg_sentiment,
            'frequent_keywords': frequent_keywords,
            'topic_distribution': dict(Counter(topic_counts).most_common(10)),
            'frequent_flights': frequent_flights,
            'frequent_services': frequent_services,
            'avg_satisfaction': avg_satisfaction
        }
    
    
    def _create_default_longterm_analysis(self) -> 'LongTermSemanticAnalysis':
        """创建默认的长期分析结果"""
        
        return LongTermSemanticAnalysis(
            confirmed_traveler_type="休闲旅客",
            core_needs=["基础出行服务"],
            behavioral_insights=["常规查询"],
            personalization_recommendations=["标准服务推荐"],
            confidence_level=0.3,
            data_completeness=0.2
        )
    
    def _format_conversation(self, conversation_history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        formatted_lines = []
        
        for item in conversation_history:
            query = item.get('query', '')
            response = item.get('response', '')
            created_at = item.get('created_at', '')
            
            if query:
                formatted_lines.append(f"[{created_at}] 用户: {query}")
            if response:
                formatted_lines.append(f"[{created_at}] 助手: {response}")
        
        return "\n".join(formatted_lines)
    

class SessionMetricsCalculator:
    """会话指标计算器 - 纯数据计算"""
    def __init__(self):
        pass
    
    def calculate_session_metrics(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> SessionMetrics:
        """计算会话基础指标"""
        user_messages = [msg for msg in conversation_history if msg.get('role') == 'user']
        system_messages = [msg for msg in conversation_history if msg.get('role') == 'assistant']
        
        # 计算时间信息
        start_time = None
        end_time = None
        if conversation_history:
            try:
                start_time = datetime.fromisoformat(conversation_history[0].get('created_at', ''))
                end_time = datetime.fromisoformat(conversation_history[-1].get('created_at', ''))
            except:
                start_time = datetime.now()
                end_time = None
        
        duration_seconds = None
        if start_time and end_time:
            duration_seconds = int((end_time - start_time).total_seconds())
        
        # 计算平均响应时间（简化版本）
        avg_response_time = 2.0 if system_messages else None
        day = start_time.strftime('%Y-%m-%d')
        return SessionMetrics(
            start_time=start_time or datetime.now(),
            end_time=end_time or datetime.now(),
            day=day,
            duration_seconds=duration_seconds,
            turn_count=len(conversation_history),
            user_messages_count=len(user_messages),
            system_responses_count=len(system_messages),
            avg_response_time=avg_response_time
        )

class DataProfileAnalyzer:   
    async def extract_technical_context(self, conversation_history: List[Dict[str, Any]]) -> TechnicalContext:
        """提取技术环境信息 - 数据提取"""
        first_msg = conversation_history[0] if conversation_history else {}
        metadata = first_msg.get('metadata', {})
        ip_location = {}
        if metadata.get('query_ip'):
            ip_location = await self.get_ip_location(metadata.get('query_ip'))
        return TechnicalContext(
            source=metadata.get('query_source',''),
            device=metadata.get('query_device',''),
            ip=metadata.get('query_ip',''),
            country=ip_location.get('country',''),
            province=ip_location.get('province',''),
            city=ip_location.get('city',''),
            longitude=ip_location.get('longitude',0),
            latitude=ip_location.get('latitude',0),
            network_type=metadata.get('network_type',''),
        )
    async def get_ip_location(self, ip: str) -> Dict[str, Any]:
        """
        异步获取IP地理位置信息
        
        Args:
            ip: IP地址
            
        Returns:
            包含地理位置信息的字典
        """
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    
            if data['status'] == 'success':
                return {
                    "IP": ip,
                    "country": data.get('country'),
                    "province": data.get('regionName'),
                    "city": data.get('city'),
                    "longitude": data.get('lon'),
                    "latitude": data.get('lat')
                }
            else:
                return {
                    "IP": ip,
                    "country": "中国",
                    "province": "未知",
                    "city": "未知",
                    "longitude": 0,
                    "latitude": 0
                }
        except Exception as e:
            return {
                "IP": ip,
                "country": "中国",
                "province": "未知",
                "city": "未知",
                "longitude": 0,
                "latitude": 0
            }


class BehaviorAggregator:
    """行为数据聚合器 - 负责将多个会话画像聚合为每日画像"""
    def aggregate_daily_profile(
        self, 
        user_id: str, 
        date: str, 
        session_profiles: List[SessionProfile]
    ) -> DailyProfile:
        """聚合每日画像"""
        if not session_profiles:
            raise ValueError(f"用户 {user_id} 在 {date} 没有会话数据")
        
        # 简化的聚合逻辑
        total_sessions = len(session_profiles)
        total_turns = sum(s.session_metrics.turn_count for s in session_profiles)
        avg_session_depth = total_turns / total_sessions if total_sessions > 0 else 0.0
        
        # 基础交互指标
        interaction_metrics = DailyInteractionMetrics(
            date=date,
            total_sessions=total_sessions,
            total_turns=total_turns,
            avg_session_depth=avg_session_depth,
            avg_session_duration=10.0  # 简化值
        )
        
        # 基础行为模式
        behavior_pattern = DailyBehaviorPattern(
            dominant_language="中文",
            avg_sentiment_score=0.6  # 简化值
        )
        
        # 基础服务使用
        service_usage = DailyServiceUsage(
            resolution_rate=0.8,  # 简化值
            satisfaction_rate=0.7  # 简化值
        )
        
        return DailyProfile(
            user_id=user_id,
            date=date,
            interaction_metrics=interaction_metrics,
            behavior_pattern=behavior_pattern,
            service_usage=service_usage,
            sessions_included=[sp.session_metrics.session_id for sp in session_profiles]
        )
