"""
闲聊节点
"""
import httpx
from ..state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langgraph.prebuilt import ToolNode
from langgraph.config import get_store
from langgraph.store.base import BaseStore
from datetime import datetime
from ..tools import chitchat_query
from . import filter_messages_for_llm,max_msg_len,base_model
from common.logging import get_logger

logger = get_logger("agents.nodes.chitchat")
chitchat_tool_node = ToolNode([chitchat_query])

async def call_dashscope(dialog_his:list):
    url = "https://dashscope.aliyuncs.com/api/v1/apps/01dd90c394de4c468e0626dabef3d79e/completion"
    headers = {
        "Authorization": "Bearer sk-db024fbbe96445d8981c42a77c",
        "Content-Type": "application/json"
    }
    payload = {
        "input": {
            "messages":dialog_his
        },
        "parameters": {},
        "debug": {}
    }

    try:
        async with httpx.AsyncClient(timeout=360.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()['output']['text']
            else:
                return "抱歉，系统繁忙，请您稍后再试"
    except Exception as e:
        return "抱歉，系统繁忙，请您稍后再试"



async def handle_chitchat(state: AirportMainServiceState, config: RunnableConfig):
    """
    处理闲聊问题的节点函数

    Args:
        state: 当前状态对象
        config: 可运行配置

    Returns:
        更新后的状态对象，包含闲聊回复
    """
    logger.info("进入闲聊子智能体:")
    # 获取用户查询
    chitchat_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是深圳宝安国际机场 (SZX) 的智能客服助手，专门负责与旅客进行日常互动。

            作为机场客服：
            1. 你应该保持友好、专业和礼貌的态度
            2. 对于打招呼、问候等简单问题，给予温暖回应
            3. 回答应简洁明了，语气亲切自然
            4. 如果用户没有强制的要求你自我介绍，你不要自我介绍，只需要做最简短的回答。
            5.当前时间是: {time}，如果用户询问涉及时间的信息请考虑此因素。
            
            请注意：
            - 保持对话轻松愉快，增强旅客体验
            """
        ),
        ("placeholder", "{messages}"),
        ("human", "{user_query}")
    ]
    ).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    chain = chitchat_prompt | base_model
    # 获取消息历史
    new_messages = filter_messages_for_llm(state, max_msg_len)
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    # 调用链获取响应

    # msgs = chitchat_prompt.invoke({"messages": messages})
    # content = []
    # tmp = dict()
    # for msg in msgs.messages:
    #     tmp.clear()
    #     if len(msg.content.strip()) > 0:
    #         if msg.type == "human":
    #             tmp["role"] = "user"
    #             tmp["content"] = msg.content
    #             content.append(tmp.copy())
    #         elif msg.type == "ai":
    #             tmp["role"] = "assistant"
    #             tmp["content"] = msg.content
    #             content.append(tmp.copy())
    #         elif msg.type == "system":
    #             tmp["role"] = "system"
    #             tmp["content"] = msg.content
    #             content.append(tmp.copy())
    # response = await call_dashscope(content)
    # print("闲聊子智能体输出：",response)

    # # 提取用户画像
    # profile_executor.submit({"messages":state["messages"]+[AIMessage(role="闲聊子智能体",content=response)]},after_seconds=memery_delay)
    # return {"messages":[AIMessage(role="闲聊子智能体",content=response)]}
    
    user_query = state.get("user_query", "")
    response = await chain.ainvoke({"messages": messages,"user_query":user_query})
    response.role = "闲聊子智能体"
    # 提取用户画像
    # profile_executor.submit({"messages":state["messages"]+[response]},after_seconds=memery_delay)
    return {"messages":[response]} 