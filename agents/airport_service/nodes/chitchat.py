"""
闲聊节点
"""

from ..state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from . import base_model, filter_messages
from langgraph.prebuilt import ToolNode
from langgraph.config import get_store
from langgraph.store.base import BaseStore
from http import HTTPStatus
from dashscope import Application

from ..tools import chitchat_query
from . import base_model,filter_messages,profile_executor,memery_delay,max_msg_len

chitchat_tool_node = ToolNode([chitchat_query])

async def handle_chitchat(state: AirportMainServiceState, config: RunnableConfig, store: BaseStore):
    store = get_store()
    """
    处理闲聊问题的节点函数

    Args:
        state: 当前状态对象
        config: 可运行配置
        
    Returns:
        更新后的状态对象，包含闲聊回复
    """
    chitchat_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是深圳宝安国际机场 (SZX) 的智能客服助手，专门负责与旅客进行日常互动。

            作为机场客服：
            1. 你应该保持友好、专业和礼貌的态度
            2. 对于打招呼、问候等简单问题，给予温暖回应
            3. 回答应简洁明了，语气亲切自然
            4. 如果用户问题的太宽泛，请引导用户具体化问题，要求用户提供更详细的信息
            
            请注意：
            - 保持对话轻松愉快，增强旅客体验
            - 回答完用户问题之后，必须最后加上"本内容并未在机场知识库上有规定，仅供参考"
            """
        ),
        ("placeholder", "{messages}"),
    ]
    )
    print("进入闲聊节点")
    chain = chitchat_prompt | base_model
    # 获取消息历史
    new_state = filter_messages(state, max_msg_len)
    messages = new_state.get("messages", [])
    # 调用链获取响应

    msgs = chitchat_prompt.invoke({"messages": messages})
    content = ""
    for msg in msgs.messages:
        # print(msg.name,msg.content)
        content += msg.type + ":" + msg.content + "\n"
    print("用户输入：",messages[-1].content)
    response = Application.call(
        # 若没有配置环境变量，可用百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
        api_key="sk-2e8c1dd4f75a44bf8114b337a5498a91",
        app_id='01dd90c394de4c468e0626dabef3d79e',# 替换为实际的应用 ID
        prompt=messages[-1].content)

    if response.status_code != HTTPStatus.OK:
        pass
    else:
        print("闲聊子智能体回复：",response.output.text)
    
    return {"messages":[AIMessage(role="闲聊子智能体",content=response.output.text)]}
    

    # response = await chain.ainvoke({"messages": messages})
    # response.role = "闲聊子智能体"
    # # 提取用户画像
    # profile_executor.submit({"messages":state["messages"]+[response]},after_seconds=memery_delay)
    # return {"messages":[response]} 