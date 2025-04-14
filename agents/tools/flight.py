from langchain_core.tools import tool
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from typing_extensions import Annotated
from langchain_core.messages import ToolMessage

@tool
def flight_info_query(question: str,tool_call_id:Annotated[str,InjectedToolCallId]) -> str:
    """
    查询航班信息的工具
    此工具用于回答用户关于航班的各类查询
    
    Args:
        question: 用户提出的航班相关问题，应当是一个表达完整，意图明确的问句，例如"CA1234航班什么时候到达？"
                 "从北京到上海的航班有哪些？"或"明天的MU5678航班是什么机型？"等。如果问题不清晰，则需要用户继续澄清诉求。
    Examples:
        >>> flight_info_query("CA1234航班现在的状态是什么？")
        "CA1234航班目前正在飞行中，预计17:30到达目的地，暂无延误。"
    """
    return Command(
        update={
            "messages": [ToolMessage(content=" ",tool_call_id=tool_call_id)],
        },
        goto="__end__"
    )
