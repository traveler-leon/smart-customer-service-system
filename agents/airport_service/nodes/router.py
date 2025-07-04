"""
路由节点
"""
from ..state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from langgraph.store.base import BaseStore
from ..tools import airport_knowledge_query, flight_info_query,chitchat_query,business_handler
from . import filter_messages_for_llm
from . import max_msg_len
from langgraph.config import get_store
from langchain_core.messages import AIMessage
from . import structed_model
from common.logging import get_logger

# 获取路由节点专用日志记录器
logger = get_logger("agents.nodes.router")
tool_model = structed_model.bind_tools([airport_knowledge_query, flight_info_query,business_handler])
async def identify_intent(state: AirportMainServiceState, config: RunnableConfig, store: BaseStore):
    # store = get_store()
    messages = state.get("messages", [])
    if messages:
        user_query = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        logger.info(f"用户查询: {user_query}")
    else:
        logger.warning("没有找到用户消息")
    logger.info(f"进入主路由子智能体：{user_query}")
    airport_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是民航机场的智能客服系统决策助手。你的唯一任务是识别用户的意图，并将他们的请求路由到相应的工具。不要对用户进行任何直接回答或解释。

            <instructions>
            你需要识别的意图类型包括：
            - **航班信息查询:** 用户希望查询航班信息，例如航班号、起飞/到达时间、航班状态等。
            - **乘机须知:** 用户希望了解在深圳宝安国际机场乘机相关的规定和信息，例如安检须知、联检(边检、海关、检疫)须知、出行须知（订票（改签）、值机、登机、中转、出发、到达、行李、证件）等。以及处理闲聊问题
            - **业务办理:** 用户希望办理机场相关业务，例如轮椅租赁等。

            根据用户意图，你必须选择以下工具之一：
            - `flight_info_query`: 用于机场航班信息查询。
            - `airport_knowledge_query`: 用于机场乘机须知问答,安检须知、联检(边检、海关、检疫)须知、出行须知（订票（改签）、值机、登机、中转、出发、到达、行李、证件）等。以及处理闲聊问题
            - `business_handler`: 用于机场业务办理，例如行李寄存、行李查询、航班延误、航班取消、航班改签、航班退票、无人陪伴、轮椅租赁、失物招领、投诉等。

            操作步骤：
            1. 仔细分析完整的对话历史，理解用户真正的意图
            2. 基于完整对话历史，理解当前用户输入的意图，构建一个主谓宾结构完整、且一定要包含关键词、表述清晰明确的问题作为工具参数
            3. 选择最合适的工具
            4. 开始执行工具调用
            
            系统会根据你选择的工具自动将用户请求转发到相应的专门处理节点。
            </instructions>

            <critical_rules>
            1. 你是纯路由节点，不应该直接回答用户问题。必须通过工具调用进行路由。
            2. 即使是打招呼类的简单问题，也应该转交给airport_knowledge_query工具，而不是回答。
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
            正确操作: 使用airport_knowledge_query，参数"谢谢你的帮助"
            </example4>
            <example5>
            用户: "我想租一个轮椅"
            正确操作: 使用business_handler，参数"我想租一个轮椅"
            </example5>
            </examples>
            """
        ),
        ("placeholder", "{messages}"),
    ]
    ).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    chain = airport_assistant_prompt | tool_model
    new_messages = filter_messages_for_llm(state, max_msg_len)
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    # 调用链获取响应
    response = await chain.ainvoke({"messages": messages})
    response.role = "主路由智能体"
    
    # 返回更新后的状态
    return {"messages": [response],"user_query":user_query}

def route_to_next_node(state: AirportMainServiceState):
    # 获取最新消息
    messages = state.get("messages", [])
    if not messages:
        return "airport_tool_node"

    latest_message = messages[-1]
    # 检查是否有工具调用
    if not hasattr(latest_message, "tool_calls") or not latest_message.tool_calls:
        return "airport_tool_node"

    # 根据工具调用决定下一个节点
    tool_name = latest_message.tool_calls[-1].get("name", "")
    if tool_name == "flight_info_query":
        return "flight_tool_node"
    elif tool_name == "business_handler":
        return "business_tool_node"
    else:
        return "airport_tool_node"

    # else:
    #     return "chitchat_tool_node"