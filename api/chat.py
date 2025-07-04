import json
import asyncio
import time
from fastapi import APIRouter, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from models.schemas import (
    UserInput, AirportChatRequest,
    TextEventContent, FormEventContent, EndEventContent, ErrorEventContent, ChatEvent
)
from agents.airport_service import graph_manager
from common.logging import get_logger

# 使用专门的API聊天日志记录器
logger = get_logger("api.chat")

router = APIRouter(prefix="/chat/v1", tags=["聊天"])

@router.post("/stream", response_model=None)
async def chat_stream(user_input: UserInput, request: Request, response: Response):
    logger.info(f"收到聊天请求 - CID: {user_input.cid}, MSGID: {user_input.msgid}, Query: {user_input.query_txt}")

    if not user_input.cid or not user_input.msgid or not user_input.query_txt:
        logger.error("聊天请求缺少必要字段")
        raise HTTPException(status_code=400, detail="必要字段缺失")
    if user_input.multi_params:
        try:
            if isinstance(user_input.multi_params, str):
                multi_params = json.loads(user_input.multi_params)
                Is_translate = multi_params.get("Is_translate", False)
                Is_emotion = multi_params.get("Is_emotion", False)
            elif isinstance(user_input.multi_params, dict):
                Is_translate = user_input.multi_params.get("Is_translate", False)
                Is_emotion = user_input.multi_params.get("Is_emotion", False)
            else:
                Is_translate = False
                Is_emotion = False
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="multi_params格式错误")
    else:
        Is_translate = False
        Is_emotion = False
        
    token = request.headers.get("token","")
    if token:
        response.headers["token"] = token

    output_nodes = []
    if Is_translate:
        output_nodes = ["translate_output_node"]
    else:
        output_nodes = ["airport_assistant_node", "flight_assistant_node", "chitchat_node"]
    async def event_generator():
        try:
            threads = {
                "configurable": {
                    "passenger_id": user_input.cid,
                    "thread_id": user_input.cid,
                    "token": token,
                    "Is_translate": Is_translate,
                    "Is_emotion": Is_emotion
                }
            }
            logger.info(f"流用户输入: {user_input.query_txt}")
            yield f"data: {json.dumps({'event': 'start'})}\n\n"
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
            # output_nodes = ["router", "airport_assistant_node", "flight_assistant_node", "chitchat_node", "sql2bi_node"]
            async for node, result in graph_manager.process_chat_message(
                message=user_input.query_txt,
                thread_id=threads,
                graph_id="airport_service_graph",
                output_node=output_nodes
            ):
                print(node, result)
                if result and isinstance(result, str):
                    logger.debug(f"结果内容: {result}")
                    for sensitive_keyword in ["lookup_airport_policy", "search_flights"]:
                        if sensitive_keyword in result:
                            result = "xxx"
                            break
                    response_data["item"]["answer_txt"] = result
                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0)
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
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 验证必要字段
            cid = message_data.get("cid")
            msgid = message_data.get("msgid") 
            query_txt = message_data.get("query_txt")
            multi_params = message_data.get("multi_params")
            token = message_data.get("token", "")
            
            if not cid or not msgid or not query_txt:
                error_response = {
                    "error": "必要字段缺失",
                    "ret_code": "400001"
                }
                await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                continue
            
            # 处理multi_params
            Is_translate = False
            Is_emotion = False

            if multi_params:
                try:
                    if isinstance(multi_params, str):
                        multi_params = json.loads(multi_params)
                    
                    if isinstance(multi_params, dict):
                        Is_translate = multi_params.get("Is_translate", False)
                        Is_emotion = multi_params.get("Is_emotion", False)
                except json.JSONDecodeError:
                    error_response = {
                        "error": "multi_params格式错误",
                        "ret_code": "400002"
                    }
                    await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                    continue
            
            # 确定输出节点
            output_nodes = []
            if Is_translate:
                output_nodes = ["translate_output_node"]
            else:
                output_nodes = ["airport_assistant_node", "flight_assistant_node", "chitchat_node","business_assistant_node"]
            
            try:
                threads = {
                    "configurable": {
                        "passenger_id": cid,
                        "thread_id": cid,
                        "token": token,
                        "Is_translate": Is_translate,
                        "Is_emotion": Is_emotion
                    }
                }
                
                logger.info(f"WebSocket用户输入: {query_txt}")
                
                # 发送开始事件
                start_response = {
                    "event": "start",
                    "cid": cid,
                    "msgid": msgid
                }
                await websocket.send_text(json.dumps(start_response, ensure_ascii=False))
                
                response_data = {
                    "ret_code": "000000",
                    "ret_msg": "操作成功",
                    "item": {
                        "cid": cid,
                        "msgid": msgid,
                        "answer_txt": "",
                        "answer_txt_type": "0"
                    }
                }
                
                # 处理聊天消息并流式发送结果
                async for node, result in graph_manager.process_chat_message(
                    message=query_txt,
                    thread_id=threads,
                    graph_id="airport_service_graph",
                    output_node=output_nodes
                ):
                    print(node, result)
                    if result and isinstance(result, str):
                        logger.debug(f"WebSocket结果内容: {result}")
                        
                        # 敏感词过滤
                        for sensitive_keyword in ["lookup_airport_policy", "search_flights"]:
                            if sensitive_keyword in result:
                                result = "xxx"
                                break
                        
                        response_data["item"]["answer_txt"] = result
                        await websocket.send_text(json.dumps(response_data, ensure_ascii=False))
                        await asyncio.sleep(0)
                
                # 发送结束事件
                end_response = {
                    "event": "end",
                    "cid": cid,
                    "msgid": msgid
                }
                await websocket.send_text(json.dumps(end_response, ensure_ascii=False))
                
            except Exception as e:
                logger.error(f"WebSocket chat error: {str(e)}", exc_info=True)
                error_response = {
                    "ret_code": "000000",
                    "ret_msg": "操作成功",
                    "item": {
                        "cid": cid,
                        "msgid": msgid,
                        "answer_txt": "刚刚服务在忙，请您重新提问。",
                        "answer_txt_type": "0"
                    }
                }
                await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                
    except WebSocketDisconnect:
        logger.info("WebSocket connection disconnected")
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}", exc_info=True)
        try:
            await websocket.close()
        except:
            pass 

class EventGenerator:
    """事件生成器，负责生成符合协议的事件流"""
    
    def __init__(self):
        self.sequence = 0
        self.timestamp = int(time.time() * 1000)
    
    def _next_sequence(self) -> int:
        """获取下一个序号"""
        self.sequence += 1
        return self.sequence
    
    def _generate_id(self, event_type: str, suffix: str = "") -> str:
        """生成事件ID"""
        timestamp = int(time.time() * 1000)
        if suffix:
            return f"{event_type}-{timestamp}-{suffix}"
        return f"{event_type}-{timestamp}-{self._next_sequence()}"
    
    def create_text_event(self, text: str, format_type: str = "plain") -> ChatEvent:
        """创建文本事件"""
        return ChatEvent(
            id=self._generate_id("text"),
            sequence=self._next_sequence(),
            content=TextEventContent(text=text, format=format_type)
        )
    

    
    def create_form_event(
        self,
        form_id: str,
        title: str,
        action: str,
        fields: list,
        buttons: list,
        description: str = None
    ) -> ChatEvent:
        """创建表单事件"""
        from models.schemas import FormField, FormButton
        
        fields_obj = [FormField(**field) for field in fields]
        buttons_obj = [FormButton(**button) for button in buttons]
        
        return ChatEvent(
            id=self._generate_id("form", form_id.split('-')[0] if '-' in form_id else form_id),
            sequence=self._next_sequence(),
            content=FormEventContent(
                form_id=form_id,
                title=title,
                description=description,
                action=action,
                fields=fields_obj,
                buttons=buttons_obj
            )
        )
    
    def create_end_event(self, suggestions: list = None, metadata: dict = None) -> ChatEvent:
        """创建结束事件"""
        return ChatEvent(
            id=self._generate_id("end"),
            sequence=self._next_sequence(),
            content=EndEventContent(suggestions=suggestions, metadata=metadata)
        )
    
    def create_error_event(self, error_code: str, error_message: str) -> ChatEvent:
        """创建错误事件"""
        return ChatEvent(
            id=self._generate_id("error", error_code),
            sequence=self._next_sequence(),
            content=ErrorEventContent(error_code=error_code, error_message=error_message)
        )


# 新增机场聊天接口路由
airport_router = APIRouter(prefix="/api/v1/airport-assistant", tags=["机场智能助手"])

@airport_router.post("/chat", response_model=None)
async def airport_chat(chat_request: AirportChatRequest, request: Request):
    """
    机场智能客服聊天接口
    基于LangGraph框架设计，支持多种响应类型的流式输出
    """
    logger.info(f"收到机场聊天请求 - ThreadID: {chat_request.thread_id}, UserID: {chat_request.user_id}, Query: {chat_request.query}")
    
    # 验证必要字段
    if not chat_request.thread_id or not chat_request.user_id or not chat_request.query:
        logger.error("机场聊天请求缺少必要字段")
        raise HTTPException(status_code=400, detail="必要字段缺失")
    
    # 获取请求头中的token
    token = request.headers.get("token", "")
    
    # 处理metadata，提取系统参数
    metadata = chat_request.metadata or {}
    Is_translate = metadata.get("Is_translate", False)
    Is_emotion = metadata.get("Is_emotion", False)
    
    async def event_generator():
        """事件生成器"""
        event_gen = EventGenerator()
        
        try:
            # 构建线程配置
            threads = {
                "configurable": {
                    "passenger_id": chat_request.user_id,
                    "thread_id": chat_request.thread_id,
                    "token": token,
                    "Is_translate": Is_translate,
                    "Is_emotion": Is_emotion
                }
            }
            # 确定输出节点
            output_nodes = ["airport_assistant_node", "flight_assistant_node", "chitchat_node", "business_assistant_node"]
            logger.info(f"机场聊天流用户输入: {chat_request.query}")
            async for node, result in graph_manager.process_chat_message(
                message=chat_request.query,
                thread_id=threads,
                graph_id="airport_service_graph",
                output_node=output_nodes
            ):
                logger.info(f"节点 {node} 返回结果: {result}")
                
                if result and isinstance(result, str):                    
                    # 根据节点类型创建不同类型的事件
                    if "business_assistant_node" in node:
                        # 业务节点 - 解析表单结构
                        try:
                            # 尝试解析JSON结构的表单数据
                            form_data = json.loads(result)
                            if form_data.get("type") == "form":
                                # 生成表单事件
                                form_event = event_gen.create_form_event(
                                    form_id=f"business-{int(time.time())}",
                                    title=form_data.get("title", "业务办理"),
                                    description=form_data.get("description", ""),
                                    action=form_data.get("action", "/api/v1/forms/submit"),
                                    fields=form_data.get("fields", []),
                                    buttons=form_data.get("buttons", [])
                                )
                                
                                # 如果有服务说明，先发送文本事件
                                if form_data.get("info", {}).get("service_description"):
                                    text_event = event_gen.create_text_event(
                                        form_data["info"]["service_description"], "plain"
                                    )
                                    yield f"event: text\n"
                                    yield f"data: {json.dumps(text_event.dict(), ensure_ascii=False)}\n\n"
                                    await asyncio.sleep(0.01)
                                
                                # 发送表单事件
                                yield f"event: form\n"
                                yield f"data: {json.dumps(form_event.dict(), ensure_ascii=False)}\n\n"
                                continue  # 跳过后面的文本事件发送
                            else:
                                # 不是表单结构，按普通文本处理
                                text_event = event_gen.create_text_event(result)
                        except json.JSONDecodeError:
                            # JSON解析失败，按普通文本处理
                            text_event = event_gen.create_text_event(result)
                    else:
                        # 其他节点 - 默认文本事件
                        text_event = event_gen.create_text_event(result)
                    
                    # 发送文本事件
                    yield f"event: text\n"
                    yield f"data: {json.dumps(text_event.dict(), ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.01)  # 控制流式输出速度
                
                # 处理结构化数据（如果有） - 转换为文本显示
                elif result and isinstance(result, dict):
                    # 将结构化数据转换为可读的文本格式
                    text_content = json.dumps(result, ensure_ascii=False, indent=2)
                    text_event = event_gen.create_text_event(text_content, "markdown")
                    
                    yield f"event: text\n"
                    yield f"data: {json.dumps(text_event.dict(), ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.01)
            
            # 发送结束事件
            end_event = event_gen.create_end_event(
                suggestions=["查询行李规定", "值机办理", "航班动态"],
                metadata={"processing_time": "1.2s"}
            )
            yield f"event: end\n"
            yield f"data: {json.dumps(end_event.dict(), ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"机场聊天处理异常: {str(e)}", exc_info=True)
            
            # 发送错误事件
            error_event = event_gen.create_error_event(
                error_code="service_unavailable",
                error_message="服务暂时不可用，请稍后再试"
            )
            yield f"event: error\n"
            yield f"data: {json.dumps(error_event.dict(), ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    ) 
airport_router = APIRouter(prefix="/api/v1/airport-assistant", tags=["机场智能助手"])
@airport_router.websocket("/chat/ws")
async def airport_chat_websocket(websocket: WebSocket):
    """
    机场智能客服 WebSocket 聊天接口
    与 HTTP SSE 接口功能完全一致，支持相同的事件类型和响应格式
    """
    await websocket.accept()    
    try:
        while True:
            # 接收客户端消息
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"❌ WebSocket JSON解析失败: {e}")
                error_response = {
                    "event": "error",
                    "data": {
                        "id": f"error-json-{int(time.time() * 1000)}",
                        "sequence": 1,
                        "content": {
                            "error_code": "invalid_json",
                            "error_message": "请求格式错误，请发送有效的JSON数据"
                        }
                    }
                }
                await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                continue
            
            # 提取并验证必要字段
            thread_id = message_data.get("thread_id")
            user_id = message_data.get("user_id") 
            query = message_data.get("query")
            metadata = message_data.get("metadata", {})
            token = message_data.get("token", "")
                        
            if not thread_id or not user_id or not query:
                logger.warning("❌ WebSocket 请求缺少必要字段")
                event_gen = EventGenerator()
                error_event = event_gen.create_error_event(
                    error_code="missing_fields",
                    error_message="必要字段缺失：thread_id, user_id, query"
                )
                error_response = {
                    "event": "error",
                    "data": error_event.dict()
                }
                await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                continue
            
            # 处理 metadata，提取系统参数
            Is_translate = metadata.get("Is_translate", False)
            Is_emotion = metadata.get("Is_emotion", False)
            logger.info(f"🔍 WebSocket 收到 metadata: {metadata}")
            # 创建事件生成器
            event_gen = EventGenerator()
            
            try:
                # 构建线程配置
                threads = {
                    "configurable": {
                        "passenger_id": user_id,
                        "thread_id": thread_id,
                        "token": token,
                        "Is_translate": Is_translate,
                        "Is_emotion": Is_emotion
                    }
                }
                # 确定输出节点
                output_nodes = ["airport_assistant_node", "flight_assistant_node", "chitchat_node", "business_assistant_node"]           
                # 发送开始事件（与原始接口保持一致）
                start_response = {
                    "event": "start",
                    "thread_id": thread_id,
                    "user_id": user_id
                }
                await websocket.send_text(json.dumps(start_response, ensure_ascii=False))                
                # 处理聊天消息并发送事件
                result_count = 0
                async for node, result in graph_manager.process_chat_message(
                    message=query,
                    thread_id=threads,
                    graph_id="airport_service_graph",
                    output_node=output_nodes
                ):
                    result_count += 1                    
                    if result and isinstance(result, str):                    
                        # 根据节点类型创建不同类型的事件
                        if "business_assistant_node" in node:
                            # 业务节点 - 解析表单结构
                            try:
                                # 尝试解析JSON结构的表单数据
                                form_data = json.loads(result)
                                if form_data.get("type") == "form":
                                    # 如果有服务说明，先发送文本事件
                                    if form_data.get("info", {}).get("service_description"):
                                        text_event = event_gen.create_text_event(
                                            form_data["info"]["service_description"], "plain"
                                        )
                                        text_response = {
                                            "event": "text",
                                            "data": text_event.dict()
                                        }
                                        await websocket.send_text(json.dumps(text_response, ensure_ascii=False))
                                        await asyncio.sleep(0.01)
                                    
                                    # 生成表单事件
                                    form_event = event_gen.create_form_event(
                                        form_id=f"business-{int(time.time())}",
                                        title=form_data.get("title", "业务办理"),
                                        description=form_data.get("description", ""),
                                        action=form_data.get("action", "/api/v1/forms/submit"),
                                        fields=form_data.get("fields", []),
                                        buttons=form_data.get("buttons", [])
                                    )
                                    
                                    # 发送表单事件
                                    form_response = {
                                        "event": "form",
                                        "data": form_event.dict()
                                    }
                                    await websocket.send_text(json.dumps(form_response, ensure_ascii=False))
                                    logger.info("✅ WebSocket 发送了表单事件")
                                    continue  # 跳过后面的文本事件发送
                                else:
                                    # 不是表单结构，按普通文本处理
                                    text_event = event_gen.create_text_event(result)
                            except json.JSONDecodeError:
                                # JSON解析失败，按普通文本处理
                                text_event = event_gen.create_text_event(result)
                        else:
                            # 其他节点 - 默认文本事件
                            text_event = event_gen.create_text_event(result)
                        
                        # 发送文本事件
                        text_response = {
                            "event": "text",
                            "data": text_event.dict()
                        }
                        await websocket.send_text(json.dumps(text_response, ensure_ascii=False))
                        # await asyncio.sleep(0.01)  # 控制流式输出速度
                    
                    # 处理结构化数据（如果有） - 转换为文本显示
                    elif result and isinstance(result, dict):
                        # 将结构化数据转换为可读的文本格式
                        text_content = json.dumps(result, ensure_ascii=False, indent=2)
                        text_event = event_gen.create_text_event(text_content, "markdown")
                        
                        text_response = {
                            "event": "text",
                            "data": text_event.dict()
                        }
                        await websocket.send_text(json.dumps(text_response, ensure_ascii=False))
                        logger.info("✅ WebSocket 发送了结构化数据文本事件")
                        await asyncio.sleep(0.01)                
                # 发送结束事件
                end_event = event_gen.create_end_event(
                    suggestions=["查询行李规定", "值机办理", "航班动态"],
                    metadata={"processing_time": "1.2s", "results_count": result_count}
                )
                end_response = {
                    "event": "end",
                    "data": end_event.dict()
                }
                await websocket.send_text(json.dumps(end_response, ensure_ascii=False))
                logger.info("✅ WebSocket 发送了结束事件")
                
            except Exception as e:
                logger.error(f"机场 WebSocket 聊天处理异常: {str(e)}", exc_info=True)
                
                # 发送错误事件
                error_event = event_gen.create_error_event(
                    error_code="service_unavailable",
                    error_message="服务暂时不可用，请稍后再试"
                )
                error_response = {
                    "event": "error",
                    "data": error_event.dict()
                }
                await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                
    except WebSocketDisconnect:
        logger.info("机场智能客服 WebSocket 连接已断开")
    except Exception as e:
        logger.error(f"机场智能客服 WebSocket 连接异常: {str(e)}", exc_info=True)
        try:
            await websocket.close()
        except:
            pass 