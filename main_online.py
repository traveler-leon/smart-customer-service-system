import os
import asyncio
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, Union
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
    logger.info("Application started")
    yield
    # 关闭事件
    logger.info("Application shutting down")

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

@app.post("/chat/v1/stream", response_model=None)
async def chat_stream(user_input: UserInput, request: Request, response: Response):
    # 添加打印请求头的代码
    logger.info("Request headers:")
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
            
            # 使用新的graph_manager处理消息
            output_nodes = ["router", "airport_assistant_node", "flight_assistant_node", "chitchat_node","sql2bi_node"]
            
            async for node,result in graph_manager.process_chat_message(
                message=user_input.query_txt,
                thread_id=threads,
                graph_id="airport_service_graph",
                output_node=output_nodes
            ):
                print(node,result)
                if result and isinstance(result, str):
                    logger.debug(f"结果内容: {result}")
                    
                    # 检查敏感关键词
                    for sensitive_keyword in ["lookup_airport_policy", "search_flights"]:
                        if sensitive_keyword in result:
                            result = "xxx"
                            break
                            
                    response_data["item"]["answer_txt"] = result
                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                    
                    # 给异步任务让出控制权
                    await asyncio.sleep(0)
                    
            # 发送完成事件
            yield f"data: {json.dumps({'event': 'end'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            logger.error("异常", e)
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
        logger.error(f"Error generating graph: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8081)
