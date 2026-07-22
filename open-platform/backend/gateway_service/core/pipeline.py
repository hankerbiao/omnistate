"""网关请求处理管线。

把开放 API 请求处理流程拆分为独立阶段：
``匹配 → 鉴权 → 执行能力 → 写日志``

每个阶段是独立方法，便于单独单测与插拔重排。
路由层只需要调用 :meth:`GatewayPipeline.handle`，并在 ``GatewayError`` 抛出时
用 ``responses.build_gateway_error_response`` 统一封装。
"""

from __future__ import annotations

import httpx
from fastapi import HTTPException, Request, Response, status

from ..domain.errors import GatewayError
from .load_balancer import LoadBalancer
from ..common.logging_utils import build_call_log, logger, now_ms, request_context, request_log_fields
from .capability_executor import CapabilityExecutor
from .matching import CapabilityMatcher, resolve_upstream_path
from ..domain.models import ApiKey, Capability
from ..infrastructure.repository import Repository
from ..common.responses import (
    diagnosis_for,
    error_code_for,
    gateway_error_payload,
    request_id_from,
)
from .security import GatewayAuth
from ..config import GatewaySettings
from ..infrastructure.upstream import UpstreamClient


class CapabilityRequestContext:
    """一次开放能力请求的上下文，在管线各阶段间传递并累积状态。"""

    def __init__(self, *, request: Request, request_id: str, body: bytes) -> None:
        self.request = request
        self.request_id = request_id
        self.body = body
        self.started_ms = now_ms()
        self.gateway_started = now_ms()
        self.authenticated: GatewayAuth | None = None
        self.authenticated_key: ApiKey | None = None
        self.upstream: str | None = None
        self.capability: Capability | None = None
        self.path_params: dict[str, str] = {}
        self.status_code = 500
        self.response_body: bytes | dict = {}
        self.error_code: str | None = None
        self.diagnosis: str | None = None
        self.result: Response | None = None


class GatewayPipeline:
    """开放 API 能力执行管线。"""

    def __init__(
        self,
        *,
        auth: GatewayAuth,
        matcher: CapabilityMatcher,
        load_balancer: LoadBalancer,
        upstream_client: UpstreamClient,
        repository: Repository,
        settings: GatewaySettings,
    ) -> None:
        self._auth = auth
        self._matcher = matcher
        self._load_balancer = load_balancer
        self._repository = repository
        self._executor = CapabilityExecutor(
            upstream_client=upstream_client,
            repository=repository,
            settings=settings,
        )

    async def handle(self, request: Request) -> Response:
        """执行完整开放能力请求，返回 Starlette ``Response``。"""
        request_id = request_id_from(request)
        body = await request.body()
        ctx = CapabilityRequestContext(request=request, request_id=request_id, body=body)
        with request_context(**request_log_fields(request, request_id)):
            client_host = ctx.request.client.host if ctx.request.client else "unknown"
            logger.debug("gateway_request_start client={}", client_host)
            try:
                self._match(ctx)
                self._authenticate(ctx)
                key = self._require_key(ctx)
                with logger.contextualize(key_id=key.id):
                    if self._executor.needs_upstream(self._require_capability(ctx)):
                        self._choose_upstream(ctx)
                    await self._execute_capability(ctx)
                return self._require_response(ctx)
            except httpx.RequestError:
                logger.exception(
                    "gateway_upstream_error path={}", request.url.path
                )
                self._fail(
                    ctx,
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    error_code="UPSTREAM_UNAVAILABLE",
                    message="Upstream service unavailable",
                    diagnosis="上游服务无法连接或响应超时，请稍后重试。",
                )
            except HTTPException as exc:
                self._fail(
                    ctx,
                    status_code=exc.status_code,
                    error_code=error_code_for(exc.status_code),
                    message=str(exc.detail),
                    diagnosis=diagnosis_for(exc.status_code),
                )
            finally:
                self._record(ctx)

    # ---- 各阶段 ----

    def _match(self, ctx: CapabilityRequestContext) -> None:
        match = self._matcher.match(ctx.request.method, ctx.request.url.path)
        if not match:
            logger.warning(
                "gateway_route_not_matched method={} path={}",
                ctx.request.method,
                ctx.request.url.path,
            )
            self._fail(
                ctx,
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=error_code_for(404),
                message="Open API route not found",
                diagnosis=diagnosis_for(404),
            )
        logger.debug(
            "gateway_matched capability={} scope={} path_params={}",
            match.capability.id,
            match.capability.scope,
            match.path_params,
        )
        ctx.capability = match.capability
        ctx.path_params = match.path_params

    def _authenticate(self, ctx: CapabilityRequestContext) -> None:
        authenticated = self._auth.authenticate(ctx.request)
        logger.debug(
            "gateway_authenticated key_id={} owner={} scopes={}",
            authenticated.key.id,
            authenticated.key.ownerUserId,
            authenticated.key.scopes,
        )
        self._auth.require_scope(authenticated.key, self._require_capability(ctx).scope)
        ctx.authenticated = self._auth
        ctx.authenticated_key = authenticated.key

    def _choose_upstream(self, ctx: CapabilityRequestContext) -> None:
        upstream = self._load_balancer.choose()
        if not upstream:
            logger.error("gateway_no_upstream_available")
            self._fail(
                ctx,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code=error_code_for(503),
                message="All upstream services are unavailable",
                diagnosis=diagnosis_for(503),
            )
        logger.debug("gateway_upstream_selected upstream={}", upstream)
        ctx.upstream = upstream

    async def _execute_capability(self, ctx: CapabilityRequestContext) -> None:
        capability = self._require_capability(ctx)
        key = self._require_key(ctx)
        upstream_path = (
            resolve_upstream_path(capability, ctx.path_params)
            if self._executor.needs_upstream(capability) and capability.upstreamPath
            else "-"
        )
        logger.debug(
            "gateway_capability_begin capability={} handler={} upstream={} upstream_path={} key_id={}",
            capability.id,
            capability.handler,
            ctx.upstream,
            upstream_path,
            key.id,
        )
        result = await self._executor.execute(
            capability=capability,
            path_params=ctx.path_params,
            upstream_base_url=ctx.upstream,
            request=ctx.request,
            body=ctx.body,
            query_params=None,
            request_id=ctx.request_id,
            key=key,
        )

        ctx.status_code = result.status_code
        ctx.response_body = result.body

        self._repository.mark_key_used(key.id)
        logger.info(
            "gateway_capability_done capability={} status={} latency_ms={}",
            capability.id,
            result.status_code,
            result.latency_ms,
        )
        ctx.result = Response(
            content=result.body,
            status_code=result.status_code,
            headers=result.headers,
            media_type=result.headers.get("content-type"),
        )

    def _record(self, ctx: CapabilityRequestContext) -> None:
        gateway_latency = max(1, round(now_ms() - ctx.gateway_started))
        self._repository.add_log(
            build_call_log(
                request_id=ctx.request_id,
                request=ctx.request,
                key=ctx.authenticated_key,
                status_code=ctx.status_code,
                started_ms=ctx.started_ms,
                gateway_latency_ms=gateway_latency,
                request_body=ctx.body,
                response_body=ctx.response_body,
                error_code=ctx.error_code,
                diagnosis=ctx.diagnosis,
            )
        )

    @staticmethod
    def _fail(
        ctx: CapabilityRequestContext,
        *,
        status_code: int,
        error_code: str,
        message: str,
        diagnosis: str | None,
    ) -> None:
        ctx.status_code = status_code
        ctx.error_code = error_code
        ctx.diagnosis = diagnosis
        ctx.response_body = gateway_error_payload(
            status_code=status_code, message=message, error_code=error_code
        )
        raise GatewayError(status_code, error_code, message, diagnosis)

    @staticmethod
    def _require_capability(ctx: CapabilityRequestContext) -> Capability:
        if ctx.capability is None:
            raise RuntimeError("capability must be matched before execution")
        return ctx.capability

    @staticmethod
    def _require_key(ctx: CapabilityRequestContext) -> ApiKey:
        if ctx.authenticated_key is None:
            raise RuntimeError("request must be authenticated before execution")
        return ctx.authenticated_key

    @staticmethod
    def _require_response(ctx: CapabilityRequestContext) -> Response:
        if ctx.result is None:
            raise RuntimeError("capability execution produced no response")
        return ctx.result
