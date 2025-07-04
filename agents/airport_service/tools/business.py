"""
业务办理工具模块
"""
import sys
import os
# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from pydantic import BaseModel,Field
from typing import Annotated, NotRequired
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from ..state import AirportMainServiceState
from common.logging import get_logger
import asyncio

# 获取业务办理工具专用日志记录器
logger = get_logger("agents.tools.business")


class WhellchairRentalRequest(BaseModel):
    name: str = Field(description="预约人姓名")
    id_number: str = Field(description="旅客身份证号码,18位数字")
    phone_number: str = Field(description="旅客联系方式,11位手机号")
    flight_number: str = Field(description="航班号")
    flight_date: str = Field(description="航班日期 格式为YYYY-MM-DD HH:MM:SS")


@tool(return_direct=True,args_schema=WhellchairRentalRequest)
async def wheelchair_rental_tool(name: str
                                 , id_number: str
                                 , phone_number: str
                                 , flight_number: str
                                 , flight_date: str
                                 ,config: RunnableConfig
) -> str:
    """
    轮椅租赁服务工具
    
    Args:
        request: 轮椅租赁相关请求
    """
    await asyncio.sleep(1)
    logger.info(f"轮椅租赁服务: ")
    logger.info(f"收集到的参数 - 姓名: {name}, 身份证: {id_number}, 电话: {phone_number}, 航班号: {flight_number}, 航班日期: {flight_date}")
    
    # 返回表单结构的JSON字符串
    import json
    
    # 构建表单字段，如果参数有值则添加预填值
    fields = []
    prefilled_fields = []  # 记录预填的字段
    
    # 姓名字段
    name_field = {
        "id": "cjr",
        "type": "text",
        "label": "预约人姓名",
        "placeholder": "请输入预约人姓名",
        "required": True
    }
    if name and name.strip():  # 如果姓名已收集到
        name_field["value"] = name.strip()
        prefilled_fields.append(f"姓名: {name.strip()}")
    fields.append(name_field)
    
    # 身份证号码字段
    id_field = {
        "id": "id_number",
        "type": "text",
        "label": "身份证号码",
        "placeholder": "请输入18位身份证号码",
        "required": True,
        "validation": {
            "pattern": "^[0-9]{18}$",
            "error_message": "请输入有效的18位身份证号码"
        }
    }
    if id_number and id_number.strip():  # 如果身份证号已收集到
        id_field["value"] = id_number.strip()
        prefilled_fields.append(f"身份证: {id_number.strip()}")
    fields.append(id_field)
    
    # 联系电话字段
    phone_field = {
        "id": "cjrdh",
        "type": "tel",
        "label": "联系电话",
        "placeholder": "请输入11位手机号",
        "required": True,
        "validation": {
            "pattern": "^1[3-9][0-9]{9}$",
            "error_message": "请输入有效的11位手机号码"
        }
    }
    if phone_number and phone_number.strip():  # 如果电话号码已收集到
        phone_field["value"] = phone_number.strip()
        prefilled_fields.append(f"电话: {phone_number.strip()}")
    fields.append(phone_field)
    
    # 租赁时间字段
    time_field = {
        "id": "rq",
        "type": "datetime-local",
        "label": "航班日期",
        "placeholder": "请选择航班日期",
        "required": True
    }
    if flight_date and flight_date.strip():  # 如果租赁时间已收集到
        time_field["value"] = flight_date.strip()
        prefilled_fields.append(f"时间: {flight_date.strip()}")
    fields.append(time_field)

    # 航班号字段
    flight_number_field = {
        "id": "hbxx",
        "type": "text",
        "label": "航班号",
        "placeholder": "请输入航班号",
        "required": True
    }
    if flight_number and flight_number.strip():  # 如果航班号已收集到
        flight_number_field["value"] = flight_number.strip()
        prefilled_fields.append(f"航班号: {flight_number.strip()}")
    fields.append(flight_number_field)
    
    form_data = {
        "type": "form",
        "title": "轮椅租赁申请",
        "description": "请填写以下信息完成轮椅租赁申请",
        "fields": fields,
        "buttons": [
            {
                "id": "submit",
                "label": "提交申请",
                "type": "submit"
            },
            {
                "id": "cancel",
                "label": "取消",
                "type": "cancel"
            }
        ],
        "action": "/api/v1/business/wheelchair-rental",
        "info": {
            "service_description": "轮椅租赁服务免费提供给行动不便的旅客，仅限机场内使用，可在各航站楼问询台申请。"
        }
    }
    
    # 记录预填字段信息
    if prefilled_fields:
        logger.info(f"表单预填字段: {', '.join(prefilled_fields)}")
    else:
        logger.info("无预填字段，返回空白表单")
    
    return json.dumps(form_data, ensure_ascii=False)

@tool
async def business_handler(query: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> str:
    """
    通用业务办理工具
    用于处理用户的业务办理请求，如轮椅租赁等。
    
    Args:
        query: 用户输入的业务办理请求
    示例:
        >>> business_handler("我要租一个轮椅")
    """
    logger.info("进入业务办理工具")
    logger.info(f"用户问题: {query}")
    logger.info("准备将请求转到业务子智能体")

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="工具调用结束，已准备转交业务办理子智能体处理",
                    tool_call_id=tool_call_id
                )
            ],
            "current_query": query
        }
    )
