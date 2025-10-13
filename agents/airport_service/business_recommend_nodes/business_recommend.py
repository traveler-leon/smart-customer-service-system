"""
机场知识节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from agents.airport_service.state import BusinessRecommendState
from pydantic import BaseModel,Field
from typing import List
import json
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from trustcall import create_extractor
from agents.airport_service.core import filter_messages_for_llm,content_model
from datetime import datetime
from common.logging import get_logger
from agents.airport_service.context_engineering.prompts import business_recommend_prompts

# 获取机场知识节点专用日志记录器
logger = get_logger("agents.business-recommend-nodes.business_recommend")

class BusinessRecommendSchema(BaseModel):
    business: List[str] = Field(description="用户可能想要办理的机场提供的业务")

def replace_outer_single_quotes(lst):
    result = []
    for s in lst:
        s = s.strip()
        if s.startswith("'") and s.endswith("'"):
            s = '"' + s[1:-1] + '"'
        result.append(s)
    return result



async def provide_business_recommend(state: BusinessRecommendState, config: RunnableConfig):
    logger.info("进入业务推荐子智能体:")
    business_recommend_prompt = ChatPromptTemplate.from_messages([
        ("system", business_recommend_prompts.BUSINESS_RECOMMEND_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
        ("human", business_recommend_prompts.BUSINESS_RECOMMEND_HUMAN_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    extractor = create_extractor(
        content_model,
        tools=[BusinessRecommendSchema],
        tool_choice="BusinessRecommendSchema"
    )

    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"
    new_messages = filter_messages_for_llm(state, 5)
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    business_recommend_chain = business_recommend_prompt | extractor
    res = await business_recommend_chain.ainvoke({ "user_query": user_query,"messages":messages,"language":language})

    return {"messages":[AIMessage(content=json.dumps(replace_outer_single_quotes(res["responses"][0].business),ensure_ascii=False),name="业务推荐子智能体")], "user_query":None}





