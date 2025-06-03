import sys
import os
# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from langchain_core.tools import tool
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from typing_extensions import Annotated
from langchain_core.messages import ToolMessage
import asyncio
from text2sql import create_text2sql
from config.utils import config_manager

# 全局变量缓存text2sql实例
_text2sql_instance = None
_text2sql_lock = asyncio.Lock()

async def get_text2sql_instance():
    """获取text2sql实例，如果不存在则创建一个"""
    global _text2sql_instance
    
    # 使用锁确保在并发环境下只初始化一次
    async with _text2sql_lock:
        if _text2sql_instance is None:
            try:
                # 获取text2sql配置
                text2sql_config = config_manager.get_text2sql_config()
                _text2sql_instance = await create_text2sql(text2sql_config)
                print("text2sql实例已初始化")
            except Exception as e:
                print(f"初始化text2sql实例时出错: {str(e)}")
                raise
    
    return _text2sql_instance


@tool
async def flight_info_query(question: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
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
    # 定义异步查询函数
    async def perform_query(query):
        try:
            # 获取缓存的text2sql实例，避免重复初始化
            smart_sql = await get_text2sql_instance()
            # 调用ask方法获取结果
            result = await smart_sql.ask(query)
            return result       
        except Exception as e:
            return f"查询航班信息时出错: {str(e)}"

    # 执行异步查询
    # result = asyncio.run(perform_query(question))
    result = await perform_query(question)
    return Command(
        update={
            "messages": [ToolMessage(content=result['sql'], tool_call_id=tool_call_id)],
            "current_query": question,
            "db_context_docs": result
        }
    )


# if __name__ == "__main__":
#     flight_info_query.invoke({"question":"查一下从深圳出发的所有航班", "tool_call_id": "test_call_id"})