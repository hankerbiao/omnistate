"""开放 API 网关路由。

本模块只负责把请求交给 :class:`~core.pipeline.GatewayPipeline`，
并把管线抛出的 :class:`~domain.errors.GatewayError` 统一封装为网关错误响应。
所有业务阶段（匹配 / 鉴权 / 转发 / 日志）都在 ``core.pipeline`` 内，
错误码与诊断映射集中在 ``common.responses``，本文件不再内联任何错误构造。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..common.container import GatewayContainer
from ..domain.errors import GatewayError
from ..common.logging_utils import logger, request_context, request_log_fields
from ..common.responses import build_gateway_error_response, gateway_error_payload, request_id_from


def create_gateway_router(container: GatewayContainer) -> APIRouter:
    router = APIRouter(tags=["open-api-gateway"])

    @router.api_route("/api/v1/open/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def proxy(request: Request):
        request_id = request_id_from(request)
        with request_context(**request_log_fields(request, request_id)):
            try:
                return await container.pipeline.handle(request)
            except GatewayError as exc:
                logger.warning(
                    "gateway_rejected status={} error_code={} detail={}",
                    exc.status_code,
                    exc.error_code,
                    exc.message,
                )
                return build_gateway_error_response(
                    request_id=request_id,
                    status_code=exc.status_code,
                    payload=gateway_error_payload(
                        status_code=exc.status_code, message=exc.message, error_code=exc.error_code
                    ),
                )

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return router
