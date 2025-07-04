import os
import asyncio
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import warnings

from agents.airport_service import graph_manager, build_airport_service_graph
from common.logging import setup_logger, get_logger
from config.factory import get_logger_config, get_app_config, get_directories_config, get_graph_config
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

    # 注册自定义图
    graph_config = get_graph_config()
    graph_name = graph_config.get("name", "airport_service_graph")
    graph_manager.register_graph(graph_name, build_airport_service_graph())
    logger.info("Application started")
    yield
    # 关闭事件
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

# 注册API路由
app.include_router(api_router)

# 添加一个用于查看图结构的辅助函数
def view_graph():
    try:
        graph = build_airport_service_graph()
        graph_image = graph.compile().get_graph().draw_mermaid_png()
        with open("main_graph1.png", "wb") as f:
            f.write(graph_image)
    except Exception as e:
        logger.error(f"Error generating graph: {e}")

if __name__ == "__main__":
    import uvicorn
    view_graph()
    host = app_config.get("host", "0.0.0.0")
    port = app_config.get("port", 8081)
    uvicorn.run("main:app", host=host, port=port)
