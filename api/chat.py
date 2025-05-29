import json
import asyncio
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from models.schemas import UserInput
from agents.airport_service import graph_manager
from common.logging import get_logger

logger = get_logger("airport_service")

router = APIRouter(prefix="/chat/v1", tags=["聊天"])

@router.post("/stream", response_model=None)
async def chat_stream(user_input: UserInput, request: Request, response: Response):
    logger.info("Request headers:")
    for header_name, header_value in request.headers.items():
        logger.info(f"{header_name}: {header_value}")
    if not user_input.cid or not user_input.msgid or not user_input.query_txt:
        raise HTTPException(status_code=400, detail="必要字段缺失")
    if user_input.multi_params:
        try:
            if isinstance(user_input.multi_params, str):
                multi_params = json.loads(user_input.multi_params)
                Is_translate = multi_params.get("Is_translate", False)
                Is_emotion = multi_params.get("Is_emotion", False)
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
        output_nodes = ["router","airport_assistant_node", "flight_assistant_node", "chitchat_node"]
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