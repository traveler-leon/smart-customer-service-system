import os
import asyncio
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import warnings

from agents.airport_service import graph_manager, build_airport_service_graph
from common.logging import setup_logger, get_logger
from api.router import api_router  # 导入API路由器

warnings.filterwarnings("ignore")

# 设置日志
setup_logger(log_dir="logs", log_level="INFO")
logger = get_logger("airport_service")

# Lifespan事件管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    # 确保data目录存在
    os.makedirs("data", exist_ok=True)
    # 注册自定义图
    graph_manager.register_graph("airport_service_graph", build_airport_service_graph())
    logger.info("Application started")
    yield
    # 关闭事件
    logger.info("Application shutting down")

app = FastAPI(
    title="智能客户服务系统",
    description="机场智能客服API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        with open("main_graph.png", "wb") as f:
            f.write(graph_image)
    except Exception as e:
        logger.error(f"Error generating graph: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8081)
