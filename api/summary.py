from fastapi import APIRouter, HTTPException, Request, Response

from models.schemas import SummaryRequest
from agents.airport_service import graph_manager
from common.logging import get_logger

logger = get_logger("airport_service")

router = APIRouter(prefix="/chat/v1", tags=["摘要"])

@router.post("/summary")
async def get_conversation_summary(summary_req: SummaryRequest, request: Request, response: Response):
    if not summary_req.cid or not summary_req.msgid:
        raise HTTPException(status_code=400, detail="必要字段缺失")
    token = request.headers.get("token", "")
    if token:
        response.headers["token"] = token
    try:
        threads = {
            "configurable": {
                "passenger_id": summary_req.cid,
                "thread_id": summary_req.cid,
                "token": token
            }
        }
        summary = await graph_manager.summarize_conversation(
            thread_id=threads,
            graph_id="airport_service_graph"
        )
        # print(summary)
        return {
            "ret_code": "000000",
            "ret_msg": "操作成功",
            "item": {
                "cid": summary_req.cid,
                "msgid": summary_req.msgid,
                "answer_txt": summary,
                "answer_txt_type": "0"
            }
        }
    except Exception as e:
        logger.error(f"获取摘要出错: {str(e)}", exc_info=True)
        return {
            "ret_code": "999999",
            "ret_msg": "获取摘要失败",
            "item": {
                "cid": summary_req.cid,
                "msgid": summary_req.msgid,
                "answer_txt": "获取对话摘要失败，请稍后再试。",
                "answer_txt_type": "0"
            }
        } 