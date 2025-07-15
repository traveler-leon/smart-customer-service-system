import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from datetime import datetime
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.config import get_store
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from agents.airport_service.state import BusinessServiceState
from agents.airport_service.tools.business import (
    wheelchair_rental_tool
    ,business_handler
)
from agents.airport_service.core import filter_messages_for_llm, max_msg_len,structed_model
from common.logging import get_logger
# 获取业务办理节点专用日志记录器
logger = get_logger("agents.main-nodes.business")

# 用于主路由节点
router_bussiness_tools = ToolNode([
    business_handler
])
# 业务办理子智能体的工具列表
business_tools = ToolNode([
    wheelchair_rental_tool
])

# 业务办理子智能体的提示词
business_agent_prompt = """你是深圳宝安国际机场的业务办理专员。你的职责是帮助旅客办理各种机场相关业务。
<服务范围>
3. 特殊服务：轮椅租赁、无人陪伴儿童、特殊餐食申请等
</服务范围>
<工作原则>
1. 保持专业、友好、耐心的服务态度
2. 仔细理解用户需求，选择合适的工具处理
3. 如需更多信息，主动询问用户
4. 当前时间是: {time}，如果用户询问涉及时间的信息请考虑此因素。
</工作原则>
请根据用户的业务办理需求，选择合适的工具并提供专业的服务指导。""".format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))



def message_filter(state: BusinessServiceState, config: RunnableConfig):
    new_messages = filter_messages_for_llm(state, max_msg_len)
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    return {
        "llm_input_messages": messages
    }

# 创建业务办理子智能体
business_agent = create_react_agent(
    model=structed_model,
    tools=business_tools,
    prompt=business_agent_prompt,
    pre_model_hook=message_filter,
    state_schema=BusinessServiceState,
    name="业务办理子智能体"
)
