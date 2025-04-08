"""
知识问答模块的节点实现
"""

import json
import random
from typing import Dict, List, Any

from agents.knowledge_qa.state import KnowledgeQAState
from agents.utils.llm_utils import default_llm
from agents.utils.vector_store import default_vector_store


def query_analysis(state: KnowledgeQAState):
    """分析用户查询的完整性和明确度"""
    messages = state["messages"]
    latest_message = messages[-1]["content"] if isinstance(messages[-1], dict) else messages[-1].content
    
    # 使用LLM分析查询完整性
    system_prompt = """分析用户关于机场的问题是否完整明确。
    如果不完整，确定缺少哪些信息。例如：
    - 未指明具体机场或航站楼
    - 未指明具体服务或设施
    - 查询太宽泛无法给出有针对性的回答
    
    回复格式：
    {
      "query_complete": true/false,
      "missing_info": ["缺失信息1", "缺失信息2"...],
      "needs_clarification": true/false
    }"""
    
    analysis_result = default_llm.invoke(
        [{"role": "user", "content": latest_message}],
        system_prompt=system_prompt,
        output_format="JSON"
    )
    
    # 解析LLM返回的JSON结果
    result = default_llm.parse_json_response(analysis_result, {
        "query_complete": True,
        "missing_info": [],
        "needs_clarification": False
    })
    
    return {
        "query_complete": result["query_complete"],
        "missing_info": result.get("missing_info", []),
        "needs_clarification": result["needs_clarification"],
        "clarification_round": state.get("clarification_round", 0) + (1 if result["needs_clarification"] else 0)
    }


def clarification_node(state: KnowledgeQAState):
    """生成澄清问题"""
    if state.get("clarification_round", 0) > 2:
        # 防止无限澄清循环，最多澄清两轮
        return {
            "query_complete": True,  # 强制进入下一阶段
            "messages": state["messages"] + [{"role": "assistant", "content": "我将基于目前的信息尽力回答您的问题。"}]
        }
    
    # 根据缺失信息生成澄清问题
    clarification_prompt = f"为了更好地回答您的问题，我需要了解一些细节：\n"
    for info in state.get("missing_info", []):
        clarification_prompt += f"- {info}?\n"
    clarification_prompt += "\n您能提供这些信息吗？"
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": clarification_prompt}]
    }


def knowledge_retrieval(state: KnowledgeQAState):
    """检索相关知识"""
    messages = state["messages"]
    
    # 提取最后一条用户消息作为查询
    last_user_msg = None
    for msg in reversed(messages):
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.type
        if role == "user" or role == "human":
            last_user_msg = content
            break
    
    if not last_user_msg:
        return {
            "context_retrieved": [],
            "relevance_score": 0.0
        }
    
    # 从向量数据库检索相关知识
    search_results = default_vector_store.search(last_user_msg, limit=5)
    
    # 计算相关性分数
    relevance_score = sum([result["score"] for result in search_results]) / len(search_results) if search_results else 0
    
    # 检查是否是关于刀具的查询，获取更多细节
    if "刀" in last_user_msg or "刀具" in last_user_msg:
        knife_results = default_vector_store.search("刀具 安检 规定", limit=3)
        search_results.extend(knife_results)
    
    return {
        "context_retrieved": search_results,
        "relevance_score": relevance_score
    }


def check_granularity(state: KnowledgeQAState):
    """检查检索结果的粒度是否与用户问题匹配"""
    messages = state["messages"]
    last_user_msg = None
    for msg in reversed(messages):
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.type
        if role == "user" or role == "human":
            last_user_msg = content
            break
            
    context = state.get("context_retrieved", [])
    context_content = [c["content"] for c in context]
    
    # 使用LLM分析粒度匹配情况
    system_prompt = """
    分析用户问题与检索到的上下文信息的粒度匹配情况。
    如果检索到的信息包含比用户问题更细粒度的分类或规定，
    请识别出这些更细粒度的类别，以便我们可以引导用户进行更具体的提问。
    
    例如:
    - 用户问"可以带刀具吗?"，但上下文包含对不同类型刀具(水果刀、菜刀、折叠刀等)的不同规定
    - 用户问"机场有餐厅吗?"，但上下文包含不同航站楼的不同餐厅信息
    - 用户问"行李限重是多少?"，但上下文包含不同舱位、不同航线的行李规定
    
    回复格式：
    {
      "granularity_match": true/false,
      "sub_categories": ["子类别1", "子类别2"...],
      "needs_refinement": true/false,
      "refinement_question": "建议的澄清问题"
    }"""
    
    analysis_input = f"用户问题: {last_user_msg}\n\n检索到的上下文:\n" + "\n".join(context_content)
    
    analysis_result = default_llm.invoke(
        [{"role": "user", "content": analysis_input}],
        system_prompt=system_prompt,
        output_format="JSON"
    )
    
    # 解析LLM返回的JSON结果
    try:
        result = default_llm.parse_json_response(analysis_result, {
            "granularity_match": True,
            "sub_categories": [],
            "needs_refinement": False,
            "refinement_question": ""
        })
        
        return {
            "granularity_match": result.get("granularity_match", True),
            "sub_categories": result.get("sub_categories", []),
            "needs_refinement": result.get("needs_refinement", False),
            "refinement_question": result.get("refinement_question", "")
        }
    except:
        # 解析失败时的默认值
        return {
            "granularity_match": True,  # 默认认为匹配，避免不必要的循环
            "sub_categories": [],
            "needs_refinement": False,
            "refinement_question": ""
        }


def request_refinement(state: KnowledgeQAState):
    """当检索结果包含更细粒度信息时，引导用户选择具体类别"""
    
    # 使用已有的子类别和建议问题
    sub_categories = state.get("sub_categories", [])
    refinement_question = state.get("refinement_question", "")
    
    # 如果没有建议问题，自动生成一个
    if not refinement_question and sub_categories:
        categories_text = "、".join(sub_categories)
        refinement_question = f"我发现关于您提问的内容有不同的规定，请问您具体是询问关于{categories_text}中的哪一种？"
    
    # 如果既没有建议问题也没有子类别，生成一个通用问题
    if not refinement_question:
        messages = state["messages"]
        last_user_msg = None
        for msg in reversed(messages):
            content = msg["content"] if isinstance(msg, dict) else msg.content
            role = msg["role"] if isinstance(msg, dict) else msg.type
            if role == "user" or role == "human":
                last_user_msg = content
                break
                
        context = state.get("context_retrieved", [])
        
        refinement_question = default_llm.invoke(
            [{"role": "user", "content": f"原始问题: {last_user_msg}\n上下文: {context}"}],
            system_prompt="生成一个简短、清晰的问题，询问用户更具体的信息。基于用户的原始问题和检索到的上下文，引导用户提供更精确的查询条件。不要超过两句话。"
        )
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": refinement_question}],
        "needs_clarification": True,
        "clarification_round": state.get("clarification_round", 0) + 1
    }


def ask_for_specifics(state: KnowledgeQAState):
    """当检索结果相关性低时请求用户提供更具体信息"""
    messages = state["messages"]
    last_user_msg = None
    for msg in reversed(messages):
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.type
        if role == "user" or role == "human":
            last_user_msg = content
            break
            
    # 分析为什么结果相关性低
    analysis = default_llm.invoke(
        [
            {"role": "user", "content": last_user_msg}
        ],
        system_prompt=f"分析为什么无法找到与用户查询高度相关的信息，并准备一个简短的反问。检索到的上下文相关性分数: {state.get('relevance_score', 0)}"
    )
    
    # 生成反问
    follow_up = default_llm.invoke(
        [{"role": "user", "content": analysis}],
        system_prompt="生成一个简短、清晰的问题，帮助用户更具体地表达需求。不要超过两句话。"
    )
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": follow_up}],
        "needs_clarification": True,
        "clarification_round": state.get("clarification_round", 0) + 1
    }


def generate_final_answer(state: KnowledgeQAState):
    """生成最终的回答"""
    messages = state["messages"]
    last_user_msg = None
    for msg in reversed(messages):
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.type
        if role == "user" or role == "human":
            last_user_msg = content
            break
            
    context = state.get("context_retrieved", [])
    context_content = [c["content"] for c in context]
    
    # 使用LLM生成回答
    system_prompt = """你是机场智能客服助手。
    请基于提供的上下文信息，回答用户的问题。
    回答必须准确，不要编造不在上下文中的信息。
    如果上下文不包含回答问题所需的信息，请直接表明你不知道，不要编造。
    不要说"根据提供的信息"或"基于上下文"等引导语。
    直接开始你的回答。"""
    
    response = default_llm.invoke(
        [{"role": "user", "content": last_user_msg}],
        system_prompt=f"{system_prompt}\n\n上下文信息: {json.dumps(context_content, ensure_ascii=False)}"
    )
    
    return {
        "current_answer": response,
        "needs_simplification": len(response) > 100  # 超过100字需要简化
    }


def simplify_answer(state: KnowledgeQAState):
    """简化冗长的回答"""
    long_answer = state.get("current_answer", "")
    
    if not long_answer:
        return {"simplified_answer": True}
    
    # 使用LLM简化回答
    system_prompt = """简化以下回答，使其:
    1. 不超过3-4个短句
    2. 直接回答核心问题
    3. 使用简洁明了的语言
    4. 保留所有关键信息
    5. 删除冗余解释和不必要的礼貌用语"""
    
    simplified = default_llm.invoke(
        [{"role": "user", "content": long_answer}],
        system_prompt=system_prompt
    )
    
    return {
        "current_answer": simplified,
        "simplified_answer": True,
        "final_response": simplified
    }


def select_response_style(state: KnowledgeQAState):
    """选择回答风格"""
    messages = state["messages"]
    last_user_msg = None
    for msg in reversed(messages):
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.type
        if role == "user" or role == "human":
            last_user_msg = content
            break
            
    # 分析用户情绪和紧急程度
    system_prompt = "简要分析用户问题的情绪和紧急程度，格式为JSON：{\"emotion\": \"平静|焦虑|着急\", \"urgency\": \"一般|紧急|非常紧急\"}"
    emotion_analysis = default_llm.invoke(
        [{"role": "user", "content": last_user_msg}],
        system_prompt=system_prompt,
        output_format="JSON"
    )
    
    try:
        emotion_data = default_llm.parse_json_response(emotion_analysis, {
            "emotion": "平静",
            "urgency": "一般"
        })
        
        # 根据情绪和紧急度设置回答风格
        if emotion_data["urgency"] == "非常紧急":
            style = "direct"  # 直接简洁风格
        elif emotion_data["emotion"] == "焦虑":
            style = "reassuring"  # 安抚风格
        else:
            # 随机选择风格增加多样性
            style = random.choice(["friendly", "professional", "helpful", "casual"])
        
        return {"response_style": style}
    except:
        return {"response_style": "professional"}  # 默认专业风格


def format_with_style(state: KnowledgeQAState):
    """根据选定的风格格式化回答"""
    answer = state.get("current_answer", "")
    style = state.get("response_style", "professional")
    
    if not answer:
        return {
            "final_response": "抱歉，我没有找到相关信息。",
            "messages": state["messages"] + [{"role": "assistant", "content": "抱歉，我没有找到相关信息。"}]
        }
    
    # 使用LLM根据风格调整回答语气
    system_prompt = f"""请保持以下回答的核心内容不变，但将其改写为{style}风格。
    
    风格说明：
    - direct: 直接、简洁、高效，只陈述必要信息
    - reassuring: 安抚式、有信心、令人放心
    - friendly: 友好、亲切、像朋友一样交谈
    - professional: 专业、正式、客观
    - helpful: 乐于助人、积极支持、提供额外相关信息
    - casual: 轻松、随意、简单直白
    
    保持回答简洁，字数与原回答相似。"""
    
    styled_answer = default_llm.invoke(
        [{"role": "user", "content": answer}],
        system_prompt=system_prompt
    )
    
    return {
        "final_response": styled_answer,
        "messages": state["messages"] + [{"role": "assistant", "content": styled_answer}]
    } 