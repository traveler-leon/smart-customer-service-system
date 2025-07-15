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
from agents.airport_service.tools import airport_knowledge_query
from trustcall import create_extractor
from agents.airport_service.core import filter_messages_for_llm,structed_model
from datetime import datetime
from common.logging import get_logger

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
    logger.info("进入问题推荐子智能体:")
    question_recommend_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是民航机场的虚拟客服助手，名为"宝安小飞"。
            请根据用户的初始问题、知识库<context>中的内容、以及对话历史，抽取出用户下一步可能问的5个问题。抽取出的问题列表必须是知识库支持回答的。
            注意：
                1.生成的内容的语言类型必须和<question>中的用户问题的语言类型一致。
                2.生成的内容必须符合知识库中的内容。
                3.生产的问题必须以第一人称回答。
            """
        ),
        ("placeholder", "{messages}"),
        ("human", 
        """
            知识库内容。
            <context> 
            {context}
            </context> 
            这是当前用户的问题: <question>{user_query}</question>
            当前时间是: {time}，如果用户询问涉及时间的信息请考虑此因素。
    """)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    extractor = create_extractor(
        structed_model,
        tools=[QuestionRecommendSchema],
        tool_choice="QuestionRecommendSchema"
    )

    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"
    kg_res = await airport_knowledge_query.ainvoke({"user_question": user_query, "tool_call_id": "kg_call_id"})
    context_docs = kg_res.update["kb_context_docs"]
    new_messages = filter_messages_for_llm(state, 5)
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    question_recommend_chain = question_recommend_prompt | extractor
    res = await question_recommend_chain.ainvoke({ "user_query": user_query,"context": context_docs,"messages":messages,"language":language})

    return {"messages":[AIMessage(content=json.dumps(replace_outer_single_quotes(res["responses"][0].question),ensure_ascii=False),role="问题推荐子智能体")], "user_query":None}





