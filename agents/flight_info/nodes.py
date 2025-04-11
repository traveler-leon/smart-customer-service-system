"""
航班信息查询模块的节点实现
"""

import json
import re
from typing import Dict, List, Any, Optional

from agents.flight_info.state import FlightInfoState
from agents.utils.llm_utils import default_llm
from agents.utils.sql_utils import default_flight_db


def extract_flight_params(state: FlightInfoState):
    """提取航班查询参数"""
    messages = state["messages"]
    latest_message = messages[-1]["content"] if isinstance(messages[-1], dict) else messages[-1].content
    
    # 使用LLM提取航班参数
    system_prompt = """提取用户航班查询中的关键参数。
    返回以下可能的参数：
    - flight_number: 航班号
    - airline: 航空公司
    - departure_city: 出发城市
    - arrival_city: 到达城市
    - date: 日期
    - status_query: 是否查询航班状态(准点/延误/取消)
    
    如果无法提取到某个参数，则不要包含此键。
    
    回复格式：
    {
      "flight_number": "航班号",
      "airline": "航空公司",
      "departure_city": "出发城市",
      "arrival_city": "到达城市",
      "date": "日期",
      "status_query": true/false
    }"""
    
    extraction_result = default_llm.invoke(
        [{"role": "user", "content": latest_message}],
        system_prompt=system_prompt,
        output_format="JSON"
    )
    
    # 解析LLM返回的JSON结果
    extracted_params = default_llm.parse_json_response(extraction_result, {})
    
    # 检查参数完整性
    # 判断条件：航班号存在，或者 (出发城市和到达城市都存在)
    params_complete = (
        "flight_number" in extracted_params or 
        ("departure_city" in extracted_params and "arrival_city" in extracted_params)
    )
    
    # 构建缺失参数列表
    missing_params = []
    if not params_complete:
        if "flight_number" not in extracted_params:
            if "departure_city" not in extracted_params:
                missing_params.append("出发城市")
            if "arrival_city" not in extracted_params:
                missing_params.append("到达城市")
        if "date" not in extracted_params and len(missing_params) == 0:
            # 日期不是必要参数，但如果其他参数都有了，可以询问日期
            missing_params.append("日期")
    
    return {
        "flight_params": extracted_params,
        "params_complete": params_complete,
        "missing_params": missing_params
    }


def request_flight_params(state: FlightInfoState):
    """请求缺失的航班参数"""
    missing_params = state.get("missing_params", [])
    
    if not missing_params:
        # 没有缺失参数，跳过该节点
        return {}
    
    # 构建请求缺失参数的提示
    prompt = "为了查询航班信息，我还需要知道："
    for param in missing_params:
        prompt += f"\n- {param}"
    
    prompt += "\n\n您能提供这些信息吗？"
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": prompt}]
    }


def generate_sql_query(state: FlightInfoState):
    """生成SQL查询"""
    params = state.get("flight_params", {})
    
    # 调用数据库模块生成SQL
    query_text = json.dumps(params, ensure_ascii=False)
    sql_query = default_flight_db.generate_sql(query_text)
    
    return {
        "sql_query": sql_query
    }


def execute_database_query(state: FlightInfoState):
    """执行数据库查询"""
    sql_query = state.get("sql_query", "")
    
    if not sql_query:
        return {
            "query_success": False,
            "error_message": "未生成SQL查询",
            "query_results": []
        }
    
    try:
        # 执行查询
        results = default_flight_db.execute_query(sql_query)
        
        # 检查查询结果
        if not results:
            return {
                "query_success": True,
                "query_results": [],
                "error_message": "未找到符合条件的航班"
            }
        
        # 检查错误
        if len(results) == 1 and "error" in results[0]:
            return {
                "query_success": False,
                "error_message": results[0]["error"],
                "query_results": [],
                "retry_count": state.get("retry_count", 0) + 1
            }
        
        return {
            "query_success": True,
            "query_results": results
        }
    except Exception as e:
        return {
            "query_success": False,
            "error_message": str(e),
            "query_results": [],
            "retry_count": state.get("retry_count", 0) + 1
        }


def handle_query_error(state: FlightInfoState):
    """处理查询错误"""
    error_message = state.get("error_message", "未知错误")
    retry_count = state.get("retry_count", 0)
    
    # 如果重试次数超过限制，返回错误消息
    if retry_count >= 2:
        error_response = f"抱歉，查询航班信息时遇到了技术问题：{error_message}。请稍后再试或者联系客服人员。"
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": error_response}],
            "final_response": error_response
        }
    
    # 尝试修复SQL查询并重试
    return {
        "sql_query": f"SELECT * FROM flights"  # 使用更简单的查询进行重试
    }


def format_flight_result(state: FlightInfoState):
    """格式化航班查询结果"""
    results = state.get("query_results", [])
    params = state.get("flight_params", {})
    
    if not results:
        no_result_message = "抱歉，未找到符合条件的航班信息。"
        return {
            "formatted_result": no_result_message,
            "final_response": no_result_message
        }
    
    # 使用LLM格式化结果
    system_prompt = """作为机场客服，请将航班查询结果以简洁易读的方式呈现给用户。
    回复应该清晰、专业，包含所有重要信息。
    不要包含任何多余的解释，直接提供航班信息即可。
    如果用户询问的是航班状态，请强调该信息。"""
    
    context = {
        "query_params": params,
        "query_results": results
    }
    
    formatted_result = default_llm.invoke(
        [{"role": "user", "content": json.dumps(context, ensure_ascii=False)}],
        system_prompt=system_prompt
    )
    
    return {
        "formatted_result": formatted_result,
        "final_response": formatted_result
    }


def simplify_flight_info(state: FlightInfoState):
    """简化航班信息"""
    formatted_result = state.get("formatted_result", "")
    
    if len(formatted_result) <= 100:
        # 已经足够简洁，无需简化
        return {
            "final_response": formatted_result,
            "simplified_result": True
        }
    
    # 使用LLM简化结果
    system_prompt = """请将以下航班信息简化为不超过50字的极简版本。
    仅保留最关键的信息，如航班号、状态(准点/延误/取消)、时间等。
    确保简化后的信息仍然准确且有用。"""
    
    simplified_result = default_llm.invoke(
        [{"role": "user", "content": formatted_result}],
        system_prompt=system_prompt
    )
    
    return {
        "formatted_result": simplified_result,
        "final_response": simplified_result,
        "simplified_result": True,
        "messages": state["messages"] + [{"role": "assistant", "content": simplified_result}]
    } 