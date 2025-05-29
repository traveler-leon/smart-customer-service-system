import sys
import os
# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from langchain_core.tools import tool
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from typing_extensions import Annotated
from langchain_core.messages import ToolMessage

@tool
async def chitchat_query(question: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
    """
    闲聊工具
    此工具用于回答用户关于问候、天气、交通等一些闲聊问题。
    注意：如果用户问的是一些可不可以携带的物品等，不可以使用此工具。而是要调用其他的工具。

    Args:
        question: 用户提出的问题"
    Examples:
        >>> chitchat_query("你好，今天天气怎么样？")
        "今天天气晴朗，温度适宜，适合出行。"
    """
    return Command(
        update={
            "messages": [ToolMessage(content="工具调用结束,即将转到闲聊子智能体", tool_call_id=tool_call_id)],
            "current_query": question
        }
    )


# if __name__ == "__main__":
#     flight_info_query.invoke({"question":"查一下从深圳出发的所有航班", "tool_call_id": "test_call_id"})