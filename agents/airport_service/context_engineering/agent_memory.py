"""
智能体记忆集成工具
按照LangGraph + Mem0最佳实践，为每个智能体节点集成记忆功能
"""
from typing import Dict, Any, List, Optional
import asyncio
from .memory_manager import memory_manager
from common.logging import get_logger

logger = get_logger("agent_memory")
class AgentMemoryMixin:
    """
    智能体记忆混入类
    为智能体节点提供记忆存储和检索功能
    """
    
    @staticmethod
    async def store_agent_conversation_interaction(
        user_id: str,
        application_id: str,
        run_id: str,
        agent_id: str,
        messages,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        存储智能体交互记忆
        
        Args:
            user_id: 用户ID
            application_id: 应用ID
            run_id: 会话ID  
            agent_id: 智能体ID
            messages: 用户查询
            response: 智能体回复
            metadata: 额外元数据
            
        Returns:
            memory_id: 记忆id
        """
        try:
            memory_id = await memory_manager.store_conversation(
                user_id=user_id,
                application_id=application_id,
                run_id=run_id,
                agent_id=agent_id,
                messages=messages,
                response=response,
                metadata=metadata
            )
            
            logger.debug(f"智能体交互已存储: {agent_id} - {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"存储智能体交互失败: {agent_id} - {e}")
            return None

    @staticmethod
    async def retrieve_relevant_conversation_memories(
        query: str,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        similarity_weight: float = 0.5,
        time_weight: float = 0.2,
        quality_weight: float = 0.3,
        min_quality_score: float = 0.7,
        time_decay_days: int = 30,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            # 使用智能筛选功能
            smart_memories = await memory_manager.get_smart_filtered_memories(
                query=query,
                user_id=user_id,
                application_id=application_id,
                agent_id=agent_id,
                similarity_weight=similarity_weight,
                time_weight=time_weight,
                quality_weight=quality_weight,
                min_quality_score=min_quality_score,
                time_decay_days=time_decay_days,
                limit=limit,
            )
            
            logger.debug(f"智能筛选到 {len(smart_memories)} 条优质记忆")
            return smart_memories
            
        except Exception as e:
            logger.error(f"智能检索记忆失败: {e}")
            return []

    @staticmethod
    async def retrieve_relevant_expert_qa_memories(
        query: str,
        application_id: Optional[str] = None,
        expert_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        检索相关专家QA记忆
        
        Args:
            query: 查询文本
            application_id: 应用名称筛选 (可选)
            expert_id: 专家ID筛选 (可选)
            tags: 标签筛选 (可选)
            services: 服务筛选 (可选)
            limit: 返回数量限制
            
        Returns:
            相关专家QA记忆列表
        """
        try:
            expert_qa_memories = await memory_manager.search_expert_qa(
                query=query,
                application_id=application_id,
                expert_id=expert_id,
                tags=tags,
                services=services,
                limit=limit,
            )
            
            logger.debug(f"检索到 {len(expert_qa_memories)} 条专家QA记忆")
            return expert_qa_memories
            
        except Exception as e:
            logger.error(f"检索专家QA记忆失败: {e}")
            return []
    
    
def memory_enabled_agent(application_id: str,agent_id: Optional[str] = None):
    def decorator(agent_func):
        async def wrapper(state: Dict[str, Any], config=None, *args, **kwargs):
            run_id = config["configurable"].get("thread_id", "unknown_thread") 
            user_id = config["configurable"].get("user_id", "unknown_user")
            user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
            metadata = state.get("metadata") if state.get("metadata") else config["configurable"].get("metadata", {})
    
            try:
                result = await agent_func(state, config, *args, **kwargs)
                # 提取智能体回复
                agent_response = ""
                msg_name = ""
                if isinstance(result, dict):
                    # 从返回的消息中提取内容
                    messages = result.get("messages", [])
                    if messages:
                        agent_response = messages[-1].content
                        msg_name = messages[-1].name
                if user_query and agent_response:
                    
                    asyncio.create_task(
                        AgentMemoryMixin.store_agent_conversation_interaction(
                            user_id=user_id,
                            application_id=application_id,
                            run_id=run_id,
                            agent_id=agent_id if agent_id else msg_name,
                            messages=user_query,
                            response=agent_response,
                            metadata=metadata
                        )
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"智能体记忆装饰器异常: {agent_id} - {e}")
                # 即使记忆功能失败，也要返回原始结果
                if config is not None:
                    return await agent_func(state, config, *args, **kwargs)
                else:
                    return await agent_func(state, *args, **kwargs)
        
        return wrapper
    return decorator


async def get_relevant_conversation_memories(
    query: str,
    user_id: Optional[str] = None,
    application_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    score_limit: float = 0.8,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """获取相关记忆 - 使用 memory_manager 统一接口"""
    try:
        results = await AgentMemoryMixin.retrieve_relevant_conversation_memories(
            query=query,
            user_id=user_id,
            application_id=application_id,
            agent_id=agent_id,  
            min_quality_score=score_limit,
            limit=limit
        )
        
        relevant_memories = []
        for result in results:
            if result.get('composite_score', 0.0) >= score_limit:
                memory_item = {
                    "query": result.get('query', ''),
                    "response": result.get('response', ''),
                    "created_at": result.get('created_at', ''),
                }
                relevant_memories.append(memory_item)
        
        return relevant_memories
        
    except Exception as e:
        logger.error(f"获取相关记忆失败: {agent_id} - {e}")
        return []


async def get_relevant_expert_qa_memories(
    query: str,
    application_id: Optional[str] = None,
    expert_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    services: Optional[List[str]] = None,
    score_limit: float = 0.0,  # 改为更宽松的默认值
    limit: int = 10
) -> List[Dict[str, Any]]:
    """获取相关专家QA记忆 - 使用 memory_manager 统一接口"""
    try:
        results = await memory_manager.search_expert_qa(
            query=query,
            application_id=application_id,
            expert_id=expert_id,
            tags=tags,
            services=services,
            limit=limit
        )
        
        relevant_qa_memories = []
        for result in results:
            # 按相关度评分筛选
            if result.get('relevance_score', 0.0) <= score_limit:
                memory_item = {
                    "question": result.get('question', ''),
                    "answer": result.get('answer', ''),
                    "expert_id": result.get('expert_id', ''),
                    "application_id": result.get('application_id', ''),
                    "images": result.get('images', ''),
                    "tags": result.get('tags', ''),
                    "services": result.get('services', ''),
                    "relevance_score": result.get('relevance_score', 0.0),
                    "created_at": result.get('created_at', ''),
                }
                relevant_qa_memories.append(memory_item)
        
        logger.debug(f"原始搜索结果: {len(results)} 条，筛选后: {len(relevant_qa_memories)} 条 (score_limit={score_limit})")
        return relevant_qa_memories
        
    except Exception as e:
        logger.error(f"获取相关专家QA记忆失败: {e}")
        return []



class MemoryEnabledAgent:
    """
    支持记忆的智能体基类
    可以被具体的智能体继承使用
    """
    
    def __init__(self, application_id: str, agent_id: str):
        self.application_id = application_id
        self.agent_id = agent_id
        self.memory_mixin = AgentMemoryMixin()
    
    async def store_interaction(
        self,
        user_id: str,
        thread_id: str,
        user_query: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """存储交互记忆"""
        return await self.memory_mixin.store_agent_interaction(
            user_id=user_id,
            application_id=self.application_id,
            run_id=thread_id,
            agent_id=self.agent_id,
            user_query=user_query,
            agent_response=agent_response,
            metadata=metadata
        )
    
    async def get_relevant_memories(
        self,
        user_id: str,
        current_query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """获取相关记忆"""
        return await self.memory_mixin.retrieve_relevant_memories(
            user_id=user_id,
            current_query=current_query,
            agent_id=self.agent_id,
            limit=limit
        )
    
    async def get_smart_filtered_memories(
        self,
        user_id: str,
        current_query: str,
        limit: int = 5,
        similarity_weight: float = 0.5,
        time_weight: float = 0.2,
        quality_weight: float = 0.3,
        min_quality_score: float = 0.7,
        time_decay_days: int = 30
    ) -> List[Dict[str, Any]]:
        """获取智能筛选的记忆"""
        return await self.memory_mixin.retrieve_smart_filtered_memories(
            user_id=user_id,
            current_query=current_query,
            agent_name=self.agent_name,
            limit=limit,
            similarity_weight=similarity_weight,
            time_weight=time_weight,
            quality_weight=quality_weight,
            min_quality_score=min_quality_score,
            time_decay_days=time_decay_days
        )

    async def get_relevant_expert_qa_memories(
        self,
        current_query: str,
        expert_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """获取相关专家QA记忆"""
        return await AgentMemoryMixin.retrieve_relevant_expert_qa_memories(
            query=current_query,
            application_id=self.application_id,
            expert_id=expert_id,
            tags=tags,
            services=services,
            limit=limit
        )
