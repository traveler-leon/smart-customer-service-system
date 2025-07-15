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
from agents.airport_service.core import filter_messages_for_llm,structed_model
from datetime import datetime
from common.logging import get_logger

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
        (
            "system",
            """你是民航机场的虚拟客服助手，名为"宝安小飞"。
            请根据用户的初始问题、以及对话历史，罗列出用户可能想要办理的机场提供的业务，罗列 3-5条。
            注意：生成的内容的语言类型必须和<question>中的用户问题的语言类型一致。
            """
        ),
        ("placeholder", "{messages}"),
        ("human", 
        """
        这是当前用户的问题: <question>{user_query}</question>
        当前时间是: {time}，如果用户询问涉及时间的信息请考虑此因素。
    """)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    extractor = create_extractor(
        structed_model,
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





