"""
业务办理模块的节点实现
"""

import json
from typing import Dict, List, Any, Optional

from agents.business_service.state import BusinessServiceState
from agents.utils.llm_utils import default_llm
from agents.utils.api_connector import default_business_api


def identify_business_type(state: BusinessServiceState):
    """识别业务类型"""
    messages = state["messages"]
    latest_message = messages[-1]["content"] if isinstance(messages[-1], dict) else messages[-1].content
    
    # 使用LLM识别业务类型
    system_prompt = """分析用户请求的业务类型。
    支持的业务类型包括：
    - 值机: 办理值机手续，选择座位
    - 改签: 更改航班日期或时间
    - 退票: 办理机票退款
    - 行李托运: 托运行李
    - 遗失物品查询: 查询机场遗失物品
    
    如果不属于任何支持的业务类型，请返回"其他"。
    
    回复格式：
    {
      "business_type": "识别的业务类型",
      "confidence": 0.0-1.0的置信度得分
    }"""
    
    analysis_result = default_llm.invoke(
        [{"role": "user", "content": latest_message}],
        system_prompt=system_prompt,
        output_format="JSON"
    )
    
    # 解析LLM返回的JSON结果
    result = default_llm.parse_json_response(analysis_result, {
        "business_type": "其他",
        "confidence": 0.0
    })
    
    # 判断置信度是否足够
    business_type = result.get("business_type")
    confidence = result.get("confidence", 0.0)
    
    if confidence < 0.6 and business_type != "其他":
        # 置信度不足，需要用户确认
        return {
            "business_type": business_type,
            "needs_confirmation": True,
            "confirmed": False
        }
    
    return {
        "business_type": business_type,
        "needs_confirmation": False,
        "confirmed": True
    }


def request_business_confirmation(state: BusinessServiceState):
    """请求用户确认业务类型"""
    business_type = state.get("business_type", "未知业务")
    
    confirmation_message = f"您是想要办理\"{business_type}\"业务吗？请回复\"是\"或\"否\"，或者告诉我您具体想要办理什么业务。"
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": confirmation_message}]
    }


def collect_business_params(state: BusinessServiceState):
    """收集业务参数"""
    messages = state["messages"]
    business_type = state.get("business_type", "")
    
    # 合并所有用户消息作为上下文
    user_messages = []
    for msg in messages:
        content = msg["content"] if isinstance(msg, dict) else msg.content
        role = msg["role"] if isinstance(msg, dict) else msg.type
        if role == "user" or role == "human":
            user_messages.append(content)
    
    user_context = "\n".join(user_messages)
    
    # 定义不同业务类型需要的参数
    param_definitions = {
        "值机": {
            "required": ["flight_number", "passenger_name"],
            "optional": ["seat_preference"]
        },
        "改签": {
            "required": ["flight_number", "passenger_name", "new_date"],
            "optional": ["new_flight_number", "reason"]
        },
        "退票": {
            "required": ["flight_number", "passenger_name"],
            "optional": ["refund_reason"]
        },
        "行李托运": {
            "required": ["flight_number", "passenger_name", "baggage_weight"],
            "optional": ["baggage_description"]
        },
        "遗失物品查询": {
            "required": ["item_description"],
            "optional": ["loss_location", "loss_time", "contact_info"]
        }
    }
    
    # 如果不是支持的业务类型，返回错误
    if business_type not in param_definitions:
        return {
            "business_params": {},
            "params_complete": False,
            "missing_params": ["不支持的业务类型"],
            "error_message": f"抱歉，我们目前不支持\"{business_type}\"业务办理。"
        }
    
    # 使用LLM提取参数
    required_params = param_definitions[business_type]["required"]
    optional_params = param_definitions[business_type]["optional"]
    all_params = required_params + optional_params
    
    # 构建提示词
    param_description = ", ".join([f"{param}" for param in all_params])
    
    system_prompt = f"""从用户消息中提取{business_type}业务所需的参数。
    需要提取的参数包括: {param_description}
    
    如果无法提取某个参数，则不要包含此键。
    
    回复格式：
    {{
      "param1": "值1",
      "param2": "值2",
      ...
    }}"""
    
    extraction_result = default_llm.invoke(
        [{"role": "user", "content": user_context}],
        system_prompt=system_prompt,
        output_format="JSON"
    )
    
    # 解析LLM返回的JSON结果
    extracted_params = default_llm.parse_json_response(extraction_result, {})
    
    # 检查必要参数是否齐全
    missing_params = []
    for param in required_params:
        if param not in extracted_params or not extracted_params[param]:
            missing_params.append(param)
    
    params_complete = len(missing_params) == 0
    
    return {
        "business_params": extracted_params,
        "params_complete": params_complete,
        "missing_params": missing_params
    }


def request_missing_params(state: BusinessServiceState):
    """请求缺失的业务参数"""
    missing_params = state.get("missing_params", [])
    business_type = state.get("business_type", "")
    
    if not missing_params:
        # 没有缺失参数，跳过该节点
        return {}
    
    # 构建参数名称的友好显示
    param_display = {
        "flight_number": "航班号",
        "passenger_name": "乘客姓名",
        "seat_preference": "座位偏好(如靠窗、过道等)",
        "new_date": "新的出行日期",
        "new_flight_number": "新的航班号",
        "reason": "改签原因",
        "refund_reason": "退票原因",
        "baggage_weight": "行李重量(公斤)",
        "baggage_description": "行李描述",
        "item_description": "遗失物品描述",
        "loss_location": "遗失地点",
        "loss_time": "遗失时间",
        "contact_info": "联系方式"
    }
    
    # 构建请求缺失参数的提示
    prompt = f"为了办理{business_type}业务，我还需要以下信息："
    for param in missing_params:
        display_name = param_display.get(param, param)
        prompt += f"\n- {display_name}"
    
    prompt += "\n\n请提供这些信息，以便我为您办理业务。"
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": prompt}]
    }


def confirm_business_operation(state: BusinessServiceState):
    """确认业务办理"""
    business_type = state.get("business_type", "")
    params = state.get("business_params", {})
    
    # 格式化参数显示
    param_display = {
        "flight_number": "航班号",
        "passenger_name": "乘客姓名",
        "seat_preference": "座位偏好",
        "new_date": "新日期",
        "new_flight_number": "新航班号",
        "reason": "原因",
        "refund_reason": "退票原因",
        "baggage_weight": "行李重量",
        "baggage_description": "行李描述",
        "item_description": "物品描述",
        "loss_location": "遗失地点",
        "loss_time": "遗失时间",
        "contact_info": "联系方式"
    }
    
    param_summary = ""
    for key, value in params.items():
        display_name = param_display.get(key, key)
        param_summary += f"- {display_name}: {value}\n"
    
    # 构建确认信息
    confirmation_message = f"请确认以下{business_type}业务信息：\n\n{param_summary}\n是否确认办理？请回复\"确认\"或\"取消\"。"
    
    return {
        "needs_confirmation": True,
        "confirmed": False,
        "messages": state["messages"] + [{"role": "assistant", "content": confirmation_message}]
    }


def process_confirmation_response(state: BusinessServiceState):
    """处理确认响应"""
    messages = state["messages"]
    latest_message = messages[-1]["content"] if isinstance(messages[-1], dict) else messages[-1].content
    
    # 检查用户响应是否是确认
    confirmation_indicators = ["确认", "是", "yes", "确定", "可以", "同意", "好", "好的", "没问题", "正确", "对"]
    cancellation_indicators = ["取消", "否", "no", "不", "不要", "不行", "算了", "拒绝", "错误", "不对"]
    
    confirmed = False
    for indicator in confirmation_indicators:
        if indicator in latest_message:
            confirmed = True
            break
    
    cancelled = False
    for indicator in cancellation_indicators:
        if indicator in latest_message:
            cancelled = True
            break
    
    if cancelled:
        cancellation_message = "已取消业务办理。如果您需要其他帮助，请随时告诉我。"
        return {
            "confirmed": False,
            "messages": state["messages"] + [{"role": "assistant", "content": cancellation_message}],
            "final_response": cancellation_message
        }
    
    return {
        "confirmed": confirmed
    }


def call_business_api(state: BusinessServiceState):
    """调用业务API"""
    business_type = state.get("business_type", "")
    params = state.get("business_params", {})
    
    # 调用API
    try:
        api_response = default_business_api.call_service(business_type, params)
        
        success = api_response.get("success", False)
        error_message = api_response.get("error", "未知错误")
        
        if success:
            return {
                "api_response": api_response,
                "api_success": True
            }
        else:
            # 检查是否是缺少参数的错误
            if api_response.get("error_code") == "MISSING_PARAMS":
                missing_fields = api_response.get("missing_fields", [])
                return {
                    "api_response": api_response,
                    "api_success": False,
                    "error_message": error_message,
                    "missing_params": missing_fields,
                    "params_complete": False
                }
            else:
                return {
                    "api_response": api_response,
                    "api_success": False,
                    "error_message": error_message
                }
    except Exception as e:
        return {
            "api_success": False,
            "error_message": str(e)
        }


def handle_business_error(state: BusinessServiceState):
    """处理业务错误"""
    error_message = state.get("error_message", "未知错误")
    business_type = state.get("business_type", "")
    
    # 根据不同业务类型提供替代选项
    alternative_options = []
    if business_type == "值机":
        alternative_options = ["尝试使用航空公司APP或网站在线值机", "前往机场自助值机柜台", "联系航空公司客服热线"]
    elif business_type == "改签":
        alternative_options = ["联系航空公司客服办理改签", "前往机场柜台办理改签", "使用航空公司APP或网站在线改签"]
    elif business_type == "退票":
        alternative_options = ["联系航空公司客服办理退票", "前往航空公司柜台办理退票", "使用航空公司APP或网站在线退票"]
    else:
        alternative_options = ["联系机场客服热线", "前往机场服务柜台咨询", "使用机场APP查询相关信息"]
    
    # 构建错误响应
    options_text = "\n".join([f"- {option}" for option in alternative_options])
    error_response = f"抱歉，在办理{business_type}业务时遇到问题：{error_message}\n\n您可以尝试以下替代方式：\n{options_text}"
    
    return {
        "alternative_options": alternative_options,
        "formatted_result": error_response,
        "final_response": error_response,
        "messages": state["messages"] + [{"role": "assistant", "content": error_response}]
    }


def format_business_result(state: BusinessServiceState):
    """格式化业务结果"""
    business_type = state.get("business_type", "")
    api_response = state.get("api_response", {})
    data = api_response.get("data", {})
    
    if not data:
        return {
            "formatted_result": "业务处理成功，但未返回详细信息。",
            "final_response": "业务处理成功，但未返回详细信息。"
        }
    
    # 使用LLM格式化结果
    system_prompt = f"""作为机场客服，请将{business_type}业务办理结果以友好、专业的方式呈现给用户。
    回复应该：
    1. 清晰说明业务办理成功
    2. 包含所有重要信息
    3. 提供后续操作建议或提醒
    4. 语气礼貌亲切
    
    不要添加多余的解释或废话，直接提供有用的信息。"""
    
    formatted_result = default_llm.invoke(
        [{"role": "user", "content": json.dumps(data, ensure_ascii=False)}],
        system_prompt=system_prompt
    )
    
    return {
        "formatted_result": formatted_result,
        "final_response": formatted_result,
        "messages": state["messages"] + [{"role": "assistant", "content": formatted_result}]
    } 