"""
路由节点
"""
from ..state import AirportMainServiceState
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from . import filter_messages_for_llm
from . import max_msg_len
from langchain_core.messages import AIMessage,RemoveMessage,HumanMessage
from . import image_model
from common.logging import get_logger

# 获取路由节点专用日志记录器
logger = get_logger("agents.nodes.images_thinking")


def remove_message(state:AirportMainServiceState,del_nb = 2):
    """
    删除尾部的几条消息
    """
    try:
        if len(state["messages"]) <= del_nb:
            return []
        else:
            del_msg = state["messages"][-del_nb:]
            return [RemoveMessage(id=msg.id) for msg in del_msg]
    except Exception as e:
        print(f"删除消息失败: {e}")
        return []


async def images_thinking(state: AirportMainServiceState, config: RunnableConfig):
    user_query = config["configurable"].get("user_query", "")
    image_data = config["configurable"].get("image_data", None)
    logger.info(f"进入图像理解子智能体：{user_query}")
    if not image_data:
        logger.info("图片数据不存在：无需处理")
        return state
    image_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是民航机场的一名智能客服系统，你擅长理解用户想问的问题并结合图片信息进行分析。

            <background_info>
            - 用户通常是在准备乘坐飞机，或者在机场遇到问题需要帮助。
            - 用户的问题主要与以下主题相关：安检规定、随身携带物品、托运行李、违禁物品、登机流程、证件要求、航班变动、值机时间等。
            - 用户经常会上传图片来询问某个物品是否可以带上飞机，或者询问机场设施的使用方法。
            - 用户的问题经常比较模糊或口语化，需要结合图片信息来理解真实意图。
            </background_info>

            <task>
            1. 仔细分析用户上传的图片内容，识别图片中的物品、文字、场景等关键信息。
            2. 结合用户的原始问题和图片信息，理解用户的真实意图。
            3. 生成一个新的、更加清晰和具体的问题，这个问题应该更适合后续的知识库检索。
            4. 新问题应该包含从图片中识别出的具体物品名称、属性或场景信息。
            5. 语言表达要正式、完整，尽可能包含"飞机"、"安检"、"机场"等关键词，便于检索系统理解意图。
            6. 最终只输出新生成的问题，不要输出任何其他内容。
            7. 如果图片内容与民航机场服务无关，请礼貌地引导用户询问相关问题。
            </task>

            <examples>
            <example1>
            用户问题：这个能带吗？
            图片内容：一瓶洗发水,容量100ml
            生成问题：我有一瓶洗发水，容量100ml，能带上飞机吗？
            </example1>

            <example2>
            用户问题：怎么用？
            图片内容：机场自助值机设备
            生成问题：如何使用机场自助值机设备进行值机操作？
            </example2>

            <example3>
            用户问题：能过安检吗？
            图片内容：一个充电宝,容量100mA
            生成问题：容量100mA的充电宝是否可以随身携带通过机场安检？
            </example3>
            </examples>
            """
        ),
        ("placeholder", "{messages}"),
        ("human",[
            {
            "type":"image_url",
            "image_url": {"url":"data:image/{image_type};base64,{image_data}"},
        },
        {
        "type":"text",
        "text": "用户初始问题：{user_query}。请你结合图片信息和用户原始问题，重新生成一个新的问题。",
        }   
        ])
    ])
    
    chain = image_assistant_prompt | image_model
    new_messages = filter_messages_for_llm(state, max_msg_len)
    messages = new_messages if len(new_messages) > 0 else [AIMessage(content="暂无对话历史")]
    # 调用链获取响应
    image_type = image_data['content_type'].split('/')[-1]
    response = await chain.ainvoke({"messages": messages,"image_type":image_type,"image_data":image_data['data'],"user_query":user_query})
    logger.info(f"图片思考结果: {response.content}")
    del_msg = remove_message(state,del_nb=1)
    return {"messages":del_msg + [HumanMessage(content=response.content)],"user_query":response.content}
