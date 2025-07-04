import sys
import os
# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from typing import Annotated, NotRequired
from langchain_core.messages import ToolMessage
from common.logging import get_logger

# 获取闲聊工具专用日志记录器
logger = get_logger("agents.tools.chitchat")

@tool
async def chitchat_query(question: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
    """
    闲聊工具
    此工具用于回答用户关于问候、天气、交通、周边旅游景点、周边服务设施等一些闲聊问题。
    注意：如果用户问的是一些可不可以携带的物品等，不可以使用此工具。而是要调用其他的工具。

    Args:
        question: 用户提出的问题"
    Examples:
        >>> chitchat_query("你好，今天天气怎么样？")
        >>> chitchat_query("深圳宝安国际机场周边有哪些旅游景点？")
    """
    logger.info("进入闲聊工具")
    logger.info(f"用户问题: {question}")
    logger.info("准备转到闲聊子智能体")

    return Command(
        update={
            "messages": [ToolMessage(content="工具调用结束,即将转到闲聊子智能体", tool_call_id=tool_call_id)],
            "current_query": question
        }
    )


# if __name__ == "__main__":
#     flight_info_query.invoke({"question":"查一下从深圳出发的所有航班", "tool_call_id": "test_call_id"})