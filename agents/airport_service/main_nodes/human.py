
"""
多语言支持节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from langchain_core.runnables import RunnableConfig
from agents.airport_service.state import AirportMainServiceState
from langchain_core.messages import AIMessage
from common.logging import get_logger


logger = get_logger("agents.main-nodes.human")
async def transfer_to_human(state: AirportMainServiceState, config: RunnableConfig):
    """
    转人工节点
    """
    logger.info("进入转人工节点")
    emotion_result = state.get("emotion_result", {})
    return {"messages": [AIMessage(content=emotion_result.get("reason", "已转人工"))]}


def route_to_next(state: AirportMainServiceState):
    # 获取最新消息
    emotion_result = state.get("emotion_result", {})
    if emotion_result.get("is_negative", False):
        return "transfer_to_human"
    else:
        return "images_thinking_node"