from langmem.short_term import SummarizationNode, RunningSummary
from langchain_core.prompts import ChatPromptTemplate

from langgraph.graph import MessagesState
from . import base_model



# summarization_node = SummarizationNode(
#     model=base_model,
#     max_tokens=384,
#     max_tokens_before_summary=512,
#     max_summary_tokens=128,
# )


# 对话摘要总结节点函数，提供给外部独立使用
async def summarize_conversation(state: MessagesState):
    """
    对话摘要总结节点函数
    
    Args:
        state: 当前状态对象
        
    Returns:
        更新后的状态对象，包含对话摘要
    """
    print("进入对话摘要总结节点")
    
    # 获取消息历史
    messages = state.values.get("messages", [])
    
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
