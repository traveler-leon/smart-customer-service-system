import json
import asyncio
import time
import os
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from models.schemas import (
    TextEventContent, RichContentEventContent, FormEventContent, FlightListEventContent, FlightInfo, EndEventContent, ErrorEventContent, ChatEvent
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
    
    def create_rich_content_event(self, text: str, images: str = None, format_type: str = "plain", layout: str = "text_first") -> ChatEvent:
        """创建富文本内容事件"""
        from models.schemas import RichContentImage
        
        # 处理图片数据 - images格式: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA/g||data:image/jpeg;base64,...'
        image_objects = []
        if images:
            # 按||分割图片数据
            image_parts = images.split('||')
            img_count = 0
            for image_part in image_parts:
                if image_part.strip():  # 确保不是空字符串
                    # 检查是否是完整的data URI格式: data:image/png;base64,数据
                    if image_part.startswith('data:') and ';base64,' in image_part:
                        # 分离content_type和数据部分
                        content_type_part, image_data = image_part.split(',', 1)
                        # 提取content_type: data:image/png;base64 -> image/png
                        content_type = content_type_part.replace('data:', '').replace(';base64', '')
                        
                        img_count += 1
                        image_obj = RichContentImage(
                            id=f"img-{img_count}",
                            content_type=content_type,
                            data=image_part,  # 保持完整的data URI格式
                            alt_text=f"图片{img_count}",
                            description=f"相关图片内容"
                        )
                        image_objects.append(image_obj)
        
        return ChatEvent(
            id=self._generate_id("rich"),
            sequence=self._next_sequence(),
            content=RichContentEventContent(
                text=text,
                format=format_type,
                images=image_objects if image_objects else None,
                layout=layout
            )
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
            
            # 提取技术环境信息字段
            query_source = metadata.get("query_source","小程序")
            query_device = metadata.get("query_device","手机")
            query_ip = metadata.get("query_ip","")
            network_type = metadata.get("network_type","5g")
            
            # 构建技术环境metadata
            technical_metadata = {}
            technical_metadata["query_source"] = query_source
            technical_metadata["query_device"] = query_device
            technical_metadata["query_ip"] = query_ip
            technical_metadata["network_type"] = network_type
            
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
                    "data": error_event.model_dump()
                }
                await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                continue
            event_gen = EventGenerator()
            try:
                # 构建线程配置
                threads = {
                    "configurable": {
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "user_query": query,
                        # "image_url": image_url,  # 添加图片URL
                        "image_data": image_data,
                        "token": token,
                        "Is_translate": Is_translate,
                        "Is_emotion": Is_emotion,
                        "metadata": technical_metadata
                    }
                }
                if Is_translate:
                    msg_nodes = ["translate_output_node"]
                    custom_nodes = []
                else:
                    msg_nodes = ["airport_assistant_node", "flight_assistant_node", "chitchat_node", "business_assistant_node","transfer_to_human"]           
                    custom_nodes = ["airport_info_search_node","flight_assistant_node","business_assistant_node"]
                
                # 发送开始事件（与原始接口保持一致）
                start_response = {
                    "event": "start",
                    "thread_id": thread_id,
                    "user_id": user_id
                }
                await websocket.send_text(json.dumps(start_response, ensure_ascii=False))                
                # 处理聊天消息并发送事件
                result_count = 0
                logger.info(f"3333333msg_nodes: {msg_nodes}")
                logger.info(f"4444444custom_nodes: {custom_nodes}")
                async for msg_type, node, result in graph_manager.process_chat_message_stream(
                    message=query,
                    thread_id=threads,
                    graph_id="airport_service_graph",
                    msg_nodes=msg_nodes,
                    custom_nodes=custom_nodes
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
                    elif msg_type=="custom" and node=="airport_info_search_node":
                        # 处理机场知识                        
                        # 尝试解析 qa 事件的 JSON 数据
                        try:
                            if result.get('type') == 'qa' and 'answer' in result:
                                answer = result.get('answer', '')
                                images = result.get('images', '')
                               
                                # 如果有图片数据，创建富文本事件
                                if images:
                                    rich_event = event_gen.create_rich_content_event(
                                        text=answer,
                                        images=images,
                                        format_type="plain",
                                        layout="text_first"
                                    )
                                    
                                    rich_response = {
                                        "event": "rich_content",
                                        "data": rich_event.model_dump()
                                    }
                                    await websocket.send_text(json.dumps(rich_response, ensure_ascii=False))
                                    logger.info("✅ WebSocket 发送了富文本内容事件")
                                    continue  # 跳过后面的文本事件发送
                                else:
                                    # 只有文本，创建普通文本事件
                                    text_event = event_gen.create_text_event(answer)
                            else:
                                # 不是qa结构或缺少answer，按普通文本处理
                                text_event = event_gen.create_text_event(result)
                        except json.JSONDecodeError:
                            # JSON解析失败，按普通文本处理
                            text_event = event_gen.create_text_event(result)
                    elif node=="transfer_to_human":
                        text_event = event_gen.create_text_event(result)
                        text_response = {
                            "event": "transfer_to_human",
                            "data": text_event.model_dump()
                        }
                        await websocket.send_text(json.dumps(text_response, ensure_ascii=False))
                        logger.info("✅ WebSocket 发送了转人工事件")
                        continue
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