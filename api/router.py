from fastapi import APIRouter
from .chat import router as chat_router
from .summary import router as summary_router

api_router = APIRouter()
api_router.include_router(chat_router)
api_router.include_router(summary_router) 