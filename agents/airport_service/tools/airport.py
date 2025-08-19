import sys
import os
from pprint import pprint
# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import asyncio
import aiohttp
import json
from langchain_core.tools import tool, InjectedToolCallId
from text2kb.retrieval import retrieve_from_kb
from langgraph.types import Command
from typing import Annotated, NotRequired
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from config.utils import config_manager
from agents.airport_service.core import rewrite_query,generate_step_back_query,rerank_results
from agents.airport_service.context_engineering.agent_memory import get_relevant_conversation_memories

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
RERANKER_API_KEY = _text2kb_config.get("reranker_api_key")

@tool
async def airport_knowledge_query(user_question:str,tool_call_id:Annotated[str,InjectedToolCallId],config:RunnableConfig) -> str:
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
    logger.info("进入机场知识查询工具:")
    # 并行生成重写查询和后退查询
    user_query = user_question
    rewritten_query_task = rewrite_query(user_query)
    step_back_query_task = generate_step_back_query(user_query)
    all_user_relevant_conversation_memories = get_relevant_conversation_memories(
        query=user_query,
        application_id="机场主智能客服",
        agent_id="机场知识问答子智能体",
        score_limit=0.85,
        limit=2
    )   
    # 等待两个查询生成完成
    rewritten_query, step_back_query, all_user_relevant_conversation_memories = await asyncio.gather(
        rewritten_query_task, 
        step_back_query_task, 
        all_user_relevant_conversation_memories,
        return_exceptions=True
    )
    conversation_memories = []
    if all_user_relevant_conversation_memories:
        tmp = {}
        for memory in all_user_relevant_conversation_memories:
            tmp.clear()
            if memory["user_id"]==config["configurable"].get("user_id"):
                tmp["user_id"] = "yourself"
            else:
                tmp["user_id"] = "other"
            tmp["query"] = memory["query"]
            tmp["response"] = memory["response"]
            tmp["created_at"] = memory["created_at"]
            conversation_memories.append(tmp)
        

    # 构建查询列表
    query_list = [user_question]  # 原始用户问题
    query_list.append(rewritten_query) if rewritten_query and not isinstance(rewritten_query, Exception) else None
    query_list.append(step_back_query) if step_back_query and not isinstance(step_back_query, Exception) else None

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
    text = "抱歉，在知识库中没有找到与问题相关的信息。"
    # 重排模型。
    if len(results) > 0 and RERANKER_MODEL and RERANKER_ADDRESS:
        results,max_score = await rerank_results(results, user_question,RERANKER_MODEL,RERANKER_ADDRESS,RERANKER_API_KEY,KB_TOP_K)
        text = "\n\n".join(f"第{i+1}个与用户问题相关的文档内容如下：\n{doc['content']}" for i, doc in enumerate(results))
    else:
        text = "\n\n".join(f"第{i+1}个与用户问题相关的文档内容如下：\n{doc['content']}" for i, doc in enumerate(results))

    logger.info(f"查询列表: {query_list}")
    logger.info(f"检索结果数量: {len(results) if 'results' in locals() else 0}")
    logger.debug(f"最终返回结果: {text}")
    return Command(
            update={
                'messages':[ToolMessage(content="知识检索结束",tool_call_id=tool_call_id)],
                'kb_context_docs':text,
                'kb_context_docs_maxscore':max_score,
                'conversation_memories':json.dumps(conversation_memories)
            },
        )


# if __name__ == "__main__":
#     pass
#     # 测试时提供一个虚拟的tool_call_id
#     print(asyncio.run(airport_knowledge_query.ainvoke({"user_question": "坐飞机可以带刀吗？", "tool_call_id": "test_call_id"})))
#     # print(asyncio.run(airport_knowledge_query.ainvoke({"user_question": "我有个充电宝，可以带上飞机吗?", "tool_call_id": "test_call_id"})))
