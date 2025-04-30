"""
闲聊节点
"""

from ..state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from . import base_model, filter_messages
from langgraph.prebuilt import ToolNode
from ..tools import chitchat_query
from . import max_msg_len

chitchat_tool_node = ToolNode([chitchat_query])

async def handle_chitchat(state: AirportMainServiceState, config: RunnableConfig):
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
            """你是济南遥墙国际机场 (TNA) 的智能客服助手，专门负责与旅客进行日常闲聊互动。

            作为机场客服：
            1. 你应该保持友好、专业和礼貌的态度
            2. 对于打招呼、问候等简单问题，给予温暖回应
            3. 可以回答天气、机场周边设施、交通等非专业性问题
            4. 如果用户问的是航班信息或机场政策等专业问题，你可以礼貌地建议他们咨询专门的航班查询或机场政策服务
            5. 回答应简洁明了，语气亲切自然
            
            请注意：
            - 保持对话轻松愉快，增强旅客体验
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
    response = await chain.ainvoke({"messages": messages})
    response.role = "闲聊子智能体"
    return {"messages":[response]} 