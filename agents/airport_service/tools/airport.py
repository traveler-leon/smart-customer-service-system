import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
import asyncio
from text2kb.retrieval import retrieve_from_kb
from langchain_core.messages import AnyMessage
from typing import List
from config.utils import config_manager
from agents.airport_service.core import comprehensive_query_transform,rerank_results
from agents.airport_service.context_engineering.agent_memory import get_relevant_expert_qa_memories
from agents.airport_service.state import RetrievalResult
from common.logging import get_logger
logger = get_logger("agents.tools.airport")

_text2kb_config = config_manager.get_text2kb_config()
KB_ADDRESS = _text2kb_config.get("kb_address")
KB_API_KEY = _text2kb_config.get("kb_api_key")
KB_DATASET_NAME = _text2kb_config.get("kb_dataset_name")
KB_VECTOR_SIMILARITY_WEIGHT = float(_text2kb_config.get("kb_vector_similarity_weight"))
KB_TOP_K = int(_text2kb_config.get("kb_topK"))
KB_KEY_WORDS = bool(_text2kb_config.get("kb_key_words"))
RERANKER_MODEL = _text2kb_config.get("reranker_model")
RERANKER_ADDRESS = _text2kb_config.get("reranker_address")
RERANKER_API_KEY = _text2kb_config.get("reranker_api_key")



async def airport_knowledge_query2docs_main(user_question:str,messages:List[AnyMessage]) -> RetrievalResult:
    """
    统一的知识检索入口，返回标准化的检索结果
    
    Args:
        user_question: 用户问题
        messages: 历史消息列表
        
    Returns:
        RetrievalResult: 统一的检索结果对象
    """
    user_query = user_question
    
    # 第一步：先完成问题重写（知识库检索依赖这个）
    rewritten_query_task = comprehensive_query_transform(user_query,'rewrite',messages)
    step_back_query_task = comprehensive_query_transform(user_query,'step_back',messages)
    rewritten_query, step_back_query = await asyncio.gather(
        rewritten_query_task, 
        step_back_query_task, 
        return_exceptions=True
    )
    
    # 第二步：并行执行专家QA检索和知识库检索
    expert_qa_task = get_relevant_expert_qa_memories(
        query=user_query,
        score_limit=0.2,
        limit=1
    )
    
    # 构建查询列表
    query_list = [user_question]  # 原始用户问题
    query_list.append(rewritten_query) if rewritten_query and not isinstance(rewritten_query, Exception) else None
    query_list.append(step_back_query) if step_back_query and not isinstance(step_back_query, Exception) else None
    logger.info(f"重写后的问题: {query_list}")
    
    # 并行执行所有查询的知识库检索
    retrieval_tasks = [
        retrieve_from_kb(question=query,
                        dataset_name=KB_DATASET_NAME,
                        address=KB_ADDRESS,
                        api_key=KB_API_KEY,
                        similarity_threshold=0.01,
                        vector_similarity_weight=KB_VECTOR_SIMILARITY_WEIGHT,
                        top_k=KB_TOP_K*15,
                        key_words=KB_KEY_WORDS)
        for query in query_list
    ]
    
    # 并行等待专家QA检索和知识库检索完成
    expert_qa_memories, all_results_list = await asyncio.gather(
        expert_qa_task,
        asyncio.gather(*retrieval_tasks, return_exceptions=True),
        return_exceptions=True
    )
    
    # 优先使用专家QA的结果
    if expert_qa_memories and not isinstance(expert_qa_memories, Exception) and len(expert_qa_memories) > 0:
        expert_qa = expert_qa_memories[0]
        logger.info(f"使用专家QA结果，分数: {expert_qa.get('score', 1.0)}")
        return RetrievalResult(
            source="expert_qa",
            content=expert_qa["answer"],
            score=expert_qa.get("score", 1.0),
            images=expert_qa.get("images"),
            metadata={"query_list": query_list}
        )
    
    # 合并所有检索结果
    all_results = []
    for result_list in all_results_list:
        if not isinstance(result_list, Exception):
            all_results.extend(result_list)
    
    # 去重（基于文档内容）
    seen_contents = set()
    unique_results = []
    for result in all_results:
        if result['content'] not in seen_contents:
            seen_contents.add(result['content'])
            unique_results.append(result)
    
    results = unique_results
    max_score = 0.0
    
    # 重排模型
    if len(results) > 0 and RERANKER_MODEL and RERANKER_ADDRESS:
        results, max_score = await rerank_results(results, user_question, RERANKER_MODEL, RERANKER_ADDRESS, RERANKER_API_KEY, KB_TOP_K)
        text = "\n\n".join(f"第{i+1}个与用户问题相关的文档内容如下：\n{doc['content']}" for i, doc in enumerate(results))
        logger.info(f"知识库检索成功，最高分数: {max_score}")
        return RetrievalResult(
            source="knowledge_base",
            content=text,
            score=max_score,
            images=None,
            metadata={"query_list": query_list, "doc_count": len(results)}
        )
    elif len(results) > 0:
        text = "\n\n".join(f"第{i+1}个与用户问题相关的文档内容如下：\n{doc['content']}" for i, doc in enumerate(results))
        logger.info(f"知识库检索成功（未使用重排）")
        return RetrievalResult(
            source="knowledge_base",
            content=text,
            score=0.0,
            images=None,
            metadata={"query_list": query_list, "doc_count": len(results)}
        )
    
    # 没有找到任何结果
    logger.warning("未找到任何相关检索结果")
    return RetrievalResult(
        source="none",
        content="抱歉，在知识库中没有找到与问题相关的信息。",
        score=0.0,
        images=None,
        metadata={"query_list": query_list}
    )


async def airport_knowledge_query2docs(user_question:str,messages:List[AnyMessage]) -> RetrievalResult:
    """
    简化版知识检索（仅知识库检索，不包含专家QA）
    
    Args:
        user_question: 用户问题
        messages: 历史消息列表
        
    Returns:
        RetrievalResult: 统一的检索结果对象
    """
    user_query = user_question
    rewritten_query_task = comprehensive_query_transform(user_query,'rewrite',messages)
    step_back_query_task = comprehensive_query_transform(user_query,'step_back',messages)  
    # 等待两个查询生成完成
    rewritten_query, step_back_query = await asyncio.gather(
        rewritten_query_task, 
        step_back_query_task, 
        return_exceptions=True
    )

    # 构建查询列表
    query_list = [user_question]  # 原始用户问题
    query_list.append(rewritten_query) if rewritten_query and not isinstance(rewritten_query, Exception) else None
    query_list.append(step_back_query) if step_back_query and not isinstance(step_back_query, Exception) else None
    logger.info(f"重写后的问题: {query_list}")
    
    # 并行执行所有查询的检索
    retrieval_tasks = [
        retrieve_from_kb(question=query,
                        dataset_name=KB_DATASET_NAME,
                        address=KB_ADDRESS,
                        api_key=KB_API_KEY,
                        similarity_threshold=0.01,
                        vector_similarity_weight=KB_VECTOR_SIMILARITY_WEIGHT,
                        top_k=KB_TOP_K,
                        key_words=KB_KEY_WORDS)
        for query in query_list
    ]
    all_results_list = await asyncio.gather(*retrieval_tasks, return_exceptions=True)
    
    # 合并所有检索结果
    all_results = []
    for result_list in all_results_list:
        if not isinstance(result_list, Exception):
            all_results.extend(result_list)
    
    # 去重（基于文档内容）
    seen_contents = set()
    unique_results = []
    for result in all_results:
        if result['content'] not in seen_contents:
            seen_contents.add(result['content'])
            unique_results.append(result)
    
    results = unique_results
    max_score = 0.0
    
    # 重排模型
    if len(results) > 0 and RERANKER_MODEL and RERANKER_ADDRESS:
        results, max_score = await rerank_results(results, user_question, RERANKER_MODEL, RERANKER_ADDRESS, RERANKER_API_KEY, KB_TOP_K)
        text = "\n\n".join(f"第{i+1}个与用户问题相关的文档内容如下：\n{doc['content']}" for i, doc in enumerate(results))
        logger.info(f"知识库检索成功，最高分数: {max_score}")
        return RetrievalResult(
            source="knowledge_base",
            content=text,
            score=max_score,
            images=None,
            metadata={"query_list": query_list, "doc_count": len(results)}
        )
    elif len(results) > 0:
        text = "\n\n".join(f"第{i+1}个与用户问题相关的文档内容如下：\n{doc['content']}" for i, doc in enumerate(results))
        logger.info(f"知识库检索成功（未使用重排）")
        return RetrievalResult(
            source="knowledge_base",
            content=text,
            score=0.0,
            images=None,
            metadata={"query_list": query_list, "doc_count": len(results)}
        )
    
    # 没有找到任何结果
    logger.warning("未找到任何相关检索结果")
    return RetrievalResult(
        source="none",
        content="抱歉，在知识库中没有找到与问题相关的信息。",
        score=0.0,
        images=None,
        metadata={"query_list": query_list}
    )
