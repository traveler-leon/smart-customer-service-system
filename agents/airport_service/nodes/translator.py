"""
多语言支持节点
"""
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from ..state import AirportMainServiceState, TranslationResult
from trustcall import create_extractor
from langchain_core.messages import RemoveMessage,HumanMessage,AIMessage
from . import base_model
from common.logging import get_logger

# 获取翻译节点专用日志记录器
logger = get_logger("agents.nodes.translator")

# 输入翻译Prompt

bound = create_extractor(base_model,tools=[TranslationResult])

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



async def translate_input(state: AirportMainServiceState, config: RunnableConfig, store: BaseStore):
    """
    翻译输入节点
    
    Args:
        state: 当前状态对象
        config: 可运行配置
    """
    Is_translate = config["configurable"].get("Is_translate",False)
    logger.info(f"进入输入翻译节点 - 是否需要翻译: {Is_translate}")

    if not Is_translate:
        logger.info("输入无需翻译，直接返回")
        return state
    else:
        logger.info("输入需要翻译，开始处理")
        input_parser = PydanticOutputParser(pydantic_object=TranslationResult)
        input_translation_prompt = PromptTemplate(
            template=(
                "你是一个高精度的语言检测和翻译助手。\n"
                "请根据用户输入，检测语言类型，保留用户的原始内容，并将非中文内容翻译成中文。\n"
                "如果用户输入已经是中文，只需标记语言为'中文'并保持内容不变。\n"
                "{format_instructions}\n"
                "用户输入：{user_input}"
            ),
            input_variables=["user_input"],
            partial_variables={"format_instructions": input_parser.get_format_instructions()},
        )
        chain = input_translation_prompt | bound

        last_msg = state["messages"][-1]
        user_input = last_msg.content
        del_msg = remove_message(state,del_nb=2)

        try:
            result = await chain.ainvoke({"user_input": user_input})
            language = result["responses"][0].language
            original_text = result["responses"][0].original_text
            translated_text = result["responses"][0].translated_text

            return {"translator_result": TranslationResult(language=language, original_text=original_text, translated_text=translated_text), "messages": del_msg + [HumanMessage(name=last_msg.name,content=translated_text)]}
        except Exception as e:
            print("进入异常")
            return {"translator_result": TranslationResult(language="Chinese", original_text=user_input, translated_text=user_input), "messages": del_msg + [HumanMessage(name =last_msg.name,content=user_input)]}





async def translate_output(state: AirportMainServiceState, config: RunnableConfig, store: BaseStore):
    """
    翻译输出节点
    
    Args:
        state: 当前状态对象
        config: 可运行配置
    """
    Is_translate = config["configurable"].get("Is_translate",False)
    logger.info(f"进入输出翻译节点 - 是否需要翻译: {Is_translate}")

    if not Is_translate:
        logger.info("输出无需翻译，直接返回")
        return state
    else:
        logger.info("输出需要翻译，开始处理")
        output_translation_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """你是一个高精度的多语言翻译助手，负责将中文翻译为语言类型为：{language}的语言。

                    <instructions>
                    - **步骤 1: 内容处理** - 如果内容已经是{language}，保持原文不变；如果是其他语言，进行高质量翻译
                
                遵循以下规则：
                - 保持翻译的准确性和自然流畅
                - 保留原文的语气和风格
                - 确保专业术语的准确翻译
                - 对于中文的输入，保持内容不变
                - 除了翻译，不要输出其他内容
                </instructions>
                下面是一些翻译的例子：
                <examples>
                    <example1>
                        <input>
                        您好，我需要办理登机手续。
                        </input>
                        <output>
                        Hello, I need to check in for my flight.
                        </output>
                    </example1>
                    <example2>
                        <input>
                        您好，候机室在哪里？
                        </input>
                        <output>
                        Bonjour, où se trouve la salle d'attente?
                        </output>
                    </example2>
                    <example3>
                        <input>
                        我想确认一下航班延误的情况。
                        </input>
                        <output>
                        フライトの遅延について確認したいのですが。
                        </output>
                    </example3>
                    </example3>
                </examples>
                """
            ),
            ("human", "请翻译以下内容：\n{user_input}")
        ])

        try:
            language = state["translator_result"].language
            logger.info("语言类型为：",language)
            chain = output_translation_prompt | base_model
            user_input = state["messages"][-1].content
            logger.info("输出prompt",output_translation_prompt.invoke({"user_input": user_input,"language":language}))

            result = await chain.ainvoke({"user_input": user_input,"language":language})
            return { "messages": [AIMessage(role = "中文翻译助手",content=result.content)]}
        except Exception as e:
            print(f"翻译失败: {e}")
