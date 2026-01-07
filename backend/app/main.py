from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.api.errors.handlers import setup_exception_handlers
from app.api.main import api_router
from app.db.config import settings
from app.core.logger import log
from app.core.mongo_client import set_mongo_client

from app.models import (
    SysWorkTypeDoc, SysWorkflowStateDoc, SysWorkflowConfigDoc,
    BusWorkItemDoc, BusFlowLogDoc
)


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
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[
                SysWorkTypeDoc,
                SysWorkflowStateDoc,
                SysWorkflowConfigDoc,
                BusWorkItemDoc,
                BusFlowLogDoc
            ]
        )
        log.success("Beanie ODM 初始化完成")

        log.success("FastAPI 服务启动完成")
        yield
    finally:
        log.info("FastAPI 服务已关闭")
        if client:
            client.close()
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

setup_exception_handlers(app)

app.include_router(api_router)


@app.get("/", summary="健康检查")
def root():
    # 简单健康检查，用于基础存活探测
    return {"status": "ok", "message": "Workflow API 服务运行中 (MongoDB)"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
