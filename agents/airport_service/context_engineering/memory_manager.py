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
from enum import Enum
from datetime import datetime, timezone, timedelta
from mem0 import AsyncMemory
from mem0.configs.base import MemoryConfig
from mem0.vector_stores.configs import VectorStoreConfig
from mem0.llms.configs import LlmConfig
from mem0.embeddings.configs import EmbedderConfig
# 导入画像模型
from .profile.user_profile_models import SessionProfile, DailyProfile, InsightProfile
from agents.airport_service.core import structed_model, emb_model
from config.utils import config_manager
from common.logging import get_logger

logger = get_logger("memory_manager")

# 延迟导入画像提取器，避免循环依赖
def _get_profile_extractor():
    """延迟导入混合式画像提取器"""
    try:
        from .profile.profile_extractor import get_profile_extractor
        # 传入配置的 LLM 实例
        return get_profile_extractor(structed_model)
    except ImportError as e:
        logger.warning(f"混合式画像提取器导入失败: {e}")
        return None

class MemoryType(Enum):
    """记忆类型枚举"""
    CONVERSATION = "conversation"  # 对话记忆
    USER_SESSION_PROFILE = "user_session_profile"  # 用户会话画像记忆
    USER_DAILY_PROFILE = "user_daily_profile"  # 用户每日画像记忆
    USER_DEEP_PROFILE = "user_deep_profile"  # 用户深度画像记忆
    EXPERT_QA = "expert_qa"  # 专家QA记忆


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
            
            # 对话记忆配置
            conversation_config = MemoryConfig(
                llm=LlmConfig(provider="langchain", config={"model": structed_model}),
                vector_store=VectorStoreConfig(
                    provider="chroma",
                    config={
                        "collection_name": "conversation_memory",
                        "host": chroma_config.get("host", "192.168.0.105"),
                        "port": str(chroma_config.get("port", "8000"))
                    }
                ),
                embedder=EmbedderConfig(
                    provider="langchain",
                    config={"model": emb_model}
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
                        "collection_name": "profile_memory",
                        "host": chroma_config.get("host", "192.168.0.200"),
                        "port": str(chroma_config.get("port", "8000"))
                    }
                ),
                embedder=EmbedderConfig(
                    provider="langchain",
                    config={"model": emb_model}
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
                    "query_source": metadata.get('query_source', '小程序'),
                    "query_device": metadata.get('query_device', '手机'),
                    "query_ip": metadata.get('query_ip', ''),
                    "network_type": metadata.get('network_type', '5g'),
                    "retrieval_content": metadata.get('retrieval_content', ''),
                    "retrieval_source": metadata.get('retrieval_source', ''),
                    "retrieval_score": metadata.get('retrieval_score', 0.0),
                    "retrieval_images": metadata.get('retrieval_images', ''),
                    "retrieval_query_list": metadata.get('retrieval_query_list', []),
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
        expert_approved: Optional[bool] = True,
        expert_id: Optional[str] = None,
        quality_score: Optional[float] = None,
        corrected_response: Optional[str] = None  
    ) -> bool:
        """
        
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
    
    async def add_expert_qa(
        self,
        question: str,
        answer: str,
        expert_id: Optional[str] = None,
        application_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加全新的专家QA对
        
        Args:
            question: 问题内容
            answer: 答案内容
            expert_id: 专家ID (可选)
            application_id: 应用名称 (可选)
            metadata: 额外元数据 (可选)
            
        Returns:
            memory_id: 记忆ID
        """
        if not self._initialized:
            await self.initialize()
        
        base_metadata = deepcopy(metadata) if metadata else {}
        
        try:
            expert_qa_metadata = {
                "agent_memory_type": MemoryType.EXPERT_QA.value,
                "application_id": application_id or "",
                "expert_id": expert_id or "",
                "question": question,
                "answer": answer
            }
            
            # 构造消息内容用于向量化存储
            messages = [
                {"role": "user", "content": question},
            ]
            
            result = await self.conversation_memory.add(
                messages=messages,
                user_id="expert_system",  # 使用特殊的用户ID标识专家系统
                metadata={**base_metadata, **expert_qa_metadata},
                infer=False
            )
            
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"专家QA已添加: {memory_id}, 专家ID: {expert_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"添加专家QA失败: {e}", exc_info=True)
            raise
    
    async def get_expert_qa_list(
        self,
        application_id: Optional[str] = None,
        expert_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        查询专家QA列表
        
        Args:
            application_id: 应用名称筛选 (可选)
            expert_id: 专家ID筛选 (可选)
            limit: 返回数量限制
            
        Returns:
            专家QA列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建过滤条件
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.EXPERT_QA.value}})
            
            # 可选条件
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if expert_id:
                filter_conditions.append({"expert_id": {"$eq": expert_id}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            result = await self.conversation_memory.get_all(
                filters=filters,
                limit=limit
            )
            
            # 处理返回结果
            if isinstance(result, dict) and 'results' in result:
                results = result['results']
                import inspect
                if inspect.iscoroutine(results):
                    results = await results
            else:
                logger.warning(f"意外的返回格式: {type(result)}")
                results = []
            
            expert_qa_list = []
            for result_item in results:
                metadata = result_item.get('metadata', {})
                
                qa_data = {
                    "memory_id": result_item.get('id'),
                    "expert_id": metadata.get('expert_id', ''),
                    "application_id": metadata.get('application_id', ''),
                    "question": metadata.get('question', ''),
                    "answer": metadata.get('answer', ''),
                    "tags": metadata.get('tags', ''),
                    "images": metadata.get('images', ''),
                    "services": metadata.get('services', ''),
                    "created_at": result_item.get('created_at'),
                    "updated_at": result_item.get('updated_at'),
                }
                expert_qa_list.append(qa_data)
            
            logger.info(f"专家QA查询完成: 条件={filters}, 结果数量={len(expert_qa_list)}")
            return expert_qa_list
            
        except Exception as e:
            logger.error(f"查询专家QA失败: {e}", exc_info=True)
            return []
    
    async def update_expert_qa(
        self,
        memory_id: str,
        question: Optional[str] = None,
        answer: Optional[str] = None,
        expert_id: Optional[str] = None,
        tags: Optional[str] = None,
        images: Optional[str] = None,
        services: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        修改专家QA
        
        Args:
            memory_id: 记忆ID
            question: 新的问题内容 (可选)
            answer: 新的答案内容 (可选)
            expert_id: 新的专家ID (可选)
            tags: 新的标签 (可选)
            images: 新的图片信息 (可选)
            services: 新的服务信息 (可选)
            metadata: 额外元数据 (可选)
            
        Returns:
            是否成功更新
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建更新的元数据
            updated_metadata = {}
            if expert_id is not None:
                updated_metadata["expert_id"] = expert_id
            if question is not None:
                updated_metadata["question"] = question
            if answer is not None:
                updated_metadata["answer"] = answer
            if tags is not None:
                updated_metadata["tags"] = tags
            if images is not None:
                updated_metadata["images"] = images
            if services is not None:
                updated_metadata["services"] = services
            
            # 如果有额外的元数据，合并进去
            if metadata:
                updated_metadata.update(metadata)
            
            # 如果问题内容有更新，需要更新记忆的主要内容
            updated_content = question if question is not None else ""
            
            await self.conversation_memory.update(
                memory_id=memory_id,
                data=updated_content,
                metadata=updated_metadata
            )
            
            logger.info(f"专家QA更新完成: memory_id={memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新专家QA失败: {e}", exc_info=True)
            return False
    
    async def delete_expert_qa(
        self,
        memory_id: str
    ) -> bool:
        """
        删除专家QA
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否成功删除
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 使用mem0的delete方法删除记忆
            await self.conversation_memory.delete(memory_id=memory_id)
            
            logger.info(f"专家QA删除完成: memory_id={memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除专家QA失败: {e}", exc_info=True)
            return False
    
    async def batch_delete_expert_qa(
        self,
        memory_ids: List[str]
    ) -> Dict[str, Any]:
        """
        批量删除专家QA
        
        Args:
            memory_ids: 记忆ID列表
            
        Returns:
            批量删除结果统计
        """
        if not self._initialized:
            await self.initialize()
        
        success_count = 0
        failed_count = 0
        failed_ids = []
        
        try:
            for memory_id in memory_ids:
                try:
                    success = await self.delete_expert_qa(memory_id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        failed_ids.append(memory_id)
                except Exception as single_error:
                    logger.error(f"单个删除失败: {memory_id} - {single_error}")
                    failed_count += 1
                    failed_ids.append(memory_id)
            
            result = {
                "total_items": len(memory_ids),
                "delete_success": success_count,
                "delete_failed": failed_count,
                "failed_ids": failed_ids,
                "timestamp": datetime.now().isoformat(),
            }
            
            logger.info(f"批量删除专家QA完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"批量删除专家QA失败: {e}", exc_info=True)
            return {
                "total_items": len(memory_ids),
                "delete_success": success_count,
                "delete_failed": failed_count,
                "failed_ids": failed_ids,
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
                    "expert_id": metadata.get('expert_id', ''),
                    "expert_corrected_response": metadata.get('expert_corrected_response', ''),
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

    async def search_expert_qa(
        self,
        query: str,
        application_id: Optional[str] = None,
        expert_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        检索专家QA对
        
        Args:
            query: 查询文本
            application_id: 应用名称筛选 (可选)
            expert_id: 专家ID筛选 (可选)
            tags: 标签筛选 (可选)
            services: 服务筛选 (可选)
            limit: 返回数量限制
            
        Returns:
            相似专家QA记录列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.EXPERT_QA.value}})
            
            # 可选条件
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if expert_id:
                filter_conditions.append({"expert_id": {"$eq": expert_id}})
            if tags:
                # 对于包含多个标签的情况，检查是否存在任意一个标签
                filter_conditions.append({"tags": {"$in": tags}})
            if services:
                # 对于包含多个服务的情况，检查是否存在任意一个服务
                filter_conditions.append({"services": {"$in": services}})
            
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
            
            expert_qa_list = []
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
                
                # 构造返回数据
                expert_qa_data = {
                    "memory_id": result.get('id'),
                    "user_id": result.get('user_id'),
                    "expert_id": metadata.get('expert_id', ''),
                    "application_id": metadata.get('application_id', ''),
                    "question": metadata.get('question', ''),
                    "answer": metadata.get('answer', ''),
                    "tags": metadata.get('tags', ''),
                    "images": metadata.get('images', ''),
                    "services": metadata.get('services', ''),
                    "relevance_score": result.get('score', 0.0),
                    "created_at": result.get('created_at'),
                    "updated_at": result.get('updated_at'),
                    "metadata": metadata
                }
                expert_qa_list.append(expert_qa_data)
                
                # 达到目标数量就停止
                if len(expert_qa_list) >= limit:
                    break
            
            return expert_qa_list
            
        except Exception as e:
            logger.error(f"专家QA相似度搜索失败: {e}", exc_info=True)
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
                                
                if user_query and assistant_response:
                    examples.append({
                        "user": user_query,
                        "assistant": assistant_response,
                        "quality_score": result.get('quality_score', 0),
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
            candidate_limit = min(limit * 5, 100)
            
            # 搜索专家审核通过的对话
            results = await self.search_conversations(
                query=query,
                application_id=application_id,
                user_id=user_id,
                agent_id=agent_id,
                expert_verified=True,
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
                        "expert_id": result.get('expert_id', ''),
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
     
    # ============================== 画像提取相关方法 ==============================
    async def trigger_session_profile_extraction(
        self,
        user_id: str,
        run_id: str,
        application_id: Optional[str] = None

    ) -> Optional[Dict[str, Any]]:
        """
        触发会话画像提取（第一步）
        
        Args:
            user_id: 用户ID  
            run_id: 会话ID
            application_id: 应用ID
            
        Returns:
            画像提取结果
        """
        if not self._initialized:
            await self.initialize()
        try:
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("画像提取器不可用")
                return None
            conversation_history = await self.get_conversation_history(
                application_id=application_id,
                user_id=user_id,
                run_id=run_id,
                limit=1000
            )
            if not conversation_history:
                logger.warning(f"未找到会话数据: {application_id}:{user_id}:{run_id}")
                return None           
            session_profile = await extractor.extract_session_profile(conversation_history=conversation_history)
            # 存储会话画像到记忆系统
            await self.store_session_profile(
                user_id=user_id,
                application_id=application_id,
                run_id=run_id,
                session_profile=session_profile
            )
            
            logger.info(f"会话画像提取完成: {user_id}:{run_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "application_id": application_id,
                "run_id": run_id,
                "profile": session_profile.model_dump(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"会话画像提取失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "application_id": application_id,
                "user_id": user_id,
                "run_id": run_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def trigger_daily_profile_aggregation(
        self,
        application_id: str,
        user_id: str,
        date: str
    ) -> Optional[Dict[str, Any]]:
        """
        触发每日画像聚合（第二步）
        
        Args:
            user_id: 用户ID
            application_id: 应用ID
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            聚合结果
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 获取画像提取器
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("画像提取器不可用")
                return None
            
            # 获取当日所有会话画像
            session_profiles= await self.get_session_profiles(
            user_id=user_id,
            application_id=application_id,
            day=date
            )
            
            if len(session_profiles)<1:
                logger.warning(f"未找到当日会话画像: {user_id}:{date}")
                return None
            
            # 聚合每日画像
            daily_profile = await extractor.extract_daily_profile(
                session_profiles=[p.get("profile") for p in session_profiles]
            )
            
            # 存储每日画像
            await self.store_daily_profile(
                user_id=user_id,
                application_id=application_id,
                date=date,
                daily_profile=daily_profile
            )
            
            logger.info(f"每日画像聚合完成: {user_id}:{date}")
            
            return {
                "success": True,
                "user_id": user_id,
                "application_id": application_id,
                "date": date,
                "profile": daily_profile.model_dump(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"每日画像聚合失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "user_id": user_id,
                "application_id": application_id,
                "date": date,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def trigger_deep_insight_analysis(
        self,
        user_id: str,
        application_id: Optional[str] = None,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        触发深度洞察分析（第三步）
        Args:
            user_id: 用户ID
            application_id: 应用名称
            days: 分析天数
            
        Returns:
            分析结果
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 获取画像提取器
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("画像提取器不可用")
                return None
            
            # 获取长期每日画像
            daily_profiles = await self.get_period_daily_profiles(user_id, application_id, days)
            
            if len(daily_profiles) < 7:  # 至少需要一周数据
                logger.warning(f"数据不足进行深度分析: {user_id}, 仅有{len(daily_profiles)}天数据")
                return None
            
            # 深度洞察分析
            analysis_period = f"{days}天"
            deep_profile = await extractor.extract_insight_profile(
                user_id=user_id,
                daily_profiles=daily_profiles,
                analysis_period=analysis_period
            )
            
            # 存储深度画像
            await self.store_deep_profile(
                user_id=user_id,
                application_id=application_id,
                analysis_period=analysis_period,
                deep_profile=deep_profile
            )
            
            logger.info(f"深度洞察分析完成: {user_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "profile": deep_profile.model_dump(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"深度洞察分析失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # ============================== 画像存储和查询辅助方法 ==============================
    
    async def store_session_profile(
        self,
        user_id: str,
        application_id: Optional[str] = None,
        run_id: Optional[str] = None,
        session_profile: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        存储会话画像
        
        Args:
            user_id: 用户ID
            application_id: 应用名称
            run_id: 会话ID
            session_profile: 会话画像数据
            metadata: 额外元数据
            
        Returns:
            memory_id: 记忆ID
        """
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}
        
        try:
            profile_metadata = {
                    "agent_memory_type": MemoryType.USER_SESSION_PROFILE.value,
                    "application_id": application_id,
                    "start_time": session_profile.session_metrics.start_time,
                    "end_time": session_profile.session_metrics.end_time,
                    "day": session_profile.session_metrics.day,
                    "duration_seconds": session_profile.session_metrics.duration_seconds,
                    "turn_count": session_profile.session_metrics.turn_count,
                    "user_messages_count": session_profile.session_metrics.user_messages_count,
                    "system_responses_count": session_profile.session_metrics.system_responses_count,
                    "avg_response_time": session_profile.session_metrics.avg_response_time,
                    "source": session_profile.technical_context.source,
                    "device": session_profile.technical_context.device,
                    "ip": session_profile.technical_context.ip,
                    "country": session_profile.technical_context.country,
                    "province": session_profile.technical_context.province,
                    "city": session_profile.technical_context.city,
                    "longitude": session_profile.technical_context.longitude,
                    "latitude": session_profile.technical_context.latitude,
                    "network_type": session_profile.technical_context.network_type,

                    "language": session_profile.content_analysis.language,
                    "style": session_profile.content_analysis.style,
                    "sentiment": session_profile.content_analysis.sentiment,
                    "anxiety_score": session_profile.content_analysis.anxiety_score,
                    "urgency_score": session_profile.content_analysis.urgency_score,
                    "satisfaction_score": session_profile.content_analysis.satisfaction_score,
                    "keywords": json.dumps(session_profile.content_analysis.keywords,ensure_ascii=False),
                    "topics": json.dumps(session_profile.content_analysis.topics,ensure_ascii=False),
                    "resolution_status": session_profile.content_analysis.resolution_status,
                    "flights": json.dumps(session_profile.service_interaction.queried_flights,ensure_ascii=False),
                    "services": json.dumps(session_profile.service_interaction.service_usage,ensure_ascii=False),

                    "confidence": session_profile.inferred_user_attribute.confidence,
                    "traveler_type": session_profile.inferred_user_attribute.traveler_type,
                    "role": session_profile.inferred_user_attribute.role,
                    "profile": json.dumps(session_profile.model_dump(),ensure_ascii=False)


            }
            
            messages = [{"role": "system", "content": f"用户 {user_id} 会话 {run_id} 的行为画像"}]
            
            result = await self.profile_memory.add(
                messages=messages,
                user_id=user_id,
                run_id=run_id,
                metadata={**base_metadata, **profile_metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"会话画像已存储: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"存储会话画像失败: {e}", exc_info=True)
            raise
    
    async def get_session_profiles(
        self,
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        run_id: Optional[str] = None,
        day: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        turn_count: Optional[int] = None,
        user_messages_count: Optional[int] = None,
        system_responses_count: Optional[int] = None,
        avg_response_time: Optional[float] = None,
        source: Optional[str] = None,
        device: Optional[str] = None,
        country: Optional[str] = None,
        province: Optional[str] = None,
        city: Optional[str] = None,
        network_type: Optional[str] = None,
        language: Optional[str] = None,
        style: Optional[str] = None,
        sentiment: Optional[str] = None,
        anxiety_score: Optional[float] = None,
        urgency_score: Optional[float] = None,
        satisfaction_score: Optional[float] = None,
        keywords: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        resolution_status: Optional[str] = None,
        flights: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        traveler_type: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 50,
    ) -> List[SessionProfile]:

        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建过滤条件列表 - 按照用户提供的案例格式
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.USER_SESSION_PROFILE.value}})
            
            # 可选条件
            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if run_id:
                filter_conditions.append({"run_id": {"$eq": run_id}})
            if day:
                filter_conditions.append({"day": {"$eq": day}})
            if duration_seconds:
                filter_conditions.append({"duration_seconds": {"$gte": duration_seconds}})
            if turn_count:
                filter_conditions.append({"turn_count": {"$gte": turn_count}})
            if user_messages_count:
                filter_conditions.append({"user_messages_count": {"$gte": user_messages_count}})
            if system_responses_count:
                filter_conditions.append({"system_responses_count": {"$gte": system_responses_count}})
            if avg_response_time:
                filter_conditions.append({"avg_response_time": {"$gte": avg_response_time}})
            if source:
                filter_conditions.append({"source": {"$eq": source}})
            if device:
                filter_conditions.append({"device": {"$eq": device}})
            if country:
                filter_conditions.append({"country": {"$eq": country}})
            if province:
                filter_conditions.append({"province": {"$eq": province}})
            if city:
                filter_conditions.append({"city": {"$eq": city}})
            if network_type:
                filter_conditions.append({"network_type": {"$eq": network_type}})
            if language:
                filter_conditions.append({"language": {"$eq": language}})
            if style:
                filter_conditions.append({"style": {"$eq": style}})
            if sentiment:
                filter_conditions.append({"sentiment": {"$eq": sentiment}})
            if anxiety_score:
                filter_conditions.append({"anxiety_score": {"$gte": anxiety_score}})
            if urgency_score:
                filter_conditions.append({"urgency_score": {"$gte": urgency_score}})
            if satisfaction_score:
                filter_conditions.append({"satisfaction_score": {"$gte": satisfaction_score}})
            if keywords:
                filter_conditions.append({"keywords": {"$in": keywords}})
            if topics:
                filter_conditions.append({"topics": {"$in": topics}})
            if resolution_status:
                filter_conditions.append({"resolution_status": {"$eq": resolution_status}})
            if flights:
                filter_conditions.append({"flights": {"$in": flights}})
            if services:
                filter_conditions.append({"services": {"$in": services}})
            if confidence:
                filter_conditions.append({"confidence": {"$gte": confidence}})

            if traveler_type:
                filter_conditions.append({"traveler_type": {"$eq": traveler_type}})
            if role:
                filter_conditions.append({"role": {"$eq": role}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            result = await self.profile_memory.get_all(filters=filters, limit=limit)
            
            if isinstance(result, dict) and 'results' in result:
                all_memories = result['results']
                # 如果返回的是协程，按照案例进行await
                import inspect
                if inspect.iscoroutine(all_memories):
                    all_memories = await all_memories
            else:
                logger.warning(f"意外的get_all返回格式: {type(result)}")
                all_memories = []
            
            session_profiles = []
            tmp_memory = {}
            for memory in all_memories:
                tmp_memory.clear()
                metadata = memory.get('metadata', {})
                profile = metadata.get('profile', '')
                if profile:
                    try:
                        tmp_memory["memory_id"] = memory.get('id')
                        tmp_memory["user_id"] = memory.get('user_id')
                        tmp_memory["application_id"] = metadata.get('application_id', '')
                        tmp_memory["run_id"] = memory.get('run_id', '')
                        tmp_memory["profile"] = SessionProfile(**json.loads(profile))
                        session_profiles.append(tmp_memory.copy())
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析profile JSON失败: {e}, 跳过此记录")
                        continue
                    except Exception as e:
                        logger.warning(f"重构SessionProfile失败: {e}, 跳过此记录")
                        continue
            
            logger.info(f"获取到 {len(session_profiles)} 条会话画像记录")
            return session_profiles
            
        except Exception as e:
            logger.error(f"获取会话画像历史失败: {e}", exc_info=True)
            return []
    
    async def store_daily_profile(
        self,
        user_id: str,
        application_id: str,
        date: str,
        daily_profile: DailyProfile,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        存储每日画像
        
        Args:
            user_id: 用户ID
            application_id: 应用名称
            date: 日期 (YYYY-MM-DD)
            daily_profile: 每日画像数据
            metadata: 额外元数据
            
        Returns:
            memory_id: 记忆ID
        """
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}
        
        try:
            profile_metadata = {
                "agent_memory_type": MemoryType.USER_DAILY_PROFILE.value,
                "application_id": application_id,
                "date": date,
                
                # 交互指标
                "total_sessions": daily_profile.interaction_metrics.total_sessions,
                "total_turns": daily_profile.interaction_metrics.total_turns,
                "avg_session_duration": daily_profile.interaction_metrics.avg_session_duration,
                "avg_session_depth": daily_profile.interaction_metrics.avg_session_depth,
                "peak_hours": json.dumps(daily_profile.interaction_metrics.peak_hours, ensure_ascii=False),
                "device_distribution": json.dumps(daily_profile.interaction_metrics.device_distribution, ensure_ascii=False),
                "source_distribution": json.dumps(daily_profile.interaction_metrics.source_distribution, ensure_ascii=False),
                "country_distribution": json.dumps(daily_profile.interaction_metrics.country_distribution, ensure_ascii=False),
                "province_distribution": json.dumps(daily_profile.interaction_metrics.province_distribution, ensure_ascii=False),
                "city_distribution": json.dumps(daily_profile.interaction_metrics.city_distribution, ensure_ascii=False),
                
                # 行为模式
                "dominant_language": daily_profile.behavior_pattern.dominant_language,
                "common_query_styles": json.dumps([style.value for style in daily_profile.behavior_pattern.common_query_styles], ensure_ascii=False),
                "avg_sentiment_score": daily_profile.behavior_pattern.avg_sentiment_score,
                "avg_anxiety_score": daily_profile.behavior_pattern.avg_anxiety_score,
                "avg_urgency_score": daily_profile.behavior_pattern.avg_urgency_score,
                "top_concerns": json.dumps(daily_profile.behavior_pattern.top_concerns, ensure_ascii=False),
                "frequent_keywords": json.dumps(daily_profile.behavior_pattern.frequent_keywords, ensure_ascii=False),
                "topic_trends": json.dumps(daily_profile.behavior_pattern.topic_trends, ensure_ascii=False),
                "resolution_rate": daily_profile.behavior_pattern.resolution_rate,
                "satisfaction_rate": daily_profile.behavior_pattern.satisfaction_rate,
                "follow_up_rate": daily_profile.behavior_pattern.follow_up_rate, 
                # 服务使用
                "flights_queried": json.dumps(daily_profile.service_usage.flights_queried, ensure_ascii=False),
                "services_used": json.dumps(daily_profile.service_usage.services_used, ensure_ascii=False),
                # 行为稳定性
                "behavior_stability": daily_profile.behavior_stability,
                # 完整画像数据
                "profile": json.dumps(daily_profile.model_dump(), ensure_ascii=False)
            }
            
            messages = [{"role": "system", "content": f"用户 {user_id} 在 {date} 的每日行为画像"}]
            
            result = await self.profile_memory.add(
                messages=messages,
                user_id=user_id,
                metadata={**base_metadata, **profile_metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"每日画像已存储: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"存储每日画像失败: {e}", exc_info=True)
            raise

    async def get_daily_profiles(
        self,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        date: Optional[str] = None,
        total_sessions: Optional[int] = None,
        total_turns: Optional[int] = None,
        avg_session_duration: Optional[float] = None,
        avg_session_depth: Optional[float] = None,
        dominant_language: Optional[str] = None,
        avg_sentiment_score: Optional[float] = None,
        avg_anxiety_score: Optional[float] = None,
        avg_urgency_score: Optional[float] = None,
        resolution_rate: Optional[float] = None,
        satisfaction_rate: Optional[float] = None,
        follow_up_rate: Optional[float] = None,
        behavior_stability: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Args:
            user_id: 用户ID (可选)
            application_id: 应用名称 (可选)
            date: 日期 (可选)
            total_sessions: 总会话次数筛选 (可选)
            total_turns: 总交互轮次筛选 (可选)
            avg_session_duration: 平均会话时长筛选 (可选)
            avg_session_depth: 平均会话深度筛选 (可选)
            dominant_language: 主要使用语言筛选 (可选)
            avg_sentiment_score: 平均情感分数筛选 (可选)
            avg_anxiety_score: 平均焦虑指数筛选 (可选)
            avg_urgency_score: 平均紧急度筛选 (可选)
            resolution_rate: 问题解决率筛选 (可选)
            satisfaction_rate: 满意度筛选 (可选)
            follow_up_rate: 需要跟进比例筛选 (可选)
            behavior_stability: 行为稳定性指数筛选 (可选)
            limit: 返回数量限制
            
        Returns:
            每日画像记录列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建过滤条件列表 - 按照用户提供的案例格式
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.USER_DAILY_PROFILE.value}})
            
            # 可选条件
            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if date:
                filter_conditions.append({"date": {"$eq": date}})
            if total_sessions:
                filter_conditions.append({"total_sessions": {"$gte": total_sessions}})
            if total_turns:
                filter_conditions.append({"total_turns": {"$gte": total_turns}})
            if avg_session_duration:
                filter_conditions.append({"avg_session_duration": {"$gte": avg_session_duration}})
            if avg_session_depth:
                filter_conditions.append({"avg_session_depth": {"$gte": avg_session_depth}})
            if dominant_language:
                filter_conditions.append({"dominant_language": {"$eq": dominant_language}})
            if avg_sentiment_score:
                filter_conditions.append({"avg_sentiment_score": {"$gte": avg_sentiment_score}})
            if avg_anxiety_score:
                filter_conditions.append({"avg_anxiety_score": {"$gte": avg_anxiety_score}})
            if avg_urgency_score:
                filter_conditions.append({"avg_urgency_score": {"$gte": avg_urgency_score}})
            if resolution_rate:
                filter_conditions.append({"resolution_rate": {"$gte": resolution_rate}})
            if satisfaction_rate:
                filter_conditions.append({"satisfaction_rate": {"$gte": satisfaction_rate}})
            if follow_up_rate:
                filter_conditions.append({"follow_up_rate": {"$gte": follow_up_rate}})
            if behavior_stability:
                filter_conditions.append({"behavior_stability": {"$gte": behavior_stability}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            # 使用 get_all 进行查询
            result = await self.profile_memory.get_all(filters=filters, limit=limit)
            
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
            profiles = []
            tmp_memory = {}
            for memory in all_memories:
                tmp_memory.clear()
                metadata = memory.get('metadata', {})
                if metadata.get('profile'):
                    tmp_memory["memory_id"] = memory.get('id')
                    tmp_memory["user_id"] = memory.get('user_id')
                    tmp_memory["application_id"] = metadata.get('application_id', '')
                    tmp_memory["date"] = metadata.get('date', '')
                    tmp_memory["profile"] = DailyProfile(**json.loads(metadata.get('profile')))
                    profiles.append(tmp_memory.copy())                    

            logger.info(f"每日画像历史查询完成: 过滤条件={filters}, 获取={len(all_memories)}, 返回=1")
            return profiles
        except Exception as e:
            logger.error(f"获取每日画像历史失败: {e}", exc_info=True)
            return []
    
    async def get_deep_profiles(
        self,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        analysis_period: Optional[str] = None,
        primary_traveler_type: Optional[str] = None,
        travel_frequency: Optional[str] = None,
        customer_value_score: Optional[float] = None,
        retention_risk: Optional[float] = None,
        upsell_potential: Optional[float] = None,
        communication_strategy: Optional[str] = None,
        personalization_level: Optional[str] = None,
        profile_confidence: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取深度画像历史
        
        Args:
            user_id: 用户ID (可选)
            application_id: 应用名称 (可选)
            analysis_period: 分析周期筛选 (可选)
            primary_traveler_type: 主要旅客类型筛选 (可选)
            travel_frequency: 出行频率筛选 (可选)
            customer_value_score: 客户价值分数筛选 (可选)
            retention_risk: 流失风险筛选 (可选)
            upsell_potential: 增值服务潜力筛选 (可选)
            communication_strategy: 沟通策略筛选 (可选)
            personalization_level: 个性化程度筛选 (可选)
            profile_confidence: 画像置信度筛选 (可选)
            limit: 返回数量限制
            
        Returns:
            深度画像记录列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 构建过滤条件列表 - 按照用户提供的案例格式
            filter_conditions = []
            
            # 基础条件：记忆类型
            filter_conditions.append({"agent_memory_type": {"$eq": MemoryType.USER_DEEP_PROFILE.value}})
            
            # 可选条件
            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if analysis_period:
                filter_conditions.append({"analysis_period": {"$eq": analysis_period}})
            if primary_traveler_type:
                filter_conditions.append({"primary_traveler_type": {"$eq": primary_traveler_type}})
            if travel_frequency:
                filter_conditions.append({"travel_frequency": {"$eq": travel_frequency}})
            if customer_value_score:
                filter_conditions.append({"customer_value_score": {"$gte": customer_value_score}})
            if retention_risk:
                filter_conditions.append({"retention_risk": {"$gte": retention_risk}})
            if upsell_potential:
                filter_conditions.append({"upsell_potential": {"$gte": upsell_potential}})
            if communication_strategy:
                filter_conditions.append({"communication_strategy": {"$eq": communication_strategy}})
            if personalization_level:
                filter_conditions.append({"personalization_level": {"$eq": personalization_level}})
            if profile_confidence:
                filter_conditions.append({"profile_confidence": {"$gte": profile_confidence}})
            
            # 构建最终过滤器
            if len(filter_conditions) == 1:
                filters = filter_conditions[0]
            else:
                filters = {"$and": filter_conditions}
            
            # 使用 get_all 进行查询
            result = await self.profile_memory.get_all(filters=filters, limit=limit)
            
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
            
            profiles = []
            tmp_memory = {}
            for memory in all_memories:
                tmp_memory.clear()
                metadata = memory.get('metadata', {})
                if metadata.get('profile'):
                    tmp_memory["memory_id"] = memory.get('id')
                    tmp_memory["user_id"] = memory.get('user_id')
                    tmp_memory["application_id"] = metadata.get('application_id', '')
                    tmp_memory["analysis_period"] = metadata.get('analysis_period', '')
                    tmp_memory["profile"] = InsightProfile(**json.loads(metadata.get('profile')))
                    profiles.append(tmp_memory.copy())
            
            logger.info(f"深度画像历史查询完成: 过滤条件={filters}, 获取={len(all_memories)}, 返回={len(profiles)}")
            return profiles
            
        except Exception as e:
            logger.error(f"获取深度画像历史失败: {e}", exc_info=True)
            return []
    
    async def store_deep_profile(
        self,
        user_id: str,
        application_id: str,
        analysis_period: str,
        deep_profile: InsightProfile,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        存储深度画像
        
        Args:
            user_id: 用户ID
            application_id: 应用名称
            analysis_period: 分析周期 (如"30天")
            deep_profile: 深度画像数据
            metadata: 额外元数据
            
        Returns:
            memory_id: 记忆ID
        """
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}
        
        try:
            profile_metadata = {
                "agent_memory_type": MemoryType.USER_DEEP_PROFILE.value,
                "application_id": application_id,
                "analysis_period": analysis_period,
                "primary_traveler_type": deep_profile.primary_traveler_type.value,
                "preferred_contact_hours": json.dumps(deep_profile.behavior_pattern.preferred_contact_hours, ensure_ascii=False),
                "preferred_airlines": json.dumps(deep_profile.travel_pattern.preferred_airlines, ensure_ascii=False),
                "travel_frequency": deep_profile.travel_pattern.travel_frequency,
                "preferred_services": json.dumps(deep_profile.service_preference.preferred_services, ensure_ascii=False),
                "customer_value_score": deep_profile.customer_value_score,
                "retention_risk": deep_profile.retention_risk,
                "upsell_potential": deep_profile.upsell_potential,
                "recommended_services": json.dumps(deep_profile.recommended_services, ensure_ascii=False),
                "communication_strategy": deep_profile.communication_strategy,
                "personalization_level": deep_profile.personalization_level,
                "profile_confidence": deep_profile.profile_confidence,
                "profile": json.dumps(deep_profile.model_dump(), ensure_ascii=False)
            }
            
            messages = [{"role": "system", "content": f"用户 {user_id} 的深度洞察画像，分析周期: {analysis_period}"}]
            
            result = await self.profile_memory.add(
                messages=messages,
                user_id=user_id,
                metadata={**base_metadata, **profile_metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"深度画像已存储: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"存储深度画像失败: {e}", exc_info=True)
            raise
        
    async def get_period_daily_profiles(self, user_id: str, application_id: str, days: int) -> List[DailyProfile]:
        """获取指定时期的每日画像"""
        try:
            # 计算日期范围
            daily_profiles = []
            end_date = datetime.now(timezone.utc)
            for i in range(days):
                date = end_date - timedelta(days=i)
                daily_profile = await self.get_daily_profiles(
                    user_id=user_id,
                    application_id=application_id,
                    date=date.strftime("%Y-%m-%d")
                )
                if daily_profile:
                    daily_profiles.append(daily_profile[0].get("profile"))

            logger.info(f"获取到用户 {user_id} 最近 {days} 天的 {len(daily_profiles)} 个每日画像")
            return daily_profiles
            
        except Exception as e:
            logger.error(f"获取时期每日画像失败: {e}", exc_info=True)
            return []
    
    def _reconstruct_profile_object(self, profile_data: Dict[str, Any], profile_type: str):
        """
        根据画像类型重构画像对象
        
        Args:
            profile_data: 画像数据字典
            profile_type: 画像类型 (session/daily/deep)
            
        Returns:
            重构的画像对象，如果失败返回None
        """
        try:
            if profile_type == "session":
                return SessionProfile(**profile_data)
            elif profile_type == "daily":
                return DailyProfile(**profile_data)
            elif profile_type == "deep" or profile_type == "deep_insight":
                return InsightProfile(**profile_data)
            else:
                logger.warning(f"未知的画像类型: {profile_type}")
                return None
        except Exception as e:
            logger.warning(f"重构{profile_type}画像失败: {e}")
            return None
    
    def reconstruct_session_profiles_from_records(self, records: List[Dict[str, Any]]) -> List[SessionProfile]:
        """
        从查询记录中重构SessionProfile对象列表
        
        Args:
            records: 查询结果记录列表
            
        Returns:
            SessionProfile对象列表
        """
        session_profiles = []
        for record in records:
            profile_data = record.get('profile_data', {})
            if profile_data:
                session_profile = self._reconstruct_profile_object(profile_data, "session")
                if session_profile:
                    session_profiles.append(session_profile)
        
        logger.info(f"成功重构了 {len(session_profiles)} 个SessionProfile对象")
        return session_profiles
    
    def reconstruct_daily_profiles_from_records(self, records: List[Dict[str, Any]]) -> List[DailyProfile]:
        """
        从查询记录中重构DailyProfile对象列表
        
        Args:
            records: 查询结果记录列表
            
        Returns:
            DailyProfile对象列表
        """
        daily_profiles = []
        for record in records:
            profile_data = record.get('profile_data', {})
            if profile_data:
                daily_profile = self._reconstruct_profile_object(profile_data, "daily")
                if daily_profile:
                    daily_profiles.append(daily_profile)
        
        logger.info(f"成功重构了 {len(daily_profiles)} 个DailyProfile对象")
        return daily_profiles
    
    def reconstruct_insight_profiles_from_records(self, records: List[Dict[str, Any]]) -> List[InsightProfile]:
        """
        从查询记录中重构InsightProfile对象列表
        
        Args:
            records: 查询结果记录列表
            
        Returns:
            InsightProfile对象列表
        """
        insight_profiles = []
        for record in records:
            profile_data = record.get('profile_data', {})
            if profile_data:
                insight_profile = self._reconstruct_profile_object(profile_data, "deep_insight")
                if insight_profile:
                    insight_profiles.append(insight_profile)
        
        logger.info(f"成功重构了 {len(insight_profiles)} 个InsightProfile对象")
        return insight_profiles
    
# 全局记忆管理器实例
memory_manager = MemoryManager()
