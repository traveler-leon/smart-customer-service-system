"""
路由节点
"""
from ..state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from langgraph.store.base import BaseStore
from ..tools import airport_knowledge_query, flight_info_query,chitchat_query,airport_knowledge_query_by_agent
from . import filter_messages
from . import max_msg_len
from langgraph.config import get_store
from langchain_core.messages import AIMessage
from . import base_model,router_model

# 绑定工具的模型
# tool_model = router_model.bind_tools([airport_knowledge_query, flight_info_query,chitchat_query])
tool_model = base_model.bind_tools([airport_knowledge_query_by_agent, flight_info_query,chitchat_query])

async def identify_intent(state: AirportMainServiceState, config: RunnableConfig, store: BaseStore):
    store = get_store()
    """
    识别用户意图的节点函数
    
    Args:
        state: 当前状态对象
        config: 可运行配置
        
    Returns:
        更新后的状态对象，包含识别出的意图
    """
    print("进入主路由子智能体")
    # 构建提示模板
    airport_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是民航机场的智能客服系统决策助手。你的唯一任务是识别用户的意图，并将他们的请求路由到相应的工具。不要对用户进行任何直接回答或解释。

            <instructions>
            你需要识别的意图类型包括：
            - **信息查询:** 用户希望查询航班信息，例如航班号、起飞/到达时间、航班状态等；交通信息。
            - **乘机须知:** 用户希望了解在深圳宝安国际机场乘机相关的规定和信息，例如安检须知、联检(边检、海关、检疫)须知、出行须知（订票（改签）、值机、登机、中转、出发、到达、行李、证件）等。
            - **机场服务:** 用户希望了解深圳宝安国际机场的服务信息，例如机场设施、商业服务
            - **业务办理:** 用户希望办理机场相关业务，例如行李寄存、行李查询、航班延误、航班取消、航班改签、航班退票、无人陪伴、轮椅租赁、失物招领、投诉等。
            - **闲聊:** 用户希望与机场客服进行闲聊，比如问候、天气、周边旅游景点、周边服务设施等。

            根据用户意图，你必须选择以下工具之一：
            - `flight_info_query`: 用于机场信息查询。
            - `airport_knowledge_query`: 用于机场乘机须知问答。
            - `chitchat_query`: 用于处理闲聊类问题。

            操作步骤：
            1. 仔细分析完整的对话历史，理解用户真正的意图
            2. 选择最合适的工具
            3. 基于完整对话历史，理解当前的意图，构建一个主谓宾结构完整、且一定要包含关键词、表述清晰明确的问题作为工具参数
            
            系统会根据你选择的工具自动将用户请求转发到相应的专门处理节点。
            </instructions>

            <critical_rules>
            1. 你是纯路由节点，不应该直接回答用户问题。必须通过工具调用进行路由。
            2. 即使是打招呼类的简单问题，也应该转交给闲聊工具，而不是回答。
            3. 当前时间是: {time}，如果用户询问涉及时间的信息请考虑此因素。
            4. 必须结合完整的对话历史，理解当前的意图，构建主谓宾结构完整的问题。对话历史中可能包含关键上下文。
            </critical_rules>

            <examples>
            <example1>
            用户: "请问明天下午3点的重庆飞济南航班是什么时候到？"
            正确操作: 使用flight_info_query，参数"明天下午3点从重庆飞往济南的航班什么时候到达？"
            </example1>
            <example2>
            用户: "我可以带充电宝上飞机吗？"
            正确操作: 使用airport_knowledge_query，参数"乘客可以携带充电宝登机吗？"
            </example2>
            <example3>
            用户A: "我要去北京"
            用户B: "航班是什么时候？"
            正确操作: 使用flight_info_query，参数"从济南到北京的航班是什么时候？"（注意结合了上下文）
            </example3>
            <example4>
            用户: "谢谢你的帮助"
            正确操作: 使用chitchat_query，参数"谢谢你的帮助"
            </example4>
            <example5>
            用户: "现在出发，从杭州萧山国际机场到杭州西湖景区。请你提供三种公共交通出行方案"
            正确操作: 使用chitchat_query，参数"现在出发，从杭州萧山国际机场到杭州西湖景区。请你提供三种公共交通出行方案"
            </example5>
            </examples>
            """
        ),
        ("placeholder", "{messages}"),
    ]
    ).partial(time=datetime.now())

    # 构建链
    chain = airport_assistant_prompt | tool_model
    # print("当前对话历史为：",state.get("messages",[]))
    # 获取消息历史
    new_state = filter_messages(state, max_msg_len)
    messages = new_state.get("messages", [AIMessage(content="暂无对话历史，可路由到闲聊工具")])
    # 调用链获取响应
    response = await chain.ainvoke({"messages": messages})
    response.role = "主路由智能体"
    
    # 返回更新后的状态
    return {"messages": [response]}

# def route_to_next_node(state: AirportMainServiceState):
#     """
#     根据当前状态路由到下一个节点
    
#     Args:
#         state: 当前状态对象
        
#     Returns:
#         字符串，表示下一个节点的名称
#     """
#     # 获取最新消息
#     messages = state.get("messages", [])
#     if not messages:
#         return "chitchat_tool_node"
#     latest_message = messages[-1]
#     # 检查是否有工具调用
#     if not hasattr(latest_message, "tool_calls") or not latest_message.tool_calls:
#         return "chitchat_tool_node"
    
#     # 根据工具调用决定下一个节点
#     tool_name = latest_message.tool_calls[-1].get("name", "")
    
#     if tool_name == "flight_info_query":
#         return "flight_tool_node"
#     elif tool_name == "airport_knowledge_query":
#         return "airport_tool_node"
#     else:
#         return "chitchat_tool_node" 
    


def route_to_next_node(state: AirportMainServiceState):
    """
    根据当前状态路由到下一个节点
    
    Args:
        state: 当前状态对象
        
    Returns:
        字符串，表示下一个节点的名称
    """
    # 获取最新消息
    messages = state.get("messages", [])
    if not messages:
        return "chitchat_tool_node"
    latest_message = messages[-1]
    # 检查是否有工具调用
    if not hasattr(latest_message, "tool_calls") or not latest_message.tool_calls:
        return "chitchat_tool_node"
    
    # 根据工具调用决定下一个节点
    tool_name = latest_message.tool_calls[-1].get("name", "")
    
    if tool_name == "flight_info_query":
        return "flight_tool_node"
    # elif tool_name == "airport_knowledge_query_by_agent":
    #     return "airport_tool_node"
    elif tool_name == "airport_knowledge_query":
        return "airport_tool_node"
    else:
        return "chitchat_tool_node" 