"""
机场知识节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from ..state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage
from agents.airport_service.tools import airport_knowledge_query
from agents.airport_service.core import filter_messages_for_agent, max_msg_len, KB_SIMILARITY_THRESHOLD,content_model
from agents.airport_service.context_engineering.prompts import main_graph_prompts
from agents.airport_service.context_engineering.agent_memory import memory_enabled_agent
from datetime import datetime
from common.logging import get_logger

logger = get_logger("agents.main-nodes.airport")
airport_tool_node = ToolNode([airport_knowledge_query])


@memory_enabled_agent(application_id="机场主智能客服", agent_id="机场知识问答子智能体")
async def provide_airport_knowledge(state: AirportMainServiceState, config: RunnableConfig):
    logger.info("进入机场知识问答子智能体:")
    
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    
    # 准备上下文信息
    context_docs = state.get("kb_context_docs", "")
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"
    conversation_memories = state.get("conversation_memories", "")
    
    kb_prompt = ChatPromptTemplate.from_messages([
        ("system", main_graph_prompts.AIRPORT_KNOWLEDGE_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
        ("human", main_graph_prompts.AIRPORT_KNOWLEDGE_HUMAN_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    logger.info("进入机场知识子智能体处理阶段")
    # if "抱歉" in context_docs or not context_docs or context_docs_maxscore < KB_SIMILARITY_THRESHOLD:
    #     return Command(
    #         goto="chitchat_node",
    #         update={
    #             "kb_context_docs":"",
    #             "kb_context_docs_maxscore":0.0
    #         }
    #     )

    new_messages = filter_messages_for_agent(state, max_msg_len, "机场知识问答子智能体")
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    
    kb_chain = kb_prompt | content_model
    res = await kb_chain.ainvoke({ 
        "user_query": user_query,
        "context": context_docs,
        "messages":messages,
        "language":language
    })
    res.name = "机场知识问答子智能体"
    return {"messages":[res],"kb_context_docs":" "}





