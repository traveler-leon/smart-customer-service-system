from fastapi import APIRouter
from .chat import airport_router
from .summary import router as summary_router
from .text2sql_training import router as text2sql_training_router
from .image_upload import image_router
from .question_recommend import router as question_recommend_router
from .business_recommend import router as business_recommend_router
from .memory_management import router as memory_management_router

api_router = APIRouter()
api_router.include_router(airport_router)
api_router.include_router(summary_router)
api_router.include_router(text2sql_training_router)
api_router.include_router(image_router)
api_router.include_router(question_recommend_router)
api_router.include_router(business_recommend_router)
api_router.include_router(memory_management_router)