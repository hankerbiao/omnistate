"""开放平台控制台 API。

只负责参数校验与编排，调试探测逻辑委托给 ``infrastructure.debug_probe.run_debug_probe``
（架构约束：本文件不得内联 httpx 探测与错误体构造）。
所有服务能力从 ``common.container.GatewayContainer`` 取用，新增能力无需改动函数签名。
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..core.catalog import CAPABILITIES, CAPABILITY_BY_ID
from ..common.container import GatewayContainer
from ..common.logging_utils import client_ip, logger, request_context
from ..infrastructure.debug_probe import run_debug_probe
from ..domain.models import (
    APIResponse,
    ChangePasswordRequest,
    ConsolePrincipal,
    CurrentUserCapabilitiesResponse,
    CreateConsoleUserRequest,
    CreateApiKeyRequest,
    DebugRequest,
    LoginRequest,
    LoginResponse,
    UpdateUserPermissionsRequest,
    UpdateUserQuotaRequest,
)
from ..infrastructure.repository import Repository
from ..core.security import GatewayAuth
from ..infrastructure.upstream import UpstreamClient


DEFAULT_INITIAL_PASSWORD = "123456"
DEFAULT_USER_TEAM = "未分组"
PASSWORD_CHANGE_PATH = "/api/v1/open-platform/change-password"


async def _console_log_context(request: Request) -> None:
    """为控制台请求注入统一日志上下文（FastAPI 异步依赖）。

    必须用 async 生成器：sync 依赖在独立线程执行，loguru 的 contextvar 无法
    传播到请求处理协程；async 生成器与 handler 同处一个任务，上下文才生效。
    """
    request_id = request.headers.get("x-request-id") or f"req_console_{secrets.token_hex(4)}"
    with request_context(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client_ip=client_ip(request),
        key_id="-",
    ):
        yield


def create_console_router(container: GatewayContainer) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/open-platform",
        tags=["open-platform-console"],
        dependencies=[Depends(_console_log_context)],
    )
    repository: Repository = container.repository
    auth: GatewayAuth = container.auth
    upstream_client: UpstreamClient = container.upstream_client
    upstreams = container.settings.upstream_base_urls
    console_token = container.settings.console_token

    def require_console(request: Request) -> ConsolePrincipal:
        if console_token:
            value = request.headers.get("x-console-token") or request.headers.get(
                "authorization", ""
            ).removeprefix("Bearer ")
            if value != console_token:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid console token")
        principal = _console_principal_from_request(request)
        if principal.user.mustChangePassword and request.url.path != PASSWORD_CHANGE_PATH:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required",
            )
        return principal

    def _console_principal_from_request(request: Request) -> ConsolePrincipal:
        user_id = request.headers.get("x-console-user-id", "user_admin").strip() or "user_admin"
        user = repository.get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid console user")
        return ConsolePrincipal(user=user)

    def require_admin(principal: ConsolePrincipal) -> None:
        if not principal.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")

    def require_key_visible(key_id: str, principal: ConsolePrincipal):
        key = repository.get_key(key_id)
        if not key or (principal.owner_filter and key.ownerUserId != principal.owner_filter):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
        return key

    def capabilities_for_user(principal: ConsolePrincipal):
        if principal.is_admin:
            return CAPABILITIES
        allowed = set(principal.user.allowedCapabilityIds)
        return [item for item in CAPABILITIES if item.id in allowed]

    @router.post("/login")
    async def login(input_data: LoginRequest) -> APIResponse:
        user = repository.verify_user_password(input_data.username, input_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        logger.info("console_login_success user_id={} username={}", user.id, user.username)
        return APIResponse(data=LoginResponse(user=user).model_dump())

    @router.get("/overview")
    async def overview(principal: ConsolePrincipal = Depends(require_console)) -> APIResponse:
        return APIResponse(data=repository.overview(owner_user_id=principal.owner_filter).model_dump())

    @router.get("/keys")
    async def list_keys(principal: ConsolePrincipal = Depends(require_console)) -> APIResponse:
        keys = repository.list_keys(owner_user_id=principal.owner_filter)
        return APIResponse(data=[key.model_dump() for key in keys])

    @router.get("/users")
    async def list_users(principal: ConsolePrincipal = Depends(require_console)) -> APIResponse:
        require_admin(principal)
        return APIResponse(data=[user.model_dump() for user in repository.list_users()])

    @router.get("/me/capabilities")
    async def current_user_capabilities(
        principal: ConsolePrincipal = Depends(require_console),
    ) -> APIResponse:
        response = CurrentUserCapabilitiesResponse(
            user=principal.user,
            capabilities=capabilities_for_user(principal),
        )
        return APIResponse(data=response.model_dump())

    @router.post("/users")
    async def create_user(
        input_data: CreateConsoleUserRequest,
        principal: ConsolePrincipal = Depends(require_console),
    ) -> APIResponse:
        require_admin(principal)
        try:
            created = repository.create_user(
                username=input_data.username,
                password=DEFAULT_INITIAL_PASSWORD,
                name=input_data.username.strip(),
                email="",
                role=input_data.role,
                team=DEFAULT_USER_TEAM,
                allowed_capability_ids=input_data.allowedCapabilityIds,
                quota=input_data.quota,
                must_change_password=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        logger.info(
            "console_user_created user_id={} username={} role={}",
            created.id,
            created.username,
            created.role,
        )
        return APIResponse(data=created.model_dump())

    @router.post("/change-password")
    async def change_password(
        input_data: ChangePasswordRequest,
        principal: ConsolePrincipal = Depends(require_console),
    ) -> APIResponse:
        if input_data.newPassword == DEFAULT_INITIAL_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must differ from default password",
            )
        if input_data.newPassword == input_data.oldPassword:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must differ from old password",
            )
        updated = repository.change_user_password(
            principal.user_id,
            input_data.oldPassword,
            input_data.newPassword,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid old password")
        logger.info("console_password_changed user_id={} username={}", updated.id, updated.username)
        return APIResponse(data=LoginResponse(user=updated).model_dump())

    @router.put("/users/{user_id}/permissions")
    async def update_user_permissions(
        user_id: str,
        input_data: UpdateUserPermissionsRequest,
        principal: ConsolePrincipal = Depends(require_console),
    ) -> APIResponse:
        require_admin(principal)
        updated = repository.update_user_permissions(user_id, input_data.allowedCapabilityIds)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return APIResponse(data=updated.model_dump())

    @router.put("/users/{user_id}/quota")
    async def update_user_quota(
        user_id: str,
        input_data: UpdateUserQuotaRequest,
        principal: ConsolePrincipal = Depends(require_console),
    ) -> APIResponse:
        require_admin(principal)
        updated = repository.update_user_quota(user_id, input_data.quota)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return APIResponse(data=updated.model_dump())

    @router.post("/keys")
    async def create_key(
        input_data: CreateApiKeyRequest,
        principal: ConsolePrincipal = Depends(require_console),
    ) -> APIResponse:
        owner_user_id = (
            input_data.ownerUserId
            if principal.is_admin and input_data.ownerUserId
            else principal.user_id
        )
        if not any(user.id == owner_user_id for user in repository.list_users()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner user not found")
        created = repository.create_key(
            name=input_data.name,
            env=input_data.env,
            scopes=input_data.scopes,
            owner_user_id=owner_user_id,
        )
        logger.info(
            "console_key_created key_id={} name={} env={} scopes={} owner_user_id={}",
            created.key.id,
            input_data.name,
            input_data.env,
            input_data.scopes,
            owner_user_id,
        )
        return APIResponse(data=created.model_dump())

    @router.post("/keys/{key_id}/revoke")
    async def revoke_key(key_id: str, principal: ConsolePrincipal = Depends(require_console)) -> APIResponse:
        require_key_visible(key_id, principal)
        if not repository.revoke_key(key_id, owner_user_id=principal.owner_filter):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
        logger.warning("console_key_revoked key_id={}", key_id)
        return APIResponse(data=True)

    @router.delete("/keys/{key_id}")
    async def delete_key(key_id: str, principal: ConsolePrincipal = Depends(require_console)) -> APIResponse:
        require_key_visible(key_id, principal)
        if not repository.delete_key(key_id, owner_user_id=principal.owner_filter):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
        logger.warning("console_key_deleted key_id={}", key_id)
        return APIResponse(data=True)

    @router.get("/capabilities")
    async def capabilities(_: ConsolePrincipal = Depends(require_console)) -> APIResponse:
        return APIResponse(data=[item.model_dump() for item in CAPABILITIES])

    @router.get("/logs")
    async def logs(limit: int = 200, principal: ConsolePrincipal = Depends(require_console)) -> APIResponse:
        return APIResponse(
            data=[
                item.model_dump()
                for item in repository.list_logs(
                    limit=max(1, min(limit, 500)), owner_user_id=principal.owner_filter
                )
            ]
        )

    @router.post("/debug")
    async def debug(
        input_data: DebugRequest,
        request: Request,
        principal: ConsolePrincipal = Depends(require_console),
    ) -> APIResponse:
        capability = CAPABILITY_BY_ID.get(input_data.capabilityId)
        if not capability:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found")
        key = require_key_visible(input_data.keyId, principal)
        if not key or key.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key is unavailable")
        auth.require_scope(key, capability.scope)

        logger.info(
            "console_debug_begin capability={} key_id={} env={} params={}",
            capability.id,
            key.id,
            input_data.env,
            input_data.params,
        )
        request_id = f"req_debug_{secrets.token_hex(4)}"
        probe_result = await run_debug_probe(
            capability=capability,
            debug_request=input_data,
            key=key,
            upstream_client=upstream_client,
            repository=repository,
            upstream_base=upstreams[0] if upstreams else "",
            request=request,
            request_id=request_id,
            settings=container.settings,
        )
        logger.info(
            "console_debug_done capability={} status={} latency_ms={}",
            capability.id,
            probe_result.get("statusCode"),
            probe_result.get("latencyMs"),
        )
        return APIResponse(data=probe_result)

    return router
