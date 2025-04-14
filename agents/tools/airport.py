from langchain_core.tools import tool
import asyncio
from langchain_core.tools import tool
from text2kb.retrieval import retrieve_from_kb
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from typing_extensions import Annotated
from langchain_core.messages import ToolMessage

@tool
def airport_knowledge_query(user_question:str,tool_call_id:Annotated[str,InjectedToolCallId]) -> str:
    """
    查询乘机相关知识的工具
    
    此工具用于回答用户关于乘机过程中的各类问题，包括但不限于安检流程、行李规定、
    登机手续、值机办理、航班延误处理等常见乘机知识。
    
    Args:
        user_question: 用户提出的乘机相关问题，应当是一个完整的问句，例如"液体可以带多少上飞机？"
                 "行李超重怎么办？"或"如何办理值机手续？"等
    Examples:
        >>> airport_knowledge_query("安检需要注意什么？")
        "乘客需要通过安检门，随身行李需要通过X光机检查。液体不超过100ml，需要放在透明袋中。"
    """
    # 创建事件循环以执行异步操作
    loop = asyncio.get_event_loop()
    
    # 执行异步检索函数
    results = loop.run_until_complete(
        retrieve_from_kb(question=user_question, dataset_name="济南机场知识库")
    )
    format_doc = []
    if len(results) > 0:
        for i,doc in enumerate(results):
            format_doc.append(f"第{i+1}个与用户问题相关的文档内容如下：\n{doc['content']}")
        text = "\n\n".join(format_doc[:3])
    else:
        text = "抱歉，在知识库中没有找到与问题相关的信息。"

    return Command(
            update={
                'messages':[ToolMessage(content=text,tool_call_id=tool_call_id)],
                'user_question': user_question,
                'similarity_context':results,

            },
        )






