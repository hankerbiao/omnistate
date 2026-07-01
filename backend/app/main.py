from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from pymongo import AsyncMongoClient

from app.shared.api.middleware.debug_http import DebugHttpLoggingMiddleware
from app.shared.api.errors.handlers import setup_exception_handlers
from app.shared.api.main import api_router
from app.shared.api.routes import health_router
from app.shared.config import get_settings
from app.shared.core.logger import log
from app.shared.core.mongo_client import set_mongo_client
from app.shared.infrastructure import initialize_infrastructure, shutdown_infrastructure
from app.shared.infrastructure.bootstrap import initialize_beanie, validate_workflow_consistency
from app.shared.kafka.health import check_kafka_health
from app.shared.middleware import RequestLoggingMiddleware, AuditLogMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用生命周期钩子：统一管理 Mongo 连接和 Beanie 初始化
    log.info("正在连接 MongoDB...")

    client = AsyncMongoClient(get_settings().mongodb.uri)

    try:
        await client.admin.command('ping')
        log.success("MongoDB 连接成功")

        # 注入全局 Mongo 客户端，供需要底层访问或事务的代码使用
        set_mongo_client(client)

        # 初始化 Beanie ODM，注册所有文档模型并确保索引
        await initialize_beanie(client[get_settings().mongodb.db_name])
        log.success("Beanie ODM 初始化完成")
        await validate_workflow_consistency()
        log.success("Workflow 配置一致性校验通过")

        # Kafka 基础设施检查（不阻塞启动）：Worker 心跳过期仅警告
        log.info("正在检查 Kafka 基础设施状态...")
        kafka_result = await check_kafka_health()
        if not kafka_result.healthy:
            log.warning(
                f"Kafka 基础设施不健康: {kafka_result.detail}\n"
                f"自动化执行结果将无法自动入库。仍可正常使用用例管理等其他功能。\n"
                f"如需执行自动化测试，请先启动 Kafka Worker: "
                f"python -m app.workers.kafka_worker_main"
            )
        else:
            log.success(f"Kafka 基础设施健康检查通过 ({kafka_result.detail})")

        log.success("FastAPI 服务启动完成")

        # Phase 6: 初始化应用级基础设施
        log.info("正在初始化应用级基础设施...")
        await initialize_infrastructure()
        log.success("应用级基础设施初始化完成")

        # 初始化系统默认配置（仅创建缺失项）
        from app.modules.system_config.service import ConfigService
        await ConfigService.init_default_configs()
        log.success("系统默认配置初始化完成")

        # 初始化 Redis 连接池
        from app.shared.redis.service import init_redis
        init_redis()
        log.success("Redis 连接池初始化完成")

        # 恢复未发送的通知批次
        from app.modules.notification.service import NotificationService
        try:
            await NotificationService.recover_pending()
            log.success("通知批次恢复完成")
        except Exception as e:
            log.warning("通知批次恢复失败（非阻塞）: {}", e)

        yield
    finally:
        log.info("FastAPI 服务已关闭")

        # 注销 Redis 服务注册并停止心跳
        from app.shared.redis.service import unregister_service, stop_heartbeat
        stop_heartbeat()
        unregister_service()
        log.info("Redis 服务注册已注销")

        # 刷新所有待处理的延迟通知
        from app.modules.notification.service import NotificationService
        await NotificationService.flush_all()
        log.info("待处理通知已全部发送")

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
    allow_origins=get_settings().app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 全链路追踪中间件（始终启用，不受 APP_DEBUG 控制）
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(AuditLogMiddleware)

# 调试模式的 HTTP 详细日志中间件（仅 debug 模式开启）
if get_settings().app.debug:
    app.add_middleware(DebugHttpLoggingMiddleware)

setup_exception_handlers(app)

app.include_router(api_router)
app.include_router(health_router, prefix="/health", tags=["Health"])


# ── AI 发现文件 ──────────────────────────────────────────────

_LLMS_TXT_PATH = Path(__file__).resolve().parents[2] / "llms.txt"


@app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
async def serve_llms_txt():
    """提供 llms.txt — 项目级 AI 发现文件（标准格式，兼容 llmstxt.dev）。"""
    if _LLMS_TXT_PATH.exists():
        return PlainTextResponse(_LLMS_TXT_PATH.read_text(encoding="utf-8"))
    return PlainTextResponse("", status_code=404)


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def serve_robots_txt():
    """提供 robots.txt。"""
    return PlainTextResponse("User-agent: *\nAllow: /\nSitemap: /llms.txt\n")


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8801, reload=True)


if __name__ == "__main__":
    main()
