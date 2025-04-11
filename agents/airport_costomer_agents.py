import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage,HumanMessage,SystemMessage,RemoveMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph,START,END
from langgraph.graph import MessagesState
from langchain_core.runnables.config import RunnableConfig
from typing import Dict, Annotated
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime
from tools import airport_knowledge_query,flight_info_query,question_clarification
from langgraph.types import Command
from typing_extensions import TypedDict, Literal

import warnings
warnings.filterwarnings("ignore")

base_url = "https://api.siliconflow.cn/v1"
api_key = "sk-zcewmhyhkaelmhrijbipqbrlfxhwnfbuegcpynkhdbzkqixd"
model = "Qwen/Qwen2.5-72B-Instruct"

base_model = ChatOpenAI(model=model,temperature=0.5,api_key=api_key,base_url=base_url)


def dict_merge(old_dict, new_dict):
    """合并字典，处理状态更新"""
    if not old_dict:
        return new_dict
    if not new_dict:
        return old_dict
    return {**old_dict, **new_dict}

class State(MessagesState):
    user_base_info: Annotated[dict, dict_merge] = {}
    user_profile_info: Annotated[dict, dict_merge] = {}

    user_question: str
    question_clarification:str
    clarification_needed: bool = False




# 将 filter_messages 函数移动到这里
def filter_messages(state: Dict, nb_messages: int = 10) -> Dict:
    """过滤消息列表，返回适合处理的格式"""
    messages = state.get("messages", [])
    if len(messages) > nb_messages:
        messages = messages[-nb_messages:]
    return {**state, "messages": messages}


# 持久化配置
config = {
    "configurable":{
        "thread_id": "1"
    },
   "token":"" 
}


def get_user_base_info(state: State,config: RunnableConfig) -> State:
    """
    获取用户基础信息
    
    Args:
        user_id: 用户ID
        
    Returns:
        包含用户基础信息的字典
    """
    if state.get("user_base_info"):
        return state
    else:
        user_base_info = {"订单号":"1234567890","航班号":"CA1234","出发地":"北京","目的地":"上海","出发时间":"2024-01-01 10:00:00","到达时间":"2024-01-01 12:00:00","乘客姓名":"张三","乘客身份证号":"123456789012345678","乘客手机号":"12345678901"}
        print("获取用户基础信息")
        return {"user_base_info":user_base_info}

def get_user_profile_info(state: State,config: RunnableConfig) -> State:
    """
    获取用户画像信息
    
    Args:
        user_id: 用户ID
        
    Returns:
        包含用户画像信息的字典
    """
    if state.get("user_profile_info"):
        return state
    else:
        user_profile_info = {"爱好":"旅游","出行方式":"飞机","出行频率":"每周一次","出行目的":"商务出差","出行时间":"2024-01-01 10:00:00","到达时间":"2024-01-01 12:00:00","乘客姓名":"张三","乘客身份证号":"123456789012345678","乘客手机号":"12345678901"}
        print("获取用户画像信息")
        return {"user_profile_info":user_profile_info}


def router_sub_agent(state: State) -> State:
    """
    路由子节点
    
    Args:
        state: 当前状态对象
    """
    if len(state["messages"][-1].tool_calls) == 0:
        return END
    elif state["messages"][-1].tool_calls[-1]['name'] == "flight_info_query":
        return "flight_info_assistant"
    elif state["messages"][-1].tool_calls[-1]['name'] == "airport_knowledge_query":
        return "airport_knowledge_assistant"
        


identify_model = base_model.bind_tools([flight_info_query,airport_knowledge_query])
def identify_intent(state: State, config: RunnableConfig) -> Command[Literal["flight_info_assistant","airport_knowledge_assistant","__end__"]]:
    """
    识别用户意图的节点函数
    
    Args:
        state: 当前状态对象
        config: 可运行配置
        
    Returns:
        更新后的状态对象，包含识别出的意图
    """
    tmp_msg = filter_messages(state)
    airport_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是济南遥墙国际机场的一名客户支持助手。你可以为用户提供航班查询、还有到机场乘机相关的一些注意事项查询服务。"
            " 具体的每一个服务都是通过调用工具来完成，使用提供的工具来搜索航班、机场政策和其他信息以协助用户的查询。"
            " 如果在搜索时要持续尝试。如果第一次搜索没有结果，请扩大搜索范围。"
            " 如果搜索结果为空，在放弃之前先扩大搜索范围。"
            "注意1：如果涉及到时间问题，要结合当下的时间来进行判断"
            "注意2：如果用户询问的问题无法回答，请告诉用户无法回答这个问题，并建议用户使用其他工具来查询相关信息"
            "注意3：如果用户问一些关于：你好，这样的语句，大概率是要开启新的一轮服务咨询，最好你也要重新介绍一下自己"
            "注意4：用户的问题必须非常明确你才能调用相应，否则要求用户继续澄清"
            "\n当前时间: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
    ).partial(time=datetime.now())

    # 使用prompt_template处理消息
    chain = airport_assistant_prompt | identify_model
    messages = tmp_msg.get("messages", [])
    response = chain.invoke({"messages": messages})


    if len(response.tool_calls) == 0:
        return Command(
            update={
                'messages':[response],
            },
            goto="__end__"
        )
    elif response.tool_calls[-1]['name'] == "flight_info_query":
        return Command(
            update={
                'messages':[response],
                'user_question': response.tool_calls[-1]['args']['question']
            },
            goto="flight_info_assistant"
        )
    elif response.tool_calls[-1]['name'] == "airport_knowledge_query":
        return Command(
            update={
                'messages':[response],
                'user_question': response.tool_calls[-1]['args']['question']
            },
            goto="airport_knowledge_assistant"
        )
    
    # return {"messages": [response]}




# 问题完整性判断节点函数
def check_question_completeness(state: State, config: RunnableConfig) -> Command[Literal["__end__"]]:
    """
    分析用户问题并在需要时进行澄清
    
    此函数用于分析用户提出的问题，判断是否需要进一步澄清，以便能够准确地调用相应工具进行查询。
    如果问题不明确或缺少关键信息，将生成澄清性问题引导用户提供更多信息。
    
    Args:
        state: 当前状态对象，包含用户消息
        config: 可运行配置
        
    Returns:
        更新后的状态对象，包含问题分析结果和可能的澄清问题
    """
    # tmp_msg = filter_messages(state)
    # if state.get("question_clarification"):
    # question_analysis_prompt = ChatPromptTemplate.from_messages(
    # [
    #     (
    #         "system",
    #         "你是一个语言结构分析专家。你的任务是分析用户问题的语言结构完整性，判断是否存在语法或结构上的缺失。"
    #         "请检查用户问题是否缺少主语、谓语、宾语、定语等关键语法成分，导致表达不清或意图模糊。"
    #         "如果用户的问题在语言结构上不完整（如缺少主语、谓语等），请生成一个简短、礼貌的澄清问题，引导用户补充缺失的语法成分。"
    #         "如果用户的问题在语言结构上已经完整，表达清晰，请直接确认问题完整性，无需额外澄清。"
    #         "注意：你只需关注语言结构本身的完整性，而非具体业务内容的详尽程度。"
    #     ),
    #     ("placeholder", "user_question:{user_question}"),
    # ])

    # question_runnable = question_analysis_prompt | base_model.bind_tools([question_clarification])
    # # 使用prompt_template处理消息
    # messages = tmp_msg.get("messages", [])
    # response = question_runnable.invoke({"messages": messages})
    # if len(response.tool_calls) == 0:
    #     return Command(
    #         update={
    #             'messages':[response],
    #         },
    #         goto="__end__"
    #     )
    # else:
    #     return Command(
    #         update={
    #             'messages':[response],
    #             'question_clarification': response.tool_calls[-1]['args']['question'],
    #             'clarification_needed': True
    #         },
    #         goto="__end__"
    #     )



    # return {**state, "question_complete": is_complete, "clarification_needed": clarification_needed}

# 实现航班信息问答子智能体结构
def flight_info_assistant(state: State, config: RunnableConfig) -> State:
    """
    航班信息助手
    
    Args:
        state: 当前状态对象
        config: 可运行配置
    """
    new_msg = state["messages"][-1]
    print("航班信息助手")
    return {**state,"messages":[]}





def airport_knowledge_assistant(state: State, config: RunnableConfig) -> State:
    """
    机场知识助手
    
    Args:
    """
    print("机场知识助手")
    return {**state,"messages":[]}









if __name__ == "__main__":
    builder = StateGraph(State)
    builder.add_node("get_user_base_info",get_user_base_info)
    builder.add_node("get_user_profile_info",get_user_profile_info)
    builder.add_node("identify_intent",identify_intent)
    builder.add_node("flight_info_assistant",flight_info_assistant)
    builder.add_node("airport_knowledge_assistant",airport_knowledge_assistant)
    builder.add_node("check_question_completeness",check_question_completeness)

    builder.add_edge(START, "get_user_base_info")
    builder.add_edge(START,"get_user_profile_info")
    builder.add_edge("get_user_base_info","identify_intent")
    builder.add_edge("get_user_profile_info","identify_intent")
    # builder.add_conditional_edges("identify_intent",router_sub_agent,["flight_info_assistant","airport_knowledge_assistant",END])
    builder.add_edge("flight_info_assistant","check_question_completeness")
    builder.add_edge("airport_knowledge_assistant","check_question_completeness")
    memory = MemorySaver()
    graph = builder.compile(
        checkpointer=memory,
    )


    try:
        graph_image = graph.get_graph(xray=True).draw_mermaid_png()
        with open("graph_7.png", "wb") as f:
            f.write(graph_image)
    except Exception as e:
        print(f"保存图形时出错: {e}")

    while True:
        user_input = input("请输入：")
        if user_input == "exit":
            break
        else:
            res = graph.stream({"messages":[HumanMessage(content=user_input)]},config,stream_mode="updates")
            for item in res:
                print("=========")
                print(item)

















