"""
机场知识节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from agents.airport_service.state import QuestionRecommendState
from pydantic import BaseModel,Field
from typing import List
import json
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from agents.airport_service.tools import airport_knowledge_query2docs
from trustcall import create_extractor
from agents.airport_service.core import filter_messages_for_llm,content_model
from datetime import datetime
from common.logging import get_logger
from agents.airport_service.context_engineering.prompts import question_recommend_prompts

# 获取机场知识节点专用日志记录器
logger = get_logger("agents.problems-recommend-nodes.question_recommend")

class QuestionRecommendSchema(BaseModel):
    question: List[str] = Field(description="用户可能询问的问题")

def replace_outer_single_quotes(lst):
    result = []
    for s in lst:
        s = s.strip()
        if s.startswith("'") and s.endswith("'"):
            s = '"' + s[1:-1] + '"'
        result.append(s)
    return result


async def provide_question_recommend(state: QuestionRecommendState, config: RunnableConfig):
    """
    问题推荐节点
    基于检索结果为用户推荐相关问题
    """
    logger.info("进入问题推荐子智能体")
    question_recommend_prompt = ChatPromptTemplate.from_messages([
        ("system", question_recommend_prompts.QUESTION_RECOMMEND_SYSTEM_PROMPT),
        ("human", question_recommend_prompts.QUESTION_RECOMMEND_HUMAN_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    extractor = create_extractor(
        content_model,
        tools=[QuestionRecommendSchema],
        tool_choice="QuestionRecommendSchema"
    )

    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"
    messages = filter_messages_for_llm(state, 5)
    
    # 执行知识检索
    retrieval_result = await airport_knowledge_query2docs(user_query, messages)
    
    # 使用统一的检索结果
    context = retrieval_result.content if retrieval_result else ""
    logger.info(f"问题推荐使用检索结果，来源: {retrieval_result.source if retrieval_result else 'none'}")
    
    question_recommend_chain = question_recommend_prompt | extractor
    res = await question_recommend_chain.ainvoke({
        "user_query": user_query,
        "context": context,
        "messages": messages,
        "language": language
    })

    return {
        "messages": [AIMessage(
            content=json.dumps(replace_outer_single_quotes(res["responses"][0].question), ensure_ascii=False),
            role="问题推荐子智能体"
        )],
        "user_query": None,
        "retrieval_result": None  # 清空检索结果
    }





