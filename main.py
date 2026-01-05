from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from db.relational import init_db, init_mock_config, get_session
from core.logger import log
from api.main import api_router
from api.errors.handlers import setup_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库和配置"""
    log.info("正在初始化数据库...")
    init_db()

    log.info("正在初始化流程配置...")
    with get_session() as session:
        init_mock_config(session)

    log.success("FastAPI 服务启动完成")
    yield
    log.info("FastAPI 服务已关闭")


app = FastAPI(
    title="Workflow API",
    description="配置驱动的工作流状态机服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置全局异常处理器
setup_exception_handlers(app)

# 注册 API 路由
app.include_router(api_router)


@app.get("/", summary="健康检查")
def root():
    """服务健康检查端点"""
    return {"status": "ok", "message": "Workflow API 服务运行中"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
