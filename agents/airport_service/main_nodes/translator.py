"""
多语言支持节点
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from agents.airport_service.state import AirportMainServiceState, TranslationResult
from trustcall import create_extractor
from langchain_core.messages import RemoveMessage,HumanMessage,AIMessage
from agents.airport_service.core import structed_model
from common.logging import get_logger

# 获取翻译节点专用日志记录器
logger = get_logger("agents.main-nodes.translator")
bound = create_extractor(structed_model,tools=[TranslationResult])

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

async def translate_input(state: AirportMainServiceState, config: RunnableConfig):
    """
    翻译输入节点
    
    Args:
        state: 当前状态对象
        config: 可运行配置
    """
    Is_translate = config["configurable"].get("Is_translate",False)
    user_query = config["configurable"].get("user_query", "")
    logger.info(f"进入输入翻译子智能体 - 是否需要翻译: {Is_translate}")

    if not Is_translate:
        return {"user_query":user_query}
    else:
        input_parser = PydanticOutputParser(pydantic_object=TranslationResult)
        input_translation_prompt = PromptTemplate(
            template=(
                "你是一个高精度的语言检测和翻译助手。\n"
                "请根据用户输入，检测语言类型，保留用户的原始内容，并将内容翻译成中文。\n"
                "如果用户输入已经是中文，也需要翻译，只是保持语言类型为中文，翻译后结果也是中文就可以。\n"
                "{format_instructions}\n"
                "用户输入：{user_input}"
            ),
            input_variables=["user_input"],
            partial_variables={"format_instructions": input_parser.get_format_instructions()},
        )
        chain = input_translation_prompt | bound

        last_msg = state["messages"][-1]
        del_msg = remove_message(state,del_nb=2)

        try:
            result = await chain.ainvoke({"user_input": user_query})
            language = result["responses"][0].language
            original_text = result["responses"][0].original_text
            translated_text = result["responses"][0].translated_text
            return {"user_query":translated_text,"translator_result": TranslationResult(language=language, original_text=original_text, translated_text=translated_text), "messages": del_msg + [HumanMessage(name=last_msg.name,content=translated_text)]}
        except Exception as e:
            logger.error(f"！！！输入翻译异常: {e}")
            return {"user_query":user_query,"translator_result": TranslationResult(language="中文", original_text=user_query, translated_text=user_query), "messages": del_msg + [HumanMessage(name =last_msg.name,content=user_query)]}





async def translate_output(state: AirportMainServiceState, config: RunnableConfig):
    """
    翻译输出节点
    
    Args:
        state: 当前状态对象
        config: 可运行配置
    """
    Is_translate = config["configurable"].get("Is_translate",False)
    logger.info(f"进入输出翻译子智能体 - 是否需要翻译: {Is_translate}")

    if not Is_translate:
        return {"user_query":None}
    else:
        output_translation_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """你是一个高精度的多语言翻译助手，负责将中文翻译成目标语言 {language}。  
                    <instructions>  
                    1. **语言判断**  
                    - 如果目标语言是中文，则直接返回原文，不做翻译；  
                    - 若为其他语言，则进行高质量翻译，确保表达自然流畅。  

                    2. **注意事项**  
                    - 翻译须保持原文意思、语气、风格一致；  
                    - 专业术语必须准确；  
                    - 除了翻译结果，不要输出任何多余内容。
                 </instructions>  

                    <examples>  
                    - **中文 → 英文**  
                    输入：  
                    > 您好，我需要办理登机手续。  
                    输出：  
                    > Hello, I need to check in for my flight.  

                    - **中文 → 法文**  
                    输入：  
                    > 您好，候机室在哪里？  
                    输出：  
                    > Bonjour, où se trouve la salle d’attente ?  

                    - **中文 → 日文**  
                    输入：  
                    > 我想确认一下航班延误的情况。  
                    输出：  
                    > フライトの遅延について確認したいのですが。  

                    - **中文 → 中文**  
                    输入：  
                    > 我想确认一下航班延误的情况。  
                    输出：  
                    > 我想确认一下航班延误的情况。  
                    </examples>

                """
            ),
            ("human", "-** 中文 -> {language} **-\n输入:\n>{user_input}\n输出:\n>")
        ])

        try:
            translator_result = state.get("translator_result")
            language = translator_result.language if translator_result else "中文"
            chain = output_translation_prompt | structed_model
            ai_msg = state["messages"][-1]
            result = await chain.ainvoke({"user_input": ai_msg.content,"language":language})
            result.name = "翻译助手"
            return { "messages": [result]}
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return {"messages": [AIMessage(name = "翻译助手",content=ai_msg.content)]}