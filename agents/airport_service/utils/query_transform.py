from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from ..nodes import base_model


async def rewrite_query(original_query):
    """
    将用户提出的原始问题重写为更适合机场客服知识库检索的问题。

    参数：
        original_query (str): 用户原始提问

    返回：
        str: 改写后的问题（适合检索）
    """
    # 带背景信息的 Prompt 模板
    query_rewrite_prompt = PromptTemplate.from_template("""
    你是一个智能客服助手，服务于中国民航机场系统。你的任务是将用户提出的模糊、简短或不完整的问题，
    改写为更具体、更完整的表达，以便于在机场客服知识库中进行准确检索。

    背景信息：
    - 用户通常是在准备乘坐飞机。
    - 用户的问题主要与以下主题相关：安检规定、随身携带物品、托运行李、违禁物品、登机流程、证件要求、航班变动、值机时间等。
    - 用户的问题经常比较模糊或口语化，例如：
    - “水能带吗？”
    - “打火机能过安检吗？”
    - “改签怎么弄？”
    - “飞机上能用充电宝吗？”

    你的任务是：
    1. 不要回答问题，只改写问题。
    2. 改写后的问题必须更加具体、清晰，适合用来检索民航机场相关的知识库内容。
    3. 语言表达要正式、完整，尽可能包含“飞机”、“安检”、“机场”等关键词，便于检索系统理解意图。
    4. 最终只输出改写后的问题，不要输出任何其他内容，包括（改写后的问题的前缀）

    示例：
    原始问题：水能带吗？
    改写后问题：乘坐飞机时，旅客是否可以随身携带瓶装水通过安检？

    原始问题：能带刀吗？
    改写后问题：乘坐国内航班时，旅客是否可以携带刀具？哪些类型的刀具允许托运或禁止携带？

    请改写以下问题：

    原始问题：{original_query}
    改写后问题：
    """)
    query_rewriter = query_rewrite_prompt | base_model

    try:

        response = await query_rewriter.ainvoke({"original_query": original_query})
        return response.content.strip()
    except Exception as e:
        print(f"[错误] 问题重写失败：{e}")
        return ''  # 出错时返回原问题



# 封装为函数
async def generate_step_back_query(original_query):
    """
    针对原始问题生成一个更泛化、更通用的回退型问题，用于补充背景检索。

    参数：
        original_query (str): 用户原始提问

    返回：
        str: 回退型问题（用于补充语义背景）
    """
    # 问题回退的提示词模板（中文+背景）
    step_back_prompt = PromptTemplate.from_template("""
    你是一个服务于中国民航机场智能客服系统的AI助手。
    请根据你对民航安检规定的理解，对用户问题中的具体物品或品牌进行分析，识别出其**在航空安检角度下的重要属性**（如是否为液体、是否为锐器、是否含锂电池等），并据此将原问题泛化为一个更具代表性的、覆盖该类属性的检索问题。
    你的目标是帮助系统准确命中与该属性相关的知识库规定。

    要求：
    1. 不要生成无关的背景问题。
    2. 要结合你的领域知识，准确判断物品的属性类别。
    3. 回退问题要表达清晰完整，符合机场安检问答逻辑。
    4. 最终只输出回退后的问题，不要输出任何其他内容，包括（回退后的问题的前缀）

    示例：
    原始问题：我能带雅诗兰黛吗？
    回退后的问题：乘坐飞机是否允许携带液体化妆品？

    原始问题：可以带菜刀吗？
    回退后的问题：乘坐国内航班是否允许携带或托运锐器类物品？

    原始问题：我可以带香水上飞机吗？
    回退后的问题：乘坐飞机时液体物品是否有限制？

    请根据下列问题识别物品属性，并生成相应的属性泛化回退问题：

    原始问题：{original_query}
    回退后的问题：
    """)
    step_back_chain = step_back_prompt | base_model

    try:
        response = await step_back_chain.ainvoke({"original_query": original_query})
        return response.content.strip()
    except Exception as e:
        print(f"[错误] 回退问题生成失败：{e}")
        return ''  # 出错时返回原问题

