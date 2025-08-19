from langchain_core.prompts import PromptTemplate
from ..models import structed_model as model
from common.logging import get_logger
from agents.airport_service.context_engineering.prompts import query_transform_prompts

logger = get_logger("agents.utils.query_transform")


async def rewrite_query(original_query):
    """
    将用户提出的原始问题重写为更适合机场客服知识库检索的问题。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 改写后的问题（适合检索）
    """
    logger.info(f"开始重写查询: {original_query}")
    query_rewrite_prompt = PromptTemplate.from_template(query_transform_prompts.QUERY_REWRITE_PROMPT)
    query_rewriter = query_rewrite_prompt | model

    try:

        response = await query_rewriter.ainvoke({"original_query": original_query})
        rewritten_query = response.content.strip()
        logger.info(f"查询重写成功: {rewritten_query}")
        return rewritten_query
    except Exception as e:
        logger.error(f"问题重写失败: {e}")
        return '' 



async def generate_step_back_query(original_query):
    """
    针对原始问题生成一个更泛化、更通用的回退型问题，用于补充背景检索。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 回退型问题（用于补充语义背景）
    """
    logger.info(f"开始生成回退查询: {original_query}")
    step_back_prompt = PromptTemplate.from_template(query_transform_prompts.STEP_BACK_PROMPT)
    step_back_chain = step_back_prompt | model

    try:
        response = await step_back_chain.ainvoke({"original_query": original_query})
        step_back_query = response.content.strip()
        logger.info(f"回退查询生成成功: {step_back_query}")
        return step_back_query
    except Exception as e:
        logger.error(f"回退问题生成失败: {e}")
        return '' 