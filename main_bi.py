import os
import asyncio
import time
import uuid
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, Union, List
import warnings

from agents.airport_service import graph_manager, build_airport_service_graph
from common.logging import setup_logger, get_logger

warnings.filterwarnings("ignore")

# 设置日志
setup_logger(log_dir="logs", log_level="INFO")
logger = get_logger("airport_service")

# Lifespan事件管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    # 确保data目录存在
    os.makedirs("data", exist_ok=True)
    # 注册自定义图
    graph_manager.register_graph("airport_service_graph", build_airport_service_graph())
    logger.info("应用已启动")
    yield
    # 关闭事件
    logger.info("应用正在关闭")

app = FastAPI(lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserInput(BaseModel):
    cid: str
    msgid: str
    query_txt: str
    partnerid: Optional[str] = None
    multi_params: Optional[Union[str, Dict[str, Any]]] = None

class APIResponseItem(BaseModel):
    cid: str
    msgid: str
    answer_txt: Union[str, Dict[str, Any]]  # 允许字符串或字典
    answer_txt_type: str

class APIResponse(BaseModel):
    ret_code: str
    ret_msg: str
    item: APIResponseItem

# 新规范API路由
@app.post("/api/v1/airport-assistant/chat")
async def chat_stream_new(request: Request):
    """新版接口，符合api_specification.md的规范"""
    try:
        # 解析请求体
        body = await request.json()
        thread_id = body.get("thread_id", "")
        user_id = body.get("user_id", "")
        query = body.get("query", "")
        stream = body.get("stream", True)
        metadata = body.get("metadata", {})
        
        if not thread_id or not user_id or not query:
            return HTTPException(status_code=400, detail="缺少必要参数")
        
        # 获取token（如果有）
        token = request.headers.get("token", "")
        
        async def event_generator():
            try:
                # 事件序列计数器
                sequence_counter = 1
                
                # 构造线程上下文
                threads = {
                    "configurable": {
                        "passenger_id": user_id,
                        "thread_id": thread_id,
                        "token": token
                    }
                }
                
                logger.info(f"用户查询: {query}")
                
                # 发送开始事件
                yield f"event: start\ndata: {json.dumps({'event': 'start'})}\n\n"
                
                # 处理用户输入
                output_nodes = ["router", "airport_assistant_node", "flight_assistant_node", "chitchat_node", "sql2bi_node"]
                
                # 用于存储和收集数据事件信息
                data_events = {}
                
                async for node, result in graph_manager.process_chat_message(
                    message=query,
                    thread_id=threads,
                    graph_id="airport_service_graph",
                    output_node=output_nodes
                ):
                    logger.debug(f"节点: {node}, 结果类型: {type(result)}")
                    
                    # 根据节点类型处理不同的响应格式
                    if node == "sql2bi_node" and result:
                        result = json.loads(result)
                        if isinstance(result, dict):
                            # 生成唯一ID
                            timestamp = int(time.time() * 1000)
                            
                            # 1. 先发送数据事件
                            # if "sql_info" in result and "data" in result:
                            #     data_id = f"data-sql-{timestamp}"
                            #     data_payload = {
                            #         "id": data_id,
                            #         "sequence": sequence_counter,
                            #         "content": {
                            #             "data_type": "sql_result",
                            #             "data": result.get("data", []),
                            #             "sql": result.get("sql_info", {}).get("sql", "")
                            #         }
                            #     }
                            #     data_events[data_id] = data_payload
                            #     yield f"event: data\ndata: {json.dumps(data_payload)}\n\n"
                            #     sequence_counter += 1
                            
                            # 2. 发送可视化事件
                            vis_id = f"vis-{result.get('chart_type', 'chart')}-{timestamp}"
                            vis_payload = {
                                "id": vis_id,
                                "sequence": sequence_counter,
                                "content": {
                                    "visualization_type": "echarts",
                                    "title": result.get("title", "数据可视化"),
                                    "description": result.get("message", ""),
                                    "data_reference": list(data_events.keys())[-1] if data_events else None,
                                    "chart_info": {
                                        "chart_type": result.get("chart_type", ""),
                                        "chart_subtype": result.get("chart_subtype", ""),
                                        "chart_name": result.get("chart_name", "")
                                    },
                                    "echarts_option": result.get("echarts_option", {}),
                                    "sql_info": result.get("sql_info", {}),
                                    "alternative_charts": result.get("suitable_charts", [])
                                }
                            }
                            print(f"event: visualization\ndata: {json.dumps(vis_payload, ensure_ascii=False)}\n\n")
                            yield f"event: visualization\ndata: {json.dumps(vis_payload, ensure_ascii=False)}\n\n"
                            sequence_counter += 1
                            
                            # 3. 可能还有文本描述
                            if "description" in result or "message" in result:
                                description = result.get("description", result.get("message", ""))
                                if description:
                                    text_id = f"text-{timestamp}-{sequence_counter}"
                                    text_payload = {
                                        "id": text_id,
                                        "sequence": sequence_counter,
                                        "content": {
                                            "text": description,
                                            "format": "plain"
                                        }
                                    }
                                    yield f"event: text\ndata: {json.dumps(text_payload)}\n\n"
                                    sequence_counter += 1
                    
                    # 文本响应处理
                    elif result and isinstance(result, str):
                        # 生成唯一ID
                        timestamp = int(time.time() * 1000)
                        text_id = f"text-{timestamp}-{sequence_counter}"
                        
                        # 检查是否为Markdown格式
                        format_type = "markdown" if "```" in result or "##" in result or "*" in result else "plain"
                        
                        text_payload = {
                            "id": text_id,
                            "sequence": sequence_counter,
                            "content": {
                                "text": result,
                                "format": format_type
                            }
                        }
                        yield f"event: text\ndata: {json.dumps(text_payload)}\n\n"
                        sequence_counter += 1
                    
                    # 处理其他可能的响应类型
                    elif result and isinstance(result, dict) and "type" in result:
                        event_type = result.get("type")
                        timestamp = int(time.time() * 1000)
                        
                        if event_type == "form":
                            form_id = f"form-{result.get('form_type', 'generic')}-{timestamp}"
                            form_payload = {
                                "id": form_id,
                                "sequence": sequence_counter,
                                "content": result.get("content", {})
                            }
                            yield f"event: form\ndata: {json.dumps(form_payload)}\n\n"
                            sequence_counter += 1
                    
                    # 给异步任务让出控制权
                    await asyncio.sleep(0)
                
                # 发送结束事件
                timestamp = int(time.time() * 1000)
                end_id = f"end-{timestamp}"
                end_payload = {
                    "id": end_id,
                    "sequence": sequence_counter,
                    "content": {
                        "suggestions": ["查询航班信息", "了解行李政策", "机场服务指南"],
                        "metadata": {
                            "processing_time": f"{(time.time() * 1000 - timestamp) / 1000:.2f}s"
                        }
                    }
                }
                yield f"event: end\ndata: {json.dumps(end_payload)}\n\n"
                
            except Exception as e:
                logger.error(f"生成响应时发生错误: {str(e)}", exc_info=True)
                timestamp = int(time.time() * 1000)
                error_id = f"error-server-{timestamp}"
                error_payload = {
                    "id": error_id,
                    "sequence": 1,
                    "content": {
                        "error_code": "server_error",
                        "error_message": "服务处理请求时发生错误，请稍后重试"
                    }
                }
                yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
        
        # 返回SSE流
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
    
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

# 保留旧接口保持兼容
@app.post("/chat/v1/stream", response_model=None)
async def chat_stream(user_input: UserInput, request: Request, response: Response):
    # 添加打印请求头的代码
    logger.info("请求头:")
    for header_name, header_value in request.headers.items():
        logger.info(f"{header_name}: {header_value}")
    
    # 验证必要字段
    if not user_input.cid or not user_input.msgid or not user_input.query_txt:
        raise HTTPException(status_code=400, detail="必要字段缺失")
        
    # 验证multi_params格式
    if user_input.multi_params:
        try:
            if isinstance(user_input.multi_params, str):
                json.loads(user_input.multi_params)  # 验证JSON格式
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="multi_params格式错误")
    
    # 从请求头中获取token
    token = request.headers.get("token","")
    if token:
        response.headers["token"] = token
    
    async def event_generator():
        try:
            threads = {
                "configurable": {
                    "passenger_id": user_input.cid,
                    "thread_id": user_input.cid,
                    "token": token
                }
            }
            
            logger.info(f"流用户输入: {user_input.query_txt}")
            
            # 发送 SSE 响应头数据
            yield f"data: {json.dumps({'event': 'start'})}\n\n"
            
            # 初始化响应数据结构
            response_data = {
                "ret_code": "000000",
                "ret_msg": "操作成功",
                "item": {
                    "cid": user_input.cid,
                    "msgid": user_input.msgid,
                    "answer_txt": "",
                    "answer_txt_type": "0"
                }
            }
            
            # 使用graph_manager处理消息
            output_nodes = ["router", "airport_assistant_node", "flight_assistant_node", "chitchat_node", "sql2bi_node"]
            
            async for node, result in graph_manager.process_chat_message(
                message=user_input.query_txt,
                thread_id=threads,
                graph_id="airport_service_graph",
                output_node=output_nodes
            ):
                logger.debug(f"节点: {node}, 结果类型: {type(result)}")
                
                # 处理SQL2BI节点的结果
                if node == "sql2bi_node" and result and isinstance(result, dict):
                    # 将SQL2BI结果转换为旧格式
                    response_data["item"]["answer_txt"] = {
                        "type": "visualization",
                        "visualization_type": "echarts",
                        "title": result.get("title", "数据可视化"),
                        "chart_info": {
                            "chart_type": result.get("chart_type", ""),
                            "chart_subtype": result.get("chart_subtype", ""),
                            "chart_name": result.get("chart_name", "")
                        },
                        "echarts_option": result.get("echarts_option", {}),
                        "message": result.get("message", "")
                    }
                    response_data["item"]["answer_txt_type"] = "1"  # 表示JSON格式
                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                
                # 处理文本结果
                elif result and isinstance(result, str):
                    logger.debug(f"结果内容: {result}")
                    
                    # 检查敏感关键词
                    for sensitive_keyword in ["lookup_airport_policy", "search_flights"]:
                        if sensitive_keyword in result:
                            result = "xxx"
                            break
                            
                    response_data["item"]["answer_txt"] = result
                    response_data["item"]["answer_txt_type"] = "0"  # 表示文本格式
                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                    
                # 给异步任务让出控制权
                await asyncio.sleep(0)
                    
            # 发送完成事件
            yield f"data: {json.dumps({'event': 'end'})}\n\n"
            
        except Exception as e:
            logger.error(f"聊天过程中出错: {str(e)}", exc_info=True)
            error_response = {
                "ret_code": "000000",
                "ret_msg": "操作成功",
                "item": {
                    "cid": user_input.cid,
                    "msgid": user_input.msgid,
                    "answer_txt": "刚刚服务在忙，请您重新提问。",
                    "answer_txt_type": "0"
                }
            }
            yield f"data: {json.dumps(error_response)}\n\n"
    
    # 返回 SSE 流式响应
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

# 添加一个用于查看图结构的辅助函数
def view_graph():
    try:
        graph = build_airport_service_graph()
        graph_image = graph.compile().get_graph().draw_mermaid_png()
        with open("main_graph.png", "wb") as f:
            f.write(graph_image)
    except Exception as e:
        logger.error(f"生成图表时出错: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8081)
