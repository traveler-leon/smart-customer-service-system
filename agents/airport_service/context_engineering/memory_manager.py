"""
动态记忆工程管理器
包含对话记忆、专家审核和用户画像三个核心模块
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
import json
import asyncio
import concurrent
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from mem0 import AsyncMemory
from mem0.configs.base import MemoryConfig
from mem0.vector_stores.configs import VectorStoreConfig
from mem0.llms.configs import LlmConfig
from mem0.embeddings.configs import EmbedderConfig
from langchain_openai import ChatOpenAI
from agents.airport_service.core import structed_model
from config.utils import config_manager
from common.logging import get_logger

logger = get_logger("memory_manager")

class MemoryType(Enum):
    """记忆类型枚举"""
    CONVERSATION = "conversation"  # 对话记忆
    USER_PROFILE = "user_profile"  # 用户画像记忆


@dataclass
class ConversationMemory:
    """对话记忆数据结构"""
    conversation_id: str
    user_id: str
    thread_id: str
    query: str
    response: str
    timestamp: datetime
    metadata: Dict[str, Any]
    is_expert_approved: bool = False
    quality_score: Optional[float] = None
    tags: List[str] = None
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class UserProfileMemory:
    """用户画像记忆数据结构"""
    user_id: str
    profile_data: Dict[str, Any]
    preferences: Dict[str, Any]
    behavioral_patterns: Dict[str, Any]
    last_updated: datetime
    extraction_source: str  # 数据来源标识
    
    def to_dict(self):
        data = asdict(self)
        data['last_updated'] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)



class AsyncMem0Client(AsyncMemory):
    """异步记忆管理器"""
    def __init__(self, config: MemoryConfig = MemoryConfig()):
        super().__init__(config)
    async def get_all(
        self,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ):

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_memories = executor.submit(self._get_all_from_vector_store, filters, limit)
            future_graph_entities = (
                executor.submit(self.graph.get_all, filters, limit) if self.enable_graph else None
            )

            concurrent.futures.wait(
                [future_memories, future_graph_entities] if future_graph_entities else [future_memories]
            )

            all_memories_result = future_memories.result()
            graph_entities_result = future_graph_entities.result() if future_graph_entities else None

        if self.enable_graph:
            return {"results": all_memories_result, "relations": graph_entities_result}
        return {"results": all_memories_result}
    
    async def search(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None,
    ):

        vector_store_task = asyncio.create_task(self._search_vector_store(query, filters, limit, threshold))
        graph_task = None
        if self.enable_graph:
            if hasattr(self.graph.search, "__await__"):  # Check if graph search is async
                graph_task = asyncio.create_task(self.graph.search(query, filters, limit))
            else:
                graph_task = asyncio.create_task(asyncio.to_thread(self.graph.search, query, filters, limit))

        if graph_task:
            original_memories, graph_entities = await asyncio.gather(vector_store_task, graph_task)
        else:
            original_memories = await vector_store_task
            graph_entities = None

        if self.enable_graph:
            return {"results": original_memories, "relations": graph_entities}

        return {"results": original_memories}
    
    async def update(self, memory_id, data,metadata:Optional[Dict[str, Any]] = None):
        embeddings = await asyncio.to_thread(self.embedding_model.embed, data, "update")
        existing_embeddings = {data: embeddings}

        await self._update_memory(memory_id, data, existing_embeddings,metadata)
        return {"message": "Memory updated successfully!"}
    

class MemoryManager:
    """动态记忆管理器"""
    
    def __init__(self):
        self.conversation_memory = None
        self.profile_memory = None
        self._initialized = False
    
    async def initialize(self):
        """初始化记忆管理器"""
        if self._initialized:
            return
            
        try:
            # 从配置获取向量存储参数
            chroma_config = config_manager.get_text2sql_config().get("storage", {})
            
            # 从原有配置文件获取嵌入模型 (复用现有的)
            from .memery.emb import embedder
            
            # 对话记忆配置
            conversation_config = MemoryConfig(
                llm=LlmConfig(provider="langchain", config={"model": structed_model}),
                vector_store=VectorStoreConfig(
                    provider="chroma",
                    config={
                        "collection_name": "conversation_memory",
                        "host": chroma_config.get("host", "192.168.0.200"),
                        "port": str(chroma_config.get("port", "8000"))
                    }
                ),
                embedder=EmbedderConfig(
                    provider="langchain",
                    config={"model": embedder}
                ),
                version="v1.1"
            )
            self.conversation_memory = AsyncMem0Client(config=conversation_config)
            
            # 用户画像记忆配置
            profile_config = MemoryConfig(
                llm=LlmConfig(provider="langchain", config={"model": structed_model}),
                vector_store=VectorStoreConfig(
                    provider="chroma",
                    config={
                        "collection_name": "user_profile_memory",
                        "host": chroma_config.get("host", "192.168.0.200"),
                        "port": str(chroma_config.get("port", "8000"))
                    }
                ),
                embedder=EmbedderConfig(
                    provider="langchain",
                    config={"model": embedder}
                ),
                version="v1.1"
            )
            self.profile_memory = AsyncMem0Client(config=profile_config)
            

            
            self._initialized = True
            logger.info("记忆管理器初始化完成")
            
        except Exception as e:
            logger.error(f"记忆管理器初始化失败: {e}", exc_info=True)
            raise
    
    async def store_conversation(
        self, 
        application_id: str,
        user_id: str, 
        run_id: str, 
        agent_id: str,
        messages,
        response: str,         
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """      
        Args:
            application_id: 应用名称
            user_id: 用户ID
            run_id: 会话ID
            agent_id: 智能体名称
            query: 用户查询
            response: 系统回复
            metadata: 额外元数据
            
        Returns:
            memory_id: 记忆id
        """
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}
        try:
            metadata = {
                "agent_memory_type": MemoryType.CONVERSATION.value,
                "response": response,  
                "application_id": application_id,  
                "expert_verified": False,  
                "expert_id": "",  
                "expert_corrected_response": "",  
                "quality_score": 0.0, 
                "user_approved": 0,
            }
            
            if metadata:
                for key, value in metadata.items():
                    if value is not None: 
                        metadata[key] = value
            
            result = await self.conversation_memory.add(
                messages=messages, 
                user_id=user_id,
                agent_id=agent_id,
                run_id=run_id,
                metadata={**base_metadata, **metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"对话记忆已存储: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"存储对话记忆失败: {e}", exc_info=True)
            raise
    
    async def get_conversation_history(
        self, 
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        query: Optional[str] = None,
        response: Optional[str] = None,
        expert_verified: Optional[bool] = None,
        user_approved: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史 - 使用 mem0 v2 filters 实现高效查询
        
        Args:
            application_id: 应用名称 (可选)
            user_id: 用户ID (可选)
            run_id: 会话ID (可选) 
            agent_id: 智能体名称 (可选)
            query: 用户查询 (可选)
            response: 系统回复 (可选)
            expert_verified: 是否专家校验 (可选)
            user_approved: 是否用户校验 (可选)
            start_date: 开始日期 (可选)
            end_date: 结束日期 (可选)
            limit: 返回数量限制

            
        Returns:
            对话记忆列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建过滤条件列表 - 按照用户提供的案例格式
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.CONVERSATION.value}})
            
            # 可选条件
            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if agent_id:
                filter_conditions.append({"agent_id": {"$eq": agent_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if run_id:
                filter_conditions.append({"run_id": {"$eq": run_id}})
            if expert_verified is not None:
                filter_conditions.append({"expert_verified": {"$eq": expert_verified}})
            if user_approved is not None:
                filter_conditions.append({"user_approved": {"$eq": user_approved}})
            if query:
                filter_conditions.append({"data": {"$eq": query}})
            if response:
                filter_conditions.append({"response": {"$eq": response}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            # 使用 get_all 进行查询
            result = await self.conversation_memory.get_all(filters=filters, limit=limit)
            
            # 按照案例中的模式处理返回结果
            if isinstance(result, dict) and 'results' in result:
                all_memories = result['results']
                # 如果返回的是协程，按照案例进行await
                import inspect
                if inspect.iscoroutine(all_memories):
                    all_memories = await all_memories
            else:
                logger.warning(f"意外的get_all返回格式: {type(result)}")
                all_memories = []
            
            conversations = []
            for memory in all_memories:
                metadata = memory.get('metadata', {})
                
                # 时间过滤（在数据库层面无法高效过滤，所以在这里手动过滤）
                if start_date or end_date:
                    memory_time = None
                    if 'created_at' in memory:
                        try:
                            # 解析数据库中的时间字符串（带时区信息）
                            created_at_str = memory['created_at']
                            if created_at_str.endswith('Z'):
                                # 处理UTC时间标识
                                memory_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            else:
                                # 处理已经包含时区信息的时间字符串
                                memory_time = datetime.fromisoformat(created_at_str)
                        except Exception as e:
                            logger.debug(f"时间解析失败: {created_at_str} - {e}")
                            memory_time = None
                    
                    if memory_time:
                        # 比较时间（现在传入的start_date和end_date都已经是带时区的）
                        if start_date:
                            # 将memory_time转换为UTC进行比较
                            memory_time_utc = memory_time.astimezone(start_date.tzinfo)
                            if memory_time_utc < start_date:
                                continue
                        
                        if end_date:
                            # 将memory_time转换为UTC进行比较  
                            memory_time_utc = memory_time.astimezone(end_date.tzinfo)
                            if memory_time_utc > end_date:
                                continue
                
                # 构造返回数据
                conversation_data = {
                    "memory_id": memory.get('id'),
                    "user_id": memory.get('user_id'),
                    "application_id": metadata.get('application_id', ''),
                    "run_id": memory.get('run_id', ''),
                    "agent_id": memory.get('agent_id', ''),
                    "query": memory.get('memory', ''),
                    "response": metadata.get('response', ''),
                    "expert_verified": metadata.get('expert_verified', False),
                    "expert_id": metadata.get('expert_id', ''),
                    "expert_corrected_response": metadata.get('expert_corrected_response', ''),
                    "quality_score": metadata.get('quality_score'),
                    "user_approved": metadata.get('user_approved', False),
                    "created_at": memory.get('created_at'),
                    "updated_at": memory.get('updated_at')
                }
                conversations.append(conversation_data)
            
            # 按创建时间排序
            conversations.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            conversations = conversations[:limit]
            logger.info(f"对话历史查询完成: 过滤条件={filters}, 获取={len(all_memories)}, 返回={len(conversations)}")
            return conversations
            
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}", exc_info=True)
            return []
    
    async def handle_user_feedback(
        self,
        response: str,
        user_approved: Optional[int] = 0,
    ) -> bool:
        """
        用户点赞对话
        
        Args:
            response: 系统回复
            user_approved: 是否用户审核通过
            
        Returns:
            是否成功更新
        """
        if not self._initialized:
            await self.initialize()
    
        try:
            his_conversation = self.get_conversation_history(response=response)
            memory_id = his_conversation[0]['memory_id']
            query = his_conversation[0]['query']
            # 构建更新的元数据
            updated_metadata = {
                "user_approved": user_approved,
            }
        
            
            await self.conversation_memory.update(
                memory_id=memory_id,
                data=query,
                metadata=updated_metadata
            )
            
            logger.info(f"用户点赞完成: memory_id={memory_id}, approved={user_approved}")
            return True
            
        except Exception as e:
            logger.error(f"专家审核失败: {e}", exc_info=True)
            return False

    async def expert_review_conversation(
        self,
        memory_id: str,
        query: str,
        expert_approved: bool,
        quality_score: Optional[float] = None,
        corrected_response: Optional[str] = None,
        expert_id: Optional[str] = None
    ) -> bool:
        """
        专家审核对话 - 使用 mem0 update API 更新记忆
        
        Args:
            memory_id: 记忆ID (mem0返回的memory_id)
            expert_approved: 是否专家审核通过
            quality_score: 质量评分 (0-1, 可选)
            corrected_response: 专家修正的回答内容 (可选)
            expert_id: 审核专家ID (可选)
            
        Returns:
            是否成功更新
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建更新的元数据
            updated_metadata = {
                "expert_verified": expert_approved,
            }
            if quality_score is not None:
                updated_metadata["quality_score"] = quality_score    
            if expert_id:
                updated_metadata["expert_id"] = expert_id
            if corrected_response:
                updated_metadata["expert_corrected_response"] = corrected_response
            
            await self.conversation_memory.update(
                memory_id=memory_id,
                data=query,
                metadata=updated_metadata
            )
            
            logger.info(f"专家审核完成: memory_id={memory_id}, approved={expert_approved}, score={quality_score}")
            return True
            
        except Exception as e:
            logger.error(f"专家审核失败: {e}", exc_info=True)
            return False

    
    async def batch_expert_review(
        self,
        review_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量专家审核 - 调用单个 expert_review_conversation 方法
        
        Args:
            review_items: 审核项目列表，每个项目包含:
                - memory_id: 记忆ID
                - expert_approved: 是否通过
                - quality_score: 质量评分
                - corrected_response: 修正回答 (可选)
                - expert_id: 审核专家ID (可选)
                
        Returns:
            批量更新结果统计
        """
        if not self._initialized:
            await self.initialize()
        
        success_count = 0
        failed_count = 0
        
        try:
            # 逐个调用 expert_review_conversation 方法
            for item in review_items:
                try:
                    memory_id = item.get('memory_id')
                    query = item.get('query')
                    expert_approved = item.get('expert_approved', False)
                    quality_score = item.get('quality_score')
                    corrected_response = item.get('corrected_response')
                    expert_id = item.get('expert_id')
                    
                    # 调用单个审核方法
                    result = await self.expert_review_conversation(
                        memory_id=memory_id,
                        query=query,
                        expert_approved=expert_approved,
                        quality_score=quality_score,
                        corrected_response=corrected_response,
                        expert_id=expert_id
                    )
                    
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as single_error:
                    logger.error(f"单个审核失败: {item.get('memory_id')} - {single_error}")
                    failed_count += 1
            
            result = {
                "total_items": len(review_items),
                "update_success": success_count,
                "update_failed": failed_count,
                "timestamp": datetime.now().isoformat(),
            }
            
            logger.info(f"批量专家审核完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"批量专家审核失败: {e}", exc_info=True)
            return {
                "total_items": len(review_items),
                "update_success": success_count,
                "update_failed": failed_count,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def search_conversations(
        self,
        query: str,
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        expert_verified: Optional[bool] = None,
        user_approved: Optional[bool] = None,
        min_quality_score: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """        
        Args:
            query: 查询文本
            application_id: 应用名称筛选 (可选)
            user_id: 用户ID筛选 (可选)
            agent_id: 智能体名称筛选 (可选)
            expert_verified: 专家校验状态筛选 (可选)
            user_approved: 用户校验状态筛选 (可选)
            min_quality_score: 最低质量评分筛选 (可选)
            limit: 返回数量限制
            
        Returns:
            相似对话记录列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.CONVERSATION.value}})
            
            # 可选条件
            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if agent_id:
                filter_conditions.append({"agent_id": {"$eq": agent_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if expert_verified is not None:
                filter_conditions.append({"expert_verified": {"$eq": expert_verified}})
            if user_approved is not None:
                filter_conditions.append({"user_approved": {"$eq": user_approved}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            search_results = await self.conversation_memory.search(
                query=query,
                filters=filters,
                limit=limit
            )
            
            conversations = []
            # 处理不同版本 API 的返回格式 - 按照案例模式
            if isinstance(search_results, dict) and 'results' in search_results:
                results = search_results['results']
                # 如果返回的是协程，按照案例进行await
                import inspect
                if inspect.iscoroutine(results):
                    results = await results
            else:
                logger.warning(f"意外的search返回格式: {type(search_results)}")
                results = []
            
            for result in results:
                metadata = result.get('metadata', {})
                
                # 只需要手动应用质量评分过滤，其他条件已在数据库层面过滤
                if min_quality_score is not None and (metadata.get('quality_score') or 0) < min_quality_score:
                    continue
                
                # 构造返回数据
                conversation_data = {
                    "memory_id": result.get('id'),
                    "user_id": result.get('user_id'),
                    "agent_id": result.get('agent_id', ''),
                    "run_id": result.get('run_id', ''),
                    "application_id": metadata.get('application_id', ''),
                    "query": result.get('memory', ''),
                    "response": metadata.get('response', ''), 
                    "expert_verified": metadata.get('expert_verified', False),
                    "quality_score": metadata.get('quality_score'),
                    "user_approved": metadata.get('user_approved', False),
                    "relevance_score": result.get('score', 0.0),
                    "created_at": result.get('created_at'),
                    "metadata": metadata
                }
                conversations.append(conversation_data)
                
                # 达到目标数量就停止
                if len(conversations) >= limit:
                    break
            
            logger.info(f"相似度搜索完成: query='{query}', 结果数量={len(conversations)}")
            return conversations
            
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}", exc_info=True)
            return []
    
    async def get_expert_approved_examples(
        self, 
        query: str, 
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_approved: Optional[bool] = None,
        min_quality_score: float = 0.8,
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        """
        从对话记忆中获取专家审核的优质QA作为prompt examples
        保持对话的时序性和完整性
        
        Args:
            query: 当前查询，用于相似度匹配
            application_id: 应用名称筛选 (可选)
            user_id: 用户ID筛选 (可选)
            agent_id: 智能体名称筛选 (可选)
            user_approved: 用户校验状态筛选 (可选)
            min_quality_score: 最低质量评分
            limit: 返回数量
            
        Returns:
            优质QA示例列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 使用相似度搜索专家审核通过的对话
            results = await self.search_conversations(
                query=query,
                application_id=application_id,
                user_id=user_id,
                agent_id=agent_id,
                expert_verified=True,
                user_approved=user_approved,
                min_quality_score=min_quality_score,
                limit=limit
            )
            
            examples = []
            for result in results:
                # 获取用户查询
                user_query = result.get('query', '')
                
                # 优先使用专家纠正的回答，否则使用原始回答
                assistant_response = result.get('metadata', {}).get('expert_corrected_response')
                if not assistant_response:
                    assistant_response = result.get('response', '')
                
                quality_score = result.get('quality_score', 0)
                
                if user_query and assistant_response and quality_score >= min_quality_score:
                    examples.append({
                        "user": user_query,
                        "assistant": assistant_response,
                        "quality_score": quality_score,
                        "memory_id": result.get('memory_id'),
                        "agent_name": result.get('agent_name'),
                        "expert_corrected": bool(result.get('metadata', {}).get('expert_corrected_response'))
                    })
                    
                if len(examples) >= limit:
                    break
            
            logger.info(f"获取到 {len(examples)} 个优质QA示例")
            return examples
            
        except Exception as e:
            logger.error(f"获取优质QA示例失败: {e}", exc_info=True)
            return []
    
    async def get_smart_filtered_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        application_id: Optional[str] = None,
        user_approved: Optional[bool] = None,
        min_quality_score: float = 0.7,
        similarity_weight: float = 0.5,
        time_weight: float = 0.2,
        quality_weight: float = 0.3,
        time_decay_days: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        智能记忆筛选 - 基于多因子综合评分的记忆检索
        
        综合考虑因素：
        1. 向量相似度 (similarity_weight)
        2. 时间遗忘因子 (time_weight) - 越新的记忆权重越高
        3. 专家评分 (quality_weight)
        
        Args:
            query: 查询文本
            user_id: 用户ID筛选 (可选)
            agent_id: 智能体名称筛选 (可选)
            application_id: 应用名称筛选 (可选)
            user_approved: 用户校验状态筛选 (可选)
            limit: 返回数量
            min_quality_score: 最低质量评分
            similarity_weight: 相似度权重 (默认0.5)
            time_weight: 时间权重 (默认0.2)
            quality_weight: 质量权重 (默认0.3)
            time_decay_days: 时间衰减周期天数 (默认30天)
            
        Returns:
            按综合得分排序的记忆列表
        """
        if not self._initialized:
            await self.initialize()
        
        # 权重归一化
        total_weight = similarity_weight + time_weight + quality_weight
        if total_weight != 1.0:
            similarity_weight /= total_weight
            time_weight /= total_weight
            quality_weight /= total_weight
            logger.warning(f"权重已归一化: similarity={similarity_weight:.2f}, time={time_weight:.2f}, quality={quality_weight:.2f}")
        
        try:
            # 获取更多候选记忆用于筛选 (通常获取limit的3-5倍)
            candidate_limit = min(limit * 5, 100)
            
            # 搜索专家审核通过的对话
            results = await self.get_expert_approved_examples(
                query=query,
                user_id=user_id,
                application_id=application_id,
                agent_id=agent_id,
                user_approved=user_approved,
                min_quality_score=min_quality_score,
                limit=candidate_limit,
            )
            
            if not results:
                logger.info("未找到符合条件的专家审核记忆")
                return []
            
            # 计算当前时间用于时间衰减
            current_time = datetime.now()
            scored_memories = []
            
            for result in results:
                try:
                    # 1. 获取相似度得分 (已归一化到0-1)
                    similarity_score = result.get('relevance_score', 0.0)
                    
                    # 2. 计算时间衰减因子
                    created_at_str = result.get('created_at', '')
                    time_score = 0.0
                    
                    if created_at_str:
                        try:
                            # 解析时间字符串
                            if 'T' in created_at_str:
                                # ISO格式: 2024-01-01T12:00:00
                                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            else:
                                # 简单格式: 2024-01-01
                                created_at = datetime.strptime(created_at_str[:19], '%Y-%m-%d %H:%M:%S')
                            
                            # 计算时间差（天数）
                            time_diff = (current_time - created_at).days
                            
                            # 时间衰减计算: 使用指数衰减，新记忆得分更高
                            # time_score = exp(-time_diff / time_decay_days)
                            import math
                            time_score = math.exp(-time_diff / time_decay_days)
                            time_score = max(0.0, min(1.0, time_score))  # 限制在0-1范围
                            
                        except Exception as time_error:
                            logger.debug(f"时间解析失败: {created_at_str} - {time_error}")
                            time_score = 0.5  # 默认中等时间得分
                    
                    # 3. 获取专家质量评分 (已在0-1范围)
                    quality_score = result.get('quality_score', 0.0) or 0.0
                    
                    # 4. 计算综合得分
                    composite_score = (
                        similarity_score * similarity_weight +
                        time_score * time_weight +
                        quality_score * quality_weight
                    )
                    
                    # 构造返回数据
                    memory_data = {
                        "memory_id": result.get('memory_id'),
                        "user_id": result.get('user_id'),
                        "agent_id": result.get('agent_id', ''),
                        "run_id": result.get('run_id', ''),
                        "application_id": result.get('application_id', ''),
                        "query": result.get('query', ''),
                        "response": result.get('response', ''),
                        "expert_verified": result.get('expert_verified', False),
                        "user_approved": result.get('user_approved', False),
                        "quality_score": quality_score,
                        "created_at": result.get('created_at'),
                        "metadata": result.get('metadata', {}),
                        
                        # 评分详情
                        "similarity_score": similarity_score,
                        "time_score": time_score,
                        "composite_score": composite_score,
                        "score_breakdown": {
                            "similarity": similarity_score,
                            "time_factor": time_score,
                            "quality": quality_score,
                            "weights": {
                                "similarity": similarity_weight,
                                "time": time_weight,
                                "quality": quality_weight
                            }
                        }
                    }
                    
                    # 优先使用专家纠正的回答
                    if result.get('metadata', {}).get('expert_corrected_response'):
                        memory_data["response"] = result['metadata']['expert_corrected_response']
                        memory_data["expert_corrected"] = True
                    else:
                        memory_data["expert_corrected"] = False
                    
                    scored_memories.append(memory_data)
                    
                except Exception as scoring_error:
                    logger.error(f"记忆评分计算失败: {scoring_error}")
                    continue
            
            # 按综合得分降序排序
            scored_memories.sort(key=lambda x: x['composite_score'], reverse=True)
            
            # 返回TopK结果
            top_memories = scored_memories[:limit]
            
            logger.info(f"智能记忆筛选完成: 候选数量={len(results)}, 有效数量={len(scored_memories)}, TopK={len(top_memories)}")

            return top_memories
            
        except Exception as e:
            logger.error(f"智能记忆筛选失败: {e}", exc_info=True)
            return []
    
    async def extract_user_profile(self, user_id: str) -> Optional[UserProfileMemory]:
        """
        从对话历史中提取用户画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户画像记忆对象
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 获取用户最近的对话历史
            conversations = await self.get_conversation_history(
                user_id=user_id,
                limit=100
            )
            
            if not conversations:
                logger.warning(f"用户 {user_id} 暂无对话历史")
                return None
            
            # 构建分析文本
            conversation_texts = []
            for conv in conversations:
                conversation_texts.append(f"用户: {conv.query}")
                conversation_texts.append(f"助手: {conv.response}")
            
            analysis_text = "\n".join(conversation_texts)
            
            # 使用LLM分析用户画像
            profile_prompt = f"""
            基于以下对话历史，分析用户的画像特征：
            
            {analysis_text}
            
            请从以下维度分析用户画像，并以JSON格式返回：
            1. 基本偏好 (preferences)
            2. 行为模式 (behavioral_patterns) 
            3. 关注领域 (interests)
            4. 沟通风格 (communication_style)
            5. 服务需求 (service_needs)
            
            返回格式：
            {{
                "preferences": {{}},
                "behavioral_patterns": {{}},
                "interests": [],
                "communication_style": "",
                "service_needs": []
            }}
            """
            
            # 调用LLM分析
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model="glm-4.5",
                temperature=0.1,
                api_key="6617719eb7df4c53a8693a7b670003c6.asoHZRafhFNhiA6o",
                base_url="https://open.bigmodel.cn/api/paas/v4/"
            )
            
            response = await llm.ainvoke(profile_prompt)
            profile_data = json.loads(response.content)
            
            # 创建用户画像记忆
            user_profile = UserProfileMemory(
                user_id=user_id,
                profile_data=profile_data,
                preferences=profile_data.get('preferences', {}),
                behavioral_patterns=profile_data.get('behavioral_patterns', {}),
                last_updated=datetime.now(),
                extraction_source=f"conversation_analysis_{len(conversations)}_records"
            )
            
            # 存储用户画像
            await self.profile_memory.add(
                messages=[{"role": "system", "content": f"用户 {user_id} 的画像信息"}],
                user_id=user_id,
                metadata={
                    "memory_type": MemoryType.USER_PROFILE.value,
                    "profile_data": user_profile.to_dict(),
                    "extracted_at": datetime.now().isoformat()
                },
                infer=False
            )
            
            logger.info(f"用户画像提取完成: {user_id}")
            return user_profile
            
        except Exception as e:
            logger.error(f"用户画像提取失败: {e}", exc_info=True)
            return None
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfileMemory]:
        """
        获取用户画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户画像记忆对象
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            results = await self.profile_memory.search(
                query=f"用户 {user_id} 的画像信息",
                user_id=user_id,
                limit=1
            )
            
            if results:
                metadata = results[0].get('metadata', {})
                profile_data = metadata.get('profile_data', {})
                if profile_data:
                    return UserProfileMemory.from_dict(profile_data)
            
            return None
            
        except Exception as e:
            logger.error(f"获取用户画像失败: {e}", exc_info=True)
            return None
    
# 全局记忆管理器实例
memory_manager = MemoryManager()
