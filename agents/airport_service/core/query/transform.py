from langchain_core.prompts import PromptTemplate,ChatPromptTemplate
from ..models import structed_model as model
from typing import List
from langchain_core.messages import AnyMessage
from datetime import datetime
from common.logging import get_logger
from agents.airport_service.context_engineering.prompts import query_transform_prompts

logger = get_logger("agents.utils.query_transform")



async def flight_rewrite_query(original_query:str,messages:List[AnyMessage]):
    """
    将用户提出的原始问题重写为更适合机场客服知识库检索的问题。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 改写后的问题（适合检索）
    """
    logger.info(f"开始重写查询: {original_query}")
    query_rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", query_transform_prompts.FLIGHT_QUERY_REWRITE_SYSTEM_PROMPT),
        ("human", query_transform_prompts.FLIGHT_QUERY_REWRITE_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    query_rewriter = query_rewrite_prompt | model

    try:

        response = await query_rewriter.ainvoke({"original_query": original_query,"messages": messages})
        rewritten_query = response.content.strip()
        logger.info(f"查询重写成功: {rewritten_query}")
        return rewritten_query
    except Exception as e:
        logger.error(f"问题重写失败: {e}")
        return original_query 

async def rewrite_query(original_query,messages:List[AnyMessage]):
    """
    将用户提出的原始问题重写为更适合机场客服知识库检索的问题。

    Args:
        original_query (str): 用户原始提问
        messages (List[AnyMessage]): 对话历史消息

    Returns:
        str: 改写后的问题（适合检索）
    """
    logger.info(f"开始重写查询: {original_query}")
    query_rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", query_transform_prompts.QUERY_REWRITE_SYSTEM_PROMPT),
        ("human", query_transform_prompts.QUERY_REWRITE_PROMPT)
    ])
    query_rewriter = query_rewrite_prompt | model

    try:

        response = await query_rewriter.ainvoke({"original_query": original_query,"messages": messages})
        rewritten_query = response.content.strip()
        return rewritten_query
    except Exception as e:
        logger.error(f"问题重写失败: {e}")
        return original_query



async def generate_step_back_query(original_query, messages:List[AnyMessage]=None):
    """
    针对原始问题生成一个更泛化、更通用的回退型问题，用于补充背景检索。

    Args:
        original_query (str): 用户原始提问
        messages (List[AnyMessage]): 对话历史消息

    Returns:
        str: 回退型问题（用于补充语义背景）
    """
    logger.info(f"开始生成回退查询: {original_query}")
    if messages:
        step_back_prompt = ChatPromptTemplate.from_messages([
            ("system", query_transform_prompts.STEP_BACK_QUERY_SYSTEM_PROMPT),
            ("human", query_transform_prompts.STEP_BACK_QUERY_PROMPT)
        ])
    else:
        step_back_prompt = PromptTemplate.from_template(query_transform_prompts.STEP_BACK_QUERY_PROMPT)
    step_back_chain = step_back_prompt | model

    try:
        response = await step_back_chain.ainvoke({"original_query": original_query,"messages": messages})
        step_back_query = response.content.strip()
        logger.info(f"回退查询生成成功: {step_back_query}")
        return step_back_query
    except Exception as e:
        logger.error(f"回退问题生成失败: {e}")
        return original_query



async def standardize_terminology(original_query, messages:List[AnyMessage]=None):
    """
    将用户的口语化表达转换为知识库标准术语。

    Args:
        original_query (str): 用户原始提问
        messages (List[AnyMessage]): 对话历史消息

    Returns:
        str: 标准化术语后的问题
    """
    logger.info(f"开始术语标准化: {original_query}")
    if messages:
        standardize_prompt = ChatPromptTemplate.from_messages([
            ("system", query_transform_prompts.STANDARDIZE_TERMINOLOGY_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
            ("human", query_transform_prompts.STANDARDIZE_TERMINOLOGY_PROMPT)
        ]).partial(messages=messages)
    else:
        standardize_prompt = PromptTemplate.from_template(query_transform_prompts.STANDARDIZE_TERMINOLOGY_PROMPT)
    standardize_chain = standardize_prompt | model

    try:
        response = await standardize_chain.ainvoke({"original_query": original_query})
        standardized_query = response.content.strip()
        logger.info(f"术语标准化成功: {standardized_query}")
        return standardized_query
    except Exception as e:
        logger.error(f"术语标准化失败: {e}")
        return original_query


async def expand_implicit_query(original_query, messages:List[AnyMessage]=None):
    """
    展开用户隐含的完整问题意图，将简短问题扩展为完整表述。

    Args:
        original_query (str): 用户原始提问
        messages (List[AnyMessage]): 对话历史消息

    Returns:
        str: 展开后的完整问题
    """
    logger.info(f"开始展开隐含查询: {original_query}")
    if messages:
        expand_prompt = ChatPromptTemplate.from_messages([
            ("system", query_transform_prompts.EXPAND_IMPLICIT_QUERY_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
            ("human", query_transform_prompts.EXPAND_IMPLICIT_QUERY_PROMPT)
        ]).partial(messages=messages)
    else:
        expand_prompt = PromptTemplate.from_template(query_transform_prompts.EXPAND_IMPLICIT_QUERY_PROMPT)
    expand_chain = expand_prompt | model

    try:
        response = await expand_chain.ainvoke({"original_query": original_query})
        expanded_query = response.content.strip()
        logger.info(f"隐含查询展开成功: {expanded_query}")
        return expanded_query
    except Exception as e:
        logger.error(f"隐含查询展开失败: {e}")
        return original_query


async def decompose_to_components(original_query):
    """
    将询问具体物品的问题分解为其关键组成部分，以匹配知识库中的相关规定。
    
    适用场景：用户询问具体物品（如感应灯、智能手表等），但知识库中没有该物品的直接规定，
    而是对其关键组成部分（如锂电池、电子元件等）有相关规定。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 分解为组件后的问题
    """
    logger.info(f"开始组件分解改写: {original_query}")
    decompose_prompt = PromptTemplate.from_template(query_transform_prompts.COMPONENT_DECOMPOSE_PROMPT)
    decompose_chain = decompose_prompt | model

    try:
        response = await decompose_chain.ainvoke({"original_query": original_query})
        decomposed_query = response.content.strip()
        logger.info(f"组件分解改写成功: {decomposed_query}")
        return decomposed_query
    except Exception as e:
        logger.error(f"组件分解改写失败: {e}")
        return original_query


async def professional_prejudgment_rewrite(original_query):
    """
    基于专业知识对用户问题进行预判性改写，像资深客服一样直接定位到关键限制条件。
    
    适用场景：用户询问具体物品时，基于民航安检专业知识，直接预判该物品的关键限制因素，
    并将问题改写为包含具体限制条件的专业问题。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 基于专业预判改写后的问题
    """
    logger.info(f"开始专业预判改写: {original_query}")
    prejudgment_prompt = PromptTemplate.from_template(query_transform_prompts.PROFESSIONAL_PREJUDGMENT_PROMPT)
    prejudgment_chain = prejudgment_prompt | model

    try:
        response = await prejudgment_chain.ainvoke({"original_query": original_query})
        prejudged_query = response.content.strip()
        logger.info(f"专业预判改写成功: {prejudged_query}")
        return prejudged_query
    except Exception as e:
        logger.error(f"专业预判改写失败: {e}")
        return original_query


async def specification_prefill_rewrite(original_query):
    """
    为涉及规格限制的物品问题预填常见的限制条件。
    
    适用场景：用户询问的物品通常有明确的规格限制（如容量、重量、尺寸等），
    直接在问题中补充最常见的限制条件，提高匹配精度。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 预填规格限制后的问题
    """
    logger.info(f"开始规格预填改写: {original_query}")
    specification_prompt = PromptTemplate.from_template(query_transform_prompts.SPECIFICATION_PREFILL_PROMPT)
    specification_chain = specification_prompt | model

    try:
        response = await specification_chain.ainvoke({"original_query": original_query})
        prefilled_query = response.content.strip()
        logger.info(f"规格预填改写成功: {prefilled_query}")
        return prefilled_query
    except Exception as e:
        logger.error(f"规格预填改写失败: {e}")
        return original_query


async def scenario_refinement_rewrite(original_query):
    """
    根据物品特性将问题细分为最可能的具体使用场景。
    
    适用场景：用户询问的物品在不同场景下有不同规定，
    基于常见情况将问题细化为最可能的具体场景。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 场景细分后的问题
    """
    logger.info(f"开始场景细分改写: {original_query}")
    scenario_prompt = PromptTemplate.from_template(query_transform_prompts.SCENARIO_REFINEMENT_PROMPT)
    scenario_chain = scenario_prompt | model

    try:
        response = await scenario_chain.ainvoke({"original_query": original_query})
        refined_query = response.content.strip()
        logger.info(f"场景细分改写成功: {refined_query}")
        return refined_query
    except Exception as e:
        logger.error(f"场景细分改写失败: {e}")
        return original_query


async def comprehensive_query_transform(original_query, strategies=None, messages:List[AnyMessage]=None):
    """
    综合性查询变换函数，根据指定策略对用户问题进行多维度改写。
    
    Args:
        original_query (str): 用户原始提问
        strategies (list): 要应用的变换策略列表，可选值：
            - 'rewrite': 基础查询重写
            - 'step_back': 回退查询生成  
            - 'standardize': 术语标准化
            - 'expand': 隐含查询展开
            - 'decompose': 组件分解改写
            - 'professional': 专业预判改写
            - 'specification': 规格预填改写
            - 'scenario': 场景细分改写
            如果为None，将应用所有策略
        messages (List[AnyMessage]): 对话历史消息
    
    Returns:
        dict: 包含各种变换结果的字典
    """
    if strategies is None:
        strategies = ['rewrite', 'flight_rewrite','step_back', 'standardize', 'expand', 'decompose', 'professional', 'specification', 'scenario']
    
    logger.info(f"开始综合查询变换: {original_query}, 策略: {strategies}")
    
    results = original_query
    
    # 根据指定策略执行相应的变换
    try:
        if 'rewrite' in strategies:
            results = await rewrite_query(original_query, messages)
        
        if 'flight_rewrite' in strategies:
            results = await flight_rewrite_query(original_query, messages)
        
        if 'step_back' in strategies:
            results = await generate_step_back_query(original_query, messages)
        
        if 'standardize' in strategies:
            results = await standardize_terminology(original_query, messages)
        
        if 'expand' in strategies:
            results = await expand_implicit_query(original_query, messages)
        
        if 'decompose' in strategies:
            results = await decompose_to_components(original_query)
        
        if 'professional' in strategies:
            results = await professional_prejudgment_rewrite(original_query)
        
        if 'specification' in strategies:
            results = await specification_prefill_rewrite(original_query)
        
        if 'scenario' in strategies:
            results = await scenario_refinement_rewrite(original_query)
        
        logger.info(f"综合查询变换完成: {results}")
        return results
        
    except Exception as e:
        logger.error(f"综合查询变换失败: {e}")
        return results 