from fastapi import APIRouter, HTTPException, Request, Response

from models import SummaryRequest, HumanAgentSummaryRequest
from agents.airport_service import graph_manager
from agents.airport_service.main_nodes.summary import summarize_human_agent_conversation
from common.logging import get_logger

# 使用专门的API摘要日志记录器
logger = get_logger("api.summary")

router = APIRouter(prefix="/chat/v1", tags=["摘要"])

@router.post("/summary")
async def get_conversation_summary(summary_req: SummaryRequest, request: Request, response: Response):
    logger.info(f"收到对话摘要请求 - CID: {summary_req.cid}, MSGID: {summary_req.msgid}")

    if not summary_req.cid or not summary_req.msgid:
        logger.error("摘要请求缺少必要字段")
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

@router.post("/human-agent-summary")
async def get_human_agent_conversation_summary(summary_req: HumanAgentSummaryRequest, request: Request, response: Response):
    if not summary_req.cid or not summary_req.msgid or not summary_req.conversation_list:
        raise HTTPException(status_code=400, detail="必要字段缺失")
    token = request.headers.get("token", "")
    if token:
        response.headers["token"] = token
    try:
        # 调用人工坐席摘要总结函数
        result = await summarize_human_agent_conversation(summary_req.conversation_list)
        return {
            "ret_code": "000000",
            "ret_msg": "操作成功",
            "item": {
                "cid": summary_req.cid,
                "msgid": summary_req.msgid,
                "answer_txt": result["summary"],
                "answer_txt_type": "0"
            }
        }
    except Exception as e:
        logger.error(f"获取人工坐席摘要出错: {str(e)}", exc_info=True)
        return {
            "ret_code": "999999",
            "ret_msg": "获取人工坐席摘要失败",
            "item": {
                "cid": summary_req.cid,
                "msgid": summary_req.msgid,
                "answer_txt": "获取人工坐席对话摘要失败，请稍后再试。",
                "answer_txt_type": "0"
            }
        } 