import sys
import os

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import asyncio
from langchain_core.tools import tool
from text2kb.retrieval import retrieve_from_kb
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from typing_extensions import Annotated
from langchain_core.messages import ToolMessage
from config.utils import config_manager

_text2kb_config = config_manager.get_text2kb_config()
KB_ADDRESS = _text2kb_config.get("kb_address")
KB_API_KEY = _text2kb_config.get("kb_api_key")

@tool
async def airport_knowledge_query(user_question:str,tool_call_id:Annotated[str,InjectedToolCallId]) -> str:
    """
    用于检索济南机场相关知识的工具，帮助解答乘客关于乘机流程的问题。
    
    此工具连接到专门的"济南机场知识库"，能够回答用户关于机场各个服务类别的详细问题。包括：
    1. 安全检查服务：安检区域、安检须知
    2. 出行服务：爱心服务、服务电话、贵宾室服务、头等舱休息室服务、晚到服务
    3. 行李服务：托运须知、行李打包、行李寄存、行李赔偿、行李逾重须知
    4. 值机服务：团队预约、值机区域、自助办理、自助值机
    5. 中转服务
    
    当用户询问任何与济南机场服务相关的问题时，应首选此工具。
    如果用户问题涉及上述服务类别的相关咨询，或明确询问机场规定和服务流程，都应该调用此工具。
    
    Args:
        user_question: 用户提出的机场服务相关问题，例如："液体可以带多少上飞机？"、
                      "行李超重怎么办？"或"济南机场有爱心服务吗？"
    
    Examples:
        >>> airport_knowledge_query("安检需要注意什么？")
        "乘客需要通过安检门，随身行李需要通过X光机检查。液体不超过100ml，需要放在透明袋中。"
    """
    print("进入知识查询工具")
    results = await retrieve_from_kb(question=user_question, dataset_name="济南机场知识库",address=KB_ADDRESS,api_key=KB_API_KEY,similarity_threshold=0.01,top_k=5,key_words=True)
    format_doc = []
    if len(results) > 0:
        for i,doc in enumerate(results):
            format_doc.append(f"第{i+1}个与用户问题相关的文档内容如下：\n{doc['content']}")
        text = "\n\n".join(format_doc[:3])
    else:
        text = "抱歉，在知识库中没有找到与问题相关的信息。"
    return Command(
            update={
                'messages':[ToolMessage(content="知识检索结束",tool_call_id=tool_call_id)],
                'current_query': user_question,
                'kb_context_docs':text,
            },
        )






if __name__ == "__main__":
    pass
    # 测试时提供一个虚拟的tool_call_id
    # print(asyncio.run(airport_knowledge_query.ainvoke({"user_question": "安检需要注意什么？", "tool_call_id": "test_call_id"})))
    # print(asyncio.run(airport_knowledge_query.ainvoke({"user_question": "坐飞机可以带刀具吗？", "tool_call_id": "test_call_id"})))
