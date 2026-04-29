from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient

from app.shared.api.middleware.debug_http import DebugHttpLoggingMiddleware
from app.shared.api.errors.handlers import setup_exception_handlers
from app.shared.api.main import api_router
from app.shared.db.config import settings
from app.shared.core.logger import log
from app.shared.core.mongo_client import set_mongo_client
from app.shared.infrastructure import initialize_infrastructure, shutdown_infrastructure
from app.shared.infrastructure.bootstrap import initialize_beanie, validate_workflow_consistency


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用生命周期钩子：统一管理 Mongo 连接和 Beanie 初始化
    log.info("正在连接 MongoDB...")

    client = AsyncMongoClient(settings.MONGO_URI)

    try:
        await client.admin.command('ping')
        log.success("MongoDB 连接成功")

        # 注入全局 Mongo 客户端，供需要底层访问或事务的代码使用
        set_mongo_client(client)

        # 初始化 Beanie ODM，注册所有文档模型并确保索引
        await initialize_beanie(client[settings.MONGO_DB_NAME])
        log.success("Beanie ODM 初始化完成")
        await validate_workflow_consistency()
        log.success("Workflow 配置一致性校验通过")

        log.success("FastAPI 服务启动完成")

        # Phase 6: 初始化应用级基础设施
        log.info("正在初始化应用级基础设施...")
        await initialize_infrastructure()
        log.success("应用级基础设施初始化完成")

        yield
    finally:
        log.info("FastAPI 服务已关闭")

        # Phase 6: 关闭应用级基础设施
        log.info("正在关闭应用级基础设施...")
        await shutdown_infrastructure()
        log.info("应用级基础设施已关闭")

        if client:
            close_result = client.close()
            if hasattr(close_result, "__await__"):
                await close_result
        set_mongo_client(None)
        log.info("MongoDB 连接已关闭")


app = FastAPI(
    title="Workflow API (MongoDB)",
    description="配置驱动的工作流状态机服务 - MongoDB 版本",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 与中间件、错误处理和业务路由都在这里统一挂载
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.APP_DEBUG:
    app.add_middleware(DebugHttpLoggingMiddleware)

setup_exception_handlers(app)

app.include_router(api_router)


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
