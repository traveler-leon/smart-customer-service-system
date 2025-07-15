import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from langmem.short_term import SummarizationNode, RunningSummary
from langchain_core.prompts import ChatPromptTemplate

from langgraph.graph import MessagesState
from agents.airport_service.core import base_model
from common.logging import get_logger

# 获取摘要节点专用日志记录器
logger = get_logger("agents.main-nodes.summary")



# summarization_node = SummarizationNode(
#     model=base_model,
#     max_tokens=384,
#     max_tokens_before_summary=512,
#     max_summary_tokens=128,
# )


# 客服对话摘要总结节点函数，提供给外部独立使用
async def summarize_conversation(state: MessagesState):
    """
    对话摘要总结节点函数

    Args:
        state: 当前状态对象

    Returns:
        更新后的状态对象，包含对话摘要
    """
    logger.info("进入对话摘要总结节点")

    # 获取消息历史
    messages = state.values.get("messages", [])
    logger.info(f"消息历史数量: {len(messages)}")
    
    # 构建提示模板
    summary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是一个专业的对话摘要助手。你的任务是对用户与济南遥墙国际机场客服系统之间的对话进行简洁明了的总结。

            请遵循以下指导：
            1. 摘要信息应该包括用户的问题，机场客服的回答，以及用户可能的后续需求
            
            你的摘要应该能让人快速了解对话的核心内容和结果。
            """
        ),
        ("placeholder", "{messages}"),
    ]
    )

    response = await base_model.ainvoke(summary_prompt.format(messages=messages))
    # 返回更新后的状态
    return {"summary": response.content}


# 人工坐席对话摘要总结函数
async def summarize_human_agent_conversation(conversation_list):
    """
    人工坐席对话摘要总结函数
    
    Args:
        conversation_list: 前端传来的对话列表
        
    Returns:
        对话摘要结果
    """
    print("进入人工坐席对话摘要总结函数")
    
    # 构建提示模板
    summary_prompt = ChatPromptTemplate.from_template("""你是一个专业的对话摘要助手。你的任务是对用户与济南遥墙国际机场人工客服之间的对话进行简洁明了的总结。
            请遵循以下指导：
            1. 摘要信息应该包括用户的问题，人工客服的回答，以及用户可能的后续需求
            2. 重点关注对话中的关键信息点和解决方案
            3. 如果有未解决的问题，请在摘要中特别指出
            4. 除了摘要总结信息之外，不要返回任何多余信息，比如不需要在内容的开头加上"摘要内容："等。
            你的摘要应该能让人快速了解对话的核心内容和结果。
            下面是用户与人工坐席的对话内容：
            {conversation_list}
            """)

    # 调用模型生成摘要
    response = await base_model.ainvoke(summary_prompt.format(conversation_list=conversation_list))
    
    # 返回摘要结果
    return {"summary": response.content}

