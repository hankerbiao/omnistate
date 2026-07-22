"""FastAPI 应用装配入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import GatewaySettings
from .common.container import GatewayContainer
from .common.logging_utils import configure_logging, logger
from .domain.models import APIResponse
from .api.console import create_console_router
from .api.gateway import create_gateway_router


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    """创建开放平台网关应用。"""
    container = GatewayContainer.build(settings)
    settings = container.settings
    configure_logging(settings.log_level, log_file=settings.log_file)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "gateway_started host={} port={} upstreams={} db={}",
            settings.host,
            settings.port,
            ",".join(settings.upstream_base_urls),
            container.repository.describe(),
        )
        try:
            yield
        finally:
            await container.upstream_client.close()
            container.repository.close()
            logger.info("gateway_stopped")

    app = FastAPI(
        title="DML V4 Open Platform Gateway",
        version="1.0.0",
        description="开放平台网关服务，提供路由转发、请求过滤、负载均衡、鉴权认证与审计日志。",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+):(3000|3001|3100|8808|8809)$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(create_console_router(container))
    app.include_router(create_gateway_router(container))

    @app.exception_handler(Exception)
    async def unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("gateway_unhandled_error error_type={}", type(exc).__name__)
        payload = APIResponse(
            code=500, message="Internal gateway error", data={"error": "INTERNAL_GATEWAY_ERROR"}
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    return app


app = create_app()
