import os
import asyncio
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import warnings

from agents.airport_service import graph_manager, build_airport_service_graph,build_question_recommend_graph,build_business_recommend_graph
from agents.airport_service.context_engineering.scheduler import start_memory_scheduler, stop_memory_scheduler
from agents.airport_service.context_engineering.memory_manager import memory_manager
from common.logging import setup_logger, get_logger
from config.factory import get_logger_config, get_app_config, get_directories_config
from api.router import api_router  # 导入API路由器

warnings.filterwarnings("ignore")

# 获取日志配置并设置日志
logger_config = get_logger_config()
setup_logger(**logger_config)
logger = get_logger("airport_service")

# Lifespan事件管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    # 确保必要目录存在
    directories_config = get_directories_config()
    os.makedirs(directories_config.get("logs", "logs"), exist_ok=True)
    
    # 确保上传图片目录存在
    # uploads_dir = os.path.join("static", "uploads")
    # os.makedirs(uploads_dir, exist_ok=True)

    # 注册自定义图
    try:
        logger.info("开始注册图...")
        graph_manager.register_graph("airport_service_graph", build_airport_service_graph())
        logger.info("成功注册 airport_service_graph")
        
        graph_manager.register_graph("question_recommend_graph", build_question_recommend_graph())
        logger.info("成功注册 question_recommend_graph")
        
        graph_manager.register_graph("business_recommend_graph", build_business_recommend_graph())
        logger.info("成功注册 business_recommend_graph")
        
        logger.info(f"所有图注册完成，当前已注册的图：{list(graph_manager._registered_graphs.keys())}")
    except Exception as e:
        logger.error(f"图注册失败：{e}", exc_info=True)
        raise
    
    # 启动记忆管理调度器
    # try:
    #     start_memory_scheduler()
    #     logger.info("记忆管理调度器已启动")
    # except Exception as e:
    #     logger.error(f"启动记忆管理调度器失败：{e}", exc_info=True)
    
    logger.info("Application started")
    yield
    # 关闭事件
    # try:
    #     stop_memory_scheduler()
    #     logger.info("记忆管理调度器已停止")
    # except Exception as e:
    #     logger.error(f"停止记忆管理调度器失败：{e}", exc_info=True)
    
    logger.info("Application shutting down")

# 获取应用配置
app_config = get_app_config()

app = FastAPI(
    title=app_config.get("title", "智能客户服务系统"),
    description=app_config.get("description", "机场智能客服API"),
    version=app_config.get("version", "1.0.0"),
    lifespan=lifespan
)

# 添加CORS中间件
cors_origins = app_config.get("cors_origins", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册API路由
app.include_router(api_router)

# 添加一个用于查看图结构的辅助函数
def view_graph():
    try:
        graph = build_airport_service_graph()
        # graph = build_business_recommend_graph()
        graph_image = graph.compile().get_graph().draw_mermaid_png()
        with open("main_grap2.png", "wb") as f:
            f.write(graph_image)
    except Exception as e:
        logger.error(f"Error generating graph: {e}")

if __name__ == "__main__":
    import uvicorn
    # view_graph()
    host = app_config.get("host", "0.0.0.0")
    port = app_config.get("port", 8081)
    uvicorn.run(app, host=host, port=port)  # 直接传递app对象而不是字符串
