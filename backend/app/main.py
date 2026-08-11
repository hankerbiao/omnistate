import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pathlib import Path

from pymongo import AsyncMongoClient

from app.shared.api.errors.handlers import setup_exception_handlers
from app.shared.api.main import api_router
from app.shared.api.routes import health_router, metrics_router
from app.shared.config import clear_runtime_settings, get_bootstrap_settings
from app.shared.core.logger import log
from app.shared.core.mongo_client import set_mongo_client
from app.shared.core.startup_diagnostics import (
    log_bootstrap_diagnostics,
    log_runtime_diagnostics,
)
from app.shared.infrastructure import initialize_infrastructure, shutdown_infrastructure
from app.shared.infrastructure.bootstrap import initialize_beanie, validate_workflow_consistency
from app.shared.kafka.health import check_kafka_health
from app.shared.middleware import RequestLoggingMiddleware, AuditLogMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用生命周期钩子：统一管理 Mongo 连接和 Beanie 初始化
    bootstrap_settings = get_bootstrap_settings()
    log_bootstrap_diagnostics(bootstrap_settings)
    log.info("正在连接 MongoDB...")

    mongo_cfg = bootstrap_settings.mongodb
    client = AsyncMongoClient(mongo_cfg.uri)

    runtime_loaded = False
    try:
        await client.admin.command('ping')
        log.success("MongoDB 连接成功")

        # 注入全局 Mongo 客户端，供需要底层访问或事务的代码使用
        set_mongo_client(client)

        # 初始化 Beanie ODM，注册所有文档模型并确保索引
        await initialize_beanie(client[mongo_cfg.db_name])
        log.success("Beanie ODM 初始化完成")

        from app.modules.system_config.service import ConfigService

        runtime_settings = await ConfigService.load_runtime_settings()
        runtime_loaded = True
        log.success("MongoDB 运行配置加载完成")
        log_runtime_diagnostics(runtime_settings)

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

        # 初始化 Redis 连接池（非阻塞：超时或失败不阻断服务启动）
        try:
            from app.shared.redis.service import init_redis
            import concurrent.futures
            _executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            _fut = _executor.submit(init_redis)
            try:
                _fut.result(timeout=8)
                log.success("Redis 连接池初始化完成")
            except concurrent.futures.TimeoutError:
                log.warning("Redis 连接池初始化超时（非阻塞，将继续启动）")
            except Exception as e:
                log.warning("Redis 连接池初始化失败（非阻塞，将继续启动）: {}", e)
            finally:
                _executor.shutdown(wait=False)
        except Exception as e:
            log.warning("Redis 连接池初始化异常（非阻塞）: {}", e)

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

        if runtime_loaded:
            # 注销 Redis 服务注册并停止心跳（安全：未初始化时自动跳过）
            try:
                from app.shared.redis.service import unregister_service, stop_heartbeat
                stop_heartbeat()
                unregister_service()
                log.info("Redis 服务注册已注销")
            except Exception as e:
                log.debug("Redis 关闭（可忽略）: {}", e)

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
        clear_runtime_settings()
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
    allow_origins=get_bootstrap_settings().app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 全链路追踪中间件（始终启用，不受 APP_DEBUG 控制）
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(AuditLogMiddleware)

setup_exception_handlers(app)

app.include_router(api_router)
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(metrics_router, prefix="/health", tags=["Health"])


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

    settings = get_bootstrap_settings()
    environment = os.getenv("DML_ENV", "production").strip().lower()
    reload_enabled = environment == "dev" and settings.app.debug
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=reload_enabled,
    )


if __name__ == "__main__":
    main()
