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
from langgraph.store.base import BaseStore
from langchain_core.messages import AIMessage
from langgraph.types import Command
from langgraph.config import get_store
from agents.airport_service.tools import airport_knowledge_query
from agents.airport_service.core import filter_messages_for_llm, max_msg_len, KB_SIMILARITY_THRESHOLD,content_model
from datetime import datetime
from common.logging import get_logger

# 获取机场知识节点专用日志记录器
logger = get_logger("agents.main-nodes.airport")
airport_tool_node = ToolNode([airport_knowledge_query])

async def provide_airport_knowledge(state: AirportMainServiceState, config: RunnableConfig):
    logger.info("进入机场知识问答子智能体:")
    kb_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是深圳宝安国际机场 (SZX) 的虚拟客服助手，名为"宝安小飞"。
            你的主要职责是帮助用户解答关于深圳宝安国际机场旅客须知问题，例如安全检查、出行服务、行李服务、值机服务、中转服务等。

            用户希望获得清晰、准确且简洁的回答。

            请在回答时保持礼貌和专业。
            - 当用户问题指向的规定或信息在 <context> 中有多种细分情况或条件时，并且用户问题本身没有明确具体属于哪种情况，你必须主动引导用户明确问题细节，而不是直接罗列所有可能性。
            - 只有当问题完全细化且能与具体规定匹配时，才提供最终答案。
            """
        ),
        ("placeholder", "{messages}"),
        ("human", 
        """
            请使用下面 <context> XML 标签内提供的信息来帮助组织你的回答。
            <context> 
            {context}
            </context> 
            请遵循下面 <instructions> 标签内的指示来回答问题。
            <instructions> 
                - **步骤 1: 初步判断相关性与匹配类型** - 首先，判断 <context> 是否包含与用户 <question> 相关的信息。
                - 如果完全不相关，请直接跳转到步骤 5，使用拒绝回答短语。
                - 如果相关，判断属于以下哪种情况：
                a) 直接匹配：用户询问的问题在 <context> 中有直接对应的规定
                b) 类别匹配：用户询问具体物品，但 <context> 中只有该物品所属大类的规定
                c) 需要澄清：<context> 中的相关信息根据不同条件有差异，而用户问题未明确这些条件

                - **步骤 2: 类别匹配处理**
                - 如果用户询问的是具体物品（如"雅诗兰黛"、"改锥"、"iPhone充电器"），但 <context> 中只有大类规定（如"液体"、"锐器"、"电子设备"），需要进行类别匹配：
                - 根据常识判断该具体物品属于哪个大类，然后应用相应的大类规定
                - 如果该物品明确属于某个大类且规定清晰，直接给出答案
                - 如果该物品可能属于多个大类或无法确定归类，则跳转到步骤 3 进行澄清
                - 例如：用户问"雅诗兰黛能带吗"，而 <context> 有液体携带规定，应询问"请问您的雅诗兰黛产品是多少毫升的？"

                - **步骤 3: 需要澄清**
                - 如果 <context> 包含相关信息，但这些信息根据不同条件有差异的，而用户问题未明确这些条件（包括步骤2中无法确定归类的情况），必须向用户提出一个澄清问题。
                - 提出一个简洁明确的问题，引导用户提供更具体的信息。例如："请问您指的是哪种类型的刀具？" 或 "您携带的液体是多少毫升？"
                - 此时，不要给出任何答案或解释，只提出澄清问题。
                - 如果需要多轮澄清，每次只问一个问题，直到问题完全细化。

                - **步骤 4: 直接回答**
                - 当用户问题已足够具体，与 <context> 中的某一具体规定完全匹配时，或通过类别匹配能明确给出答案时，首先给出明确的结论，然后提供一个解决方案。
                - 回答结构应该包含：
                1) 明确的结论（如"可以携带"、"不可以携带"、"可以随身携带但不能托运"等）
                - 不要引用 <context> 或提及信息来源，直接陈述结论或解决方法

                - **步骤 5: 无法回答（兜底）**
                - 如果 <context> 完全不相关或遇到其他无法处理的情况，使用拒绝回答短语。
        
                - **通用规则:**
                - 除了澄清问题外，不要提出其他追问。
                - 回答中不应提及 <context> 或信息来源。
                - 永远以第二人称回答用户的问题。
                - 当前时间是: {time}，如果用户询问涉及时间的信息请考虑此因素。
                - 回答问题时，要充分考虑历史对话信息。
                - 最终的回答内容的语言必须为：{language}。

            </instructions> 
            下面是实际的一些例子：
            <examples>
                <example1>
                    <question>坐飞机可以带刀吗？</question>
                    <context>
                        命题4：禁止携带各类管制器具\r\n-禁止携带各类管制器具\r\n能够造成人身伤害或者对航空安全和运输秩序构成较大危害的管制器具，
                        例如符合特定描述的管制刀具（如匕首、三棱刮刀 、带有自锁装置的弹簧刀）、军警械具（如警棍、警用电击器、手铐、催泪喷射器）以及其他国家规定的管制器具（如弩），
                        均属于民航旅客禁止随身携带和托运的物品。\r\n\r\n\n\n第2个与用户问题相关的文档内容如下：
                        \n 命题2：禁止随身携带但可作为行李托运的锐器\r\n-禁止随身携带但可作为行李托运的锐器\r\n带有锋利边缘或锐利尖端、强度足以造成人身严重伤害的金属或其他材料制成的锐器，
                        禁止民航旅客随身携带但可以作为行李托运。此类物品主要包括：刀刃长度大于6厘米的日用刀具（如菜刀、水果刀、剪刀、美工刀、裁纸刀），刀刃长度不限的专业刀具（如手术刀、屠宰刀、雕刻刀、刨刀、铣刀），
                        以及用作武术文艺表演的刀、矛、剑、戟等。\r\n\r\n\n\n第3个与用户问题相关的文档内容如下：
                        \n 命题4：禁止随身携带但可作为行李托运的其他特定工具和物品\r\n-禁止随身携带但可作 为行李托运的其他特定工具和物品\r\n其他能够造成人身伤害或对航空安全和运输秩序构成较大危害，
                        且禁止民航旅客随身携带但可以作为行李托运的物品主要包括：特定工具（如钻机、凿、锥、锯、螺栓枪、射钉枪、螺丝刀、撬棍、锤、钳、焊枪、扳手、斧头、短柄小斧、游标卡尺、冰镐、碎冰锥）以及其他物品（如飞镖、弹弓、弓箭、蜂鸣自卫器，
                        和不在国家规定管制范围内的电击器、梅斯气体、催泪瓦斯、胡椒辣椒喷剂、酸性喷雾剂、驱除动物喷剂等）。\r\n\r\n\n\n第4个与用户问题相关的文档内容如下：\n 
                    </context> 
                    你的输出：请问您带的是什么刀？
                </example1>
                <example2>
                    <question>雅诗兰黛小棕瓶能带上飞机吗？</question>
                    <context>
                        第1个与用户问题相关的文档内容如下：\n 命题1：液体、胶状及喷雾类物品携带规定概述\r\n旅客随身携带液体、胶状及喷雾类物品乘坐民航飞机，必须严格遵守相关规定。
                        这些规定涵盖了容器容量限制、包装要求以及特殊情况的处理办法。\r\n\r\n\n\n第2个与用户问题相关的文档内容如下：\n 命题2：小容量液体容器的携带规定\r\n-小容量液体容器的携带规定\r\n旅客可以携带单体容器容量不超过100毫升的液体、胶状及喷雾类物品乘机。
                        需要注意的是，这里指的是容器的容量，而非物品的实际体积。即使容器内的液体未装满，只要容器本身的容量超过100毫升，就不符合随身携带的要求。\r\n\r\n\n\n第3个与用户问题相关的文档内容如下：
                        \n 命题3：液体物品的透明袋装要求\r\n-液体物品的透明袋装要求\r\n所有符合随身携带要求的液体、胶状及喷雾类物品，都必须放置在单独的透明塑料袋内。
                        每名旅客只能携带一个这样的透明袋，且该透明袋的容量不得超过1升。\r\n\r\n\n\n第4个与用户问题相关的文档内容如下：
                    </context> 
                    你的输出：请问您的雅诗兰黛小棕瓶是多少毫升的？
                </example2>
                <example3>
                    <question>螺丝刀能带上飞机吗？</question>
                    <context>
                        第1个与用户问题相关的文档内容如下：\n 命题4：禁止随身携带但可作为行李托运的其他特定工具和物品\r\n-禁止随身携带但可作 为行李托运的其他特定工具和物品\r\n其他能够造成人身伤害或对航空安全和运输秩序构成较大危害，
                        且禁止民航旅客随身携带但可以作为行李托运的物品主要包括：特定工具（如钻机、凿、锥、锯、螺栓枪、射钉枪、螺丝刀、撬棍、锤、钳、焊枪、扳手、斧头、短柄小斧、游标卡尺、冰镐、碎冰锥）以及其他物品（如飞镖、弹弓、弓箭、蜂鸣自卫器，
                        和不在国家规定管制范围内的电击器、梅斯气体、催泪瓦斯、胡椒辣椒喷剂、酸性喷雾剂、驱除动物喷剂等）。\r\n\r\n\n\n第2个与用户问题相关的文档内容如下：
                    </context> 
                    你的输出：螺丝刀不可以随身携带，但可以托运。
                </example3>
                
            </examples>

            这是当前用户的问题: <question>{user_query}</question>
    """)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("进入机场知识子智能体处理阶段")
    user_query = state.get("user_query", "") if state.get("user_query", "") else config["configurable"].get("user_query", "")
    context_docs = state.get("kb_context_docs", "")
    context_docs_maxscore = state.get("kb_context_docs_maxscore", 0.0)
    translator_result = state.get("translator_result")
    language = translator_result.language if translator_result else "中文"
    # if "抱歉" in context_docs or not context_docs or context_docs_maxscore < KB_SIMILARITY_THRESHOLD:
    #     return Command(
    #         goto="chitchat_node",
    #         update={
    #             "kb_context_docs":"",
    #             "kb_context_docs_maxscore":0.0
    #         }
    #     )

    new_messages = filter_messages_for_llm(state, max_msg_len)
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    kb_chain = kb_prompt | content_model
    res = await kb_chain.ainvoke({ "user_query": user_query,"context": context_docs,"messages":messages,"language":language})
    res.name = "机场知识问答子智能体"
    # profile_executor.submit({"messages":state["messages"]+[res]},after_seconds=memery_delay)
    # episode_executor.submit({"messages":state["messages"]+[res]},after_seconds=memery_delay)
    return {"messages":[res],"kb_context_docs":" "}





