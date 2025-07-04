from fastapi import APIRouter
from .chat import router as chat_router, airport_router
from .summary import router as summary_router
from .text2sql_training import router as text2sql_training_router

api_router = APIRouter()
api_router.include_router(chat_router)
api_router.include_router(airport_router)
api_router.include_router(summary_router)
api_router.include_router(text2sql_training_router)