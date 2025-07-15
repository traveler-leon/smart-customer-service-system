import json
import asyncio
import time
import os
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from models.schemas import (
    TextEventContent, FormEventContent, FlightListEventContent, FlightInfo, EndEventContent, ErrorEventContent, ChatEvent
)
from agents.airport_service import graph_manager
from common.logging import get_logger

# 使用专门的API聊天日志记录器
logger = get_logger("api.chat")

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
    
    def create_flight_list_event(
        self,
        title: str,
        flights: list,
        action_hint: str = None
    ) -> ChatEvent:
        """创建航班列表事件"""
        flights_obj = [FlightInfo(**flight) for flight in flights]
        
        return ChatEvent(
            id=self._generate_id("flight_list"),
            sequence=self._next_sequence(),
            content=FlightListEventContent(
                title=title,
                flights=flights_obj,
                action_hint=action_hint
            )
        )

# 新增机场聊天接口路由
airport_router = APIRouter(prefix="/api/v1/airport-assistant", tags=["机场智能助手"])
@airport_router.websocket("/chat/ws")
async def airport_chat_websocket(websocket: WebSocket):
    await websocket.accept()    
    try:
        while True:
            try:
                message_data = await websocket.receive_json()
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
            query = message_data.get("query", "")
            image_data = message_data.get("image", None)
            metadata = message_data.get("metadata", {})
            token = message_data.get("token", "")
            Is_translate = metadata.get("Is_translate", False)
            Is_emotion = metadata.get("Is_emotion", False)
            # Is_emotion = True
            # Is_translate = True
            
            # 检查是否提供了query或image中的至少一项
            if not thread_id or not user_id or (not query and not image_data):
                logger.warning("❌ WebSocket 请求缺少必要字段")
                event_gen = EventGenerator()
                error_event = event_gen.create_error_event(
                    error_code="missing_fields",
                    error_message="必要字段缺失：thread_id, user_id, 以及query或image至少需要一项"
                )
                error_response = {
                    "event": "error",
                    "data": error_event.dict()
                }
                await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                continue
            event_gen = EventGenerator()
            try:
                # 构建线程配置
                threads = {
                    "configurable": {
                        "passenger_id": user_id,
                        "thread_id": thread_id,
                        "user_query": query,
                        # "image_url": image_url,  # 添加图片URL
                        "image_data": image_data,
                        "token": token,
                        "Is_translate": Is_translate,
                        "Is_emotion": Is_emotion
                    }
                }
                if Is_translate:
                    output_nodes = ["translate_output_node"]
                else:
                    output_nodes = ["airport_assistant_node", "flight_assistant_node", "chitchat_node", "business_assistant_node","transfer_to_human"]           
                
                # 发送开始事件（与原始接口保持一致）
                start_response = {
                    "event": "start",
                    "thread_id": thread_id,
                    "user_id": user_id
                }
                await websocket.send_text(json.dumps(start_response, ensure_ascii=False))
                
                # 处理聊天消息并发送事件
                result_count = 0
                async for msg_type, node, result in graph_manager.process_chat_message_stream(
                    message=query,
                    thread_id=threads,
                    graph_id="airport_service_graph",
                    output_node=output_nodes
                ):
                    result_count += 1                    
                    # 根据节点类型创建不同类型的事件
                    if node=="business_assistant_node":
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
                                        "data": text_event.model_dump()
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
                                    "data": form_event.model_dump()
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
                    
                    elif msg_type=="custom" and node=="flight_assistant_node":
                        # 处理航班信息
                        try:
                            flight_list_event = event_gen.create_flight_list_event(
                                title=result.get("title", "相关航班号信息"),
                                flights=result.get("data", []),
                                action_hint=result.get("action_hint")
                            )
                            flight_list_response = {
                                "event": "flight_list",
                                "data": flight_list_event.model_dump()
                            }
                            await websocket.send_text(json.dumps(flight_list_response, ensure_ascii=False))
                            logger.info("✅ WebSocket 发送了航班列表事件")
                            continue  # 跳过后面的文本事件发送

                        except json.JSONDecodeError:
                            # JSON解析失败，按普通文本处理
                            text_event = event_gen.create_text_event(result)
                    else:
                        # 其他节点 - 默认文本事件
                        text_event = event_gen.create_text_event(result)
                    
                    # 发送文本事件
                    text_response = {
                        "event": "text",
                        "data": text_event.model_dump()
                    }
                    await websocket.send_text(json.dumps(text_response, ensure_ascii=False))
                    # await asyncio.sleep(0.01)  # 控制流式输出速度
                                 
                # 发送结束事件
                end_event = event_gen.create_end_event(
                    suggestions=["查询行李规定", "值机办理", "航班动态"],
                    metadata={"processing_time": "1.2s", "results_count": result_count}
                )
                end_response = {
                    "event": "end",
                    "data": end_event.model_dump()
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
                    "data": error_event.model_dump()
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