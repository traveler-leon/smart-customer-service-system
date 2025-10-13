"""
路由节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from agents.airport_service.state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from agents.airport_service.core import filter_messages_for_llm, max_msg_len,image_model
from agents.airport_service.context_engineering.prompts import main_graph_prompts
from langchain_core.messages import AIMessage
from common.logging import get_logger

# 获取路由节点专用日志记录器
logger = get_logger("agents.main-nodes.images_thinking")

async def images_thinking(state: AirportMainServiceState, config: RunnableConfig):
    user_query = state.get("user_query") if state.get("user_query") else config["configurable"].get("user_query", "")
    image_data = config["configurable"].get("image_data", None)
    logger.info(f"进入图像理解子智能体：{user_query}")
    if not image_data:
        return state
    image_assistant_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.IMAGE_UNDERSTANDING_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
        ("human",[
            {
            "type":"image_url",
            "image_url": {"url":"data:image/{image_type};base64,{image_data}"},
        },
        {
        "type":"text",
        "text": "用户初始问题：{user_query}。请你结合图片信息和用户原始问题，重新生成一个新的问题。问题必须是中文。",
        }   
        ])
    ])
    
    chain = image_assistant_prompt | image_model
    new_messages = filter_messages_for_llm(state, max_msg_len)
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    # 调用链获取响应
    image_type = image_data['content_type'].split('/')[-1]
    response = await chain.ainvoke({"messages": messages,"image_type":image_type,"image_data":image_data['data'],"user_query":user_query})
    logger.info(f"图片思考结果: {response.content}")
    return {"user_query":response.content}
