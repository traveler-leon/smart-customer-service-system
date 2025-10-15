"""
机场知识节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from ..state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command
from langchain_core.messages import AIMessage
from agents.airport_service.tools import airport_knowledge_query2docs_main
from agents.airport_service.core import filter_messages_for_agent, max_msg_len, KB_SIMILARITY_THRESHOLD,content_model
from agents.airport_service.context_engineering.prompts import main_graph_prompts
from agents.airport_service.context_engineering.agent_memory import memory_enabled_agent
from datetime import datetime
from langgraph.config import get_stream_writer

from common.logging import get_logger

logger = get_logger("agents.main-nodes.airport")

@memory_enabled_agent(application_id="机场主智能客服")
async def airport_knowledge_agent(state: AirportMainServiceState, config: RunnableConfig):
    """
    机场知识问答处理节点
    使用统一的检索结果进行问答生成
    """
    logger.info("进入机场知识问答子智能体")

    # user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    user_query = state.get("retrieval_result").query_list[1] if state.get("retrieval_result", "") else config["configurable"].get("user_query", "")
    
    # 获取统一的检索结果
    retrieval_result = state.get("retrieval_result")
    
    # 如果是专家QA，直接返回结果
    if retrieval_result and retrieval_result.source == "expert_qa":
        logger.info("使用专家QA直接回答")
        return {"retrieval_result": None}  # 清空检索结果
    
    # 准备上下文信息
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"
    
    # 检查检索结果是否有效
    if not retrieval_result or retrieval_result.source == "none":
        logger.info("无有效检索结果，转向闲聊节点")
        return Command(
            goto="chitchat_node",
            update={"retrieval_result": None}
        )
    
    # 检查知识库检索分数是否达标
    if retrieval_result.source == "knowledge_base" and retrieval_result.score < KB_SIMILARITY_THRESHOLD:
        logger.info(f"检索分数 {retrieval_result.score} 低于阈值 {KB_SIMILARITY_THRESHOLD}，转向闲聊节点")
        return Command(
            goto="chitchat_node",
            update={"retrieval_result": None}
        )
    
    logger.info(f"使用知识库检索结果，分数: {retrieval_result.score}")
    
    # 构建提示模板
    kb_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.AIRPORT_KNOWLEDGE_SYSTEM_PROMPT),
        ("human", main_graph_prompts.AIRPORT_KNOWLEDGE_HUMAN_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    new_messages = filter_messages_for_agent(state, max_msg_len, "机场知识问答子智能体")
    logger.info(f"机场知识问答子智能体消息数量: {len(new_messages)}")

    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]

    kb_chain = kb_prompt | content_model
    res = await kb_chain.ainvoke({
        "user_query": user_query,
        "context": retrieval_result.content,
        "messages": messages,
        "language": language
    })
    res.name = "机场知识问答子智能体"
    
    return {
        "messages": [res],
        "retrieval_result": None  # 清空检索结果
    }

@memory_enabled_agent(application_id="机场主智能客服")
async def airport_knowledge_search(state: AirportMainServiceState, config: RunnableConfig):
    """
    机场知识检索节点
    执行统一的知识检索（包含专家QA和知识库）
    """
    logger.info("进入机场知识检索节点")
    
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    messages = filter_messages_for_agent(state, max_msg_len, "机场知识问答子智能体")
    
    # 执行统一检索
    retrieval_result = await airport_knowledge_query2docs_main(user_query, messages)
    logger.info(f"机场知识检索结果{retrieval_result.score}: {retrieval_result.content}")
    
    writer = get_stream_writer()
    
    # 如果是专家QA结果，直接返回答案
    if retrieval_result.source == "expert_qa":
        logger.info("检索到专家QA结果，直接返回")
        writer({
            "node_name": "airport_info_search_node",
            "data": {
                "type": "expert_qa",
                "answer": retrieval_result.content,
                "images": retrieval_result.images,
                "score": retrieval_result.score
            }
        })
        return {
            "messages": [AIMessage(content=retrieval_result.content, name="机场知识问答子智能体")],
            "retrieval_result": retrieval_result
        }
    
    # 返回知识库检索结果或无结果
    logger.info(f"检索完成，来源: {retrieval_result.source}, 分数: {retrieval_result.score}")
    return {"retrieval_result": retrieval_result}




