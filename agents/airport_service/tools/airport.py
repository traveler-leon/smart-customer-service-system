import sys
import os
from pprint import pprint
# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import asyncio
import aiohttp
import json
from langchain_core.tools import tool, InjectedToolCallId
from text2kb.retrieval import retrieve_from_kb,retrieve_from_kb_by_agent
from langgraph.types import Command
from typing import Annotated, NotRequired
from langchain_core.messages import ToolMessage
from xinference.client import Client
from config.utils import config_manager
from ..utils import rewrite_query,generate_step_back_query,rerank_results
from common.logging import get_logger
logger = get_logger("agents.tools.airport")

_text2kb_config = config_manager.get_text2kb_config()
KB_ADDRESS = _text2kb_config.get("kb_address")
KB_API_KEY = _text2kb_config.get("kb_api_key")
KB_DATASET_NAME = _text2kb_config.get("kb_dataset_name")
KB_SIMILARITY_THRESHOLD = float(_text2kb_config.get("kb_similarity_threshold"))
KB_VECTOR_SIMILARITY_WEIGHT = float(_text2kb_config.get("kb_vector_similarity_weight"))
KB_TOP_K = int(_text2kb_config.get("kb_topK"))
KB_KEY_WORDS = bool(_text2kb_config.get("kb_key_words"))
RERANKER_MODEL = _text2kb_config.get("reranker_model")
RERANKER_ADDRESS = _text2kb_config.get("reranker_address")

@tool
async def airport_knowledge_query(user_question:str,tool_call_id:Annotated[str,InjectedToolCallId]) -> str:
    """
    用于检索民航机场相关知识的工具，帮助解答乘客关于乘机须知的问题。
    
    此工具连接到专门的"民航机场知识库"，能够回答用户关于机场各个乘机须知类别的详细问题。包括：
    1. 安检须知
    2. 联检(边检、海关、检疫)须知
    3. 出行须知（订票（改签）、值机、登机、中转、出发、到达、行李、证件）

    当用户询问任何与机场乘机须知相关的问题时，应首选此工具。并提供符合检索的用户的完整问题。
    如果用户问题涉及上述知识类别的相关咨询，或明确询问机场规定和服务流程，都应该调用此工具。
    
    Args:
        user_question: 用户提出的机场服务相关问题，例如："液体可以带多少上飞机？"、
                      "行李超重怎么办？"或"机场有爱心服务吗？"
    
    Examples:
        >>> airport_knowledge_query("安检需要注意什么？")
        "乘客需要通过安检门，随身行李需要通过X光机检查。液体不超过100ml，需要放在透明袋中。"
    """
    logger.info("进入机场知识查询工具")
    logger.info(f"用户问题: {user_question}")

    # 并行生成重写查询和后退查询
    rewritten_query_task = rewrite_query(user_question)
    step_back_query_task = generate_step_back_query(user_question)
    
    # 等待两个查询生成完成
    rewritten_query, step_back_query = await asyncio.gather(
        rewritten_query_task, 
        step_back_query_task, 
        return_exceptions=True
    )
    
    # 构建查询列表
    query_list = [user_question]  # 原始用户问题
    if rewritten_query and not isinstance(rewritten_query, Exception):
        query_list.append(rewritten_query)
    if step_back_query and not isinstance(step_back_query, Exception):
        query_list.append(step_back_query)
    

    # 并行执行所有查询的检索
    retrieval_tasks = [
        retrieve_from_kb(question=query,
                        dataset_name=KB_DATASET_NAME,
                        address=KB_ADDRESS,
                        api_key=KB_API_KEY,
                        similarity_threshold=KB_SIMILARITY_THRESHOLD,
                        vector_similarity_weight=KB_VECTOR_SIMILARITY_WEIGHT,
                        top_k=KB_TOP_K,
                        key_words=KB_KEY_WORDS)
        for query in query_list
    ]
    
    # 等待所有检索完成
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
    # 重排模型。
    if len(results) > 0:
        reranked_results,max_score = await rerank_results(results, user_question,RERANKER_MODEL,RERANKER_ADDRESS,KB_TOP_K)
    format_doc = []
    if len(results) > 0:
        for i,doc in enumerate(reranked_results):
            format_doc.append(f"第{i+1}个与用户问题相关的文档内容如下：\n{doc['content']}")
        text = "\n\n".join(format_doc)
    else:
        text = "抱歉，在知识库中没有找到与问题相关的信息。"
    logger.info(f"查询列表: {query_list}")
    logger.info(f"检索结果数量: {len(reranked_results) if 'reranked_results' in locals() else 0}")
    logger.debug(f"最终返回结果: {text}")
    return Command(
            update={
                'messages':[ToolMessage(content="知识检索结束",tool_call_id=tool_call_id)],
                'current_query': user_question,
                'kb_context_docs':text,
                'kb_context_docs_maxscore':max_score
            },
        )

@tool
async def airport_knowledge_query_by_agent(user_question:str,tool_call_id:Annotated[str,InjectedToolCallId]) -> str:
    """
    用于检索济南机场相关知识的工具，帮助解答乘客关于乘机流程的问题。
    
    此工具连接到专门的"济南机场知识库"，能够回答用户关于机场各个服务类别的详细问题。包括：
    1. 安全检查服务：安检区域、安检须知
    2. 出行服务：爱心服务、服务电话、贵宾室服务、头等舱休息室服务、晚到服务
    3. 行李服务：托运须知、行李打包、行李寄存、行李赔偿、行李逾重须知
    4. 值机服务：团队预约、值机区域、自助办理、自助值机
    5. 中转服务
    
    当用户询问任何与济南机场服务相关的问题时，应首选此工具。
    如果用户问题涉及上述服务类别的相关咨询，或明确询问机场规定和服务流程，都应该调用此工具。
    
    Args:
        user_question: 用户提出的机场服务相关问题，例如："液体可以带多少上飞机？"、
                      "行李超重怎么办？"或"济南机场有爱心服务吗？"
    
    Examples:
        >>> airport_knowledge_query_by_agent("安检需要注意什么？")
        "乘客需要通过安检门，随身行李需要通过X光机检查。液体不超过100ml，需要放在透明袋中。"
    """
    from common.logging import get_logger
    logger = get_logger("agents.tools.airport")
    logger.info("进入机场知识查询工具(Agent版本)")
    logger.info(f"用户问题: {user_question}")

    text = await retrieve_from_kb_by_agent(question=user_question
                                     , agent_id="b2b2a32e33bc11f096ef4ef12f9f5002"
                                     ,address=KB_ADDRESS
                                     ,api_key=KB_API_KEY)
    logger.info(f"检索结果长度: {len(text) if text else 0}")
    return Command(
            update={
                'messages':[ToolMessage(content="知识检索结束,即将转到机场知识问答子智能体",tool_call_id=tool_call_id)],
                'current_query': user_question,
                'kb_context_docs':text,
            },
        )




if __name__ == "__main__":
    pass
    # 测试时提供一个虚拟的tool_call_id
    # print(asyncio.run(airport_knowledge_query.ainvoke({"user_question": "坐飞机可以带刀吗？", "tool_call_id": "test_call_id"})))
    # print(asyncio.run(airport_knowledge_query.ainvoke({"user_question": "我有个充电宝，可以带上飞机吗?", "tool_call_id": "test_call_id"})))
    # print(asyncio.run(airport_knowledge_query_by_agent.ainvoke({"user_question": "坐飞机可以带刀吗？", "tool_call_id": "test_call_id"})))
