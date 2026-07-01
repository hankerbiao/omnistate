"""异步上下文管理。

基于 contextvars 实现全链路追踪和操作上下文的异步传播。
中间件在请求入口设置，业务代码通过 get 函数读取，无需显式传参。

用法:
    from app.shared.context import get_trace_context, set_operation_context

    ctx = get_trace_context()
    logger.info(f"处理请求: request_id={ctx.request_id}")
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field


# =============================================================================
# contextvars 定义
# =============================================================================
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")
_client_ip_ctx: ContextVar[str] = ContextVar("client_ip", default="-")
_user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")
_username_ctx: ContextVar[str] = ContextVar("username", default="-")
_role_ids_ctx: ContextVar[list[str]] = ContextVar("role_ids", default=[])


# =============================================================================
# 数据类
# =============================================================================
@dataclass(slots=True)
class TraceContext:
    """全链路追踪上下文。"""

    request_id: str = "-"
    trace_id: str = "-"
    client_ip: str = "-"

    def to_dict(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "client_ip": self.client_ip,
        }


@dataclass(slots=True)
class OperationContext:
    """操作者上下文（用户信息）。"""

    actor_id: str = "-"
    username: str = "-"
    role_ids: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)

    @property
    def user_id(self) -> str:
        return self.actor_id


# =============================================================================
# 追踪上下文 API
# =============================================================================
def generate_request_id() -> str:
    """生成全局唯一请求 ID。"""
    return f"req_{uuid.uuid4().hex[:20]}"


def generate_trace_id() -> str:
    """生成全局唯一追踪 ID（与 request_id 相同），
    后续可扩展为独立的 trace_id 生成逻辑。
    """
    return generate_request_id()


def set_trace_context(
    request_id: str | None = None,
    trace_id: str | None = None,
    client_ip: str | None = None,
) -> None:
    """设置追踪上下文（由中间件调用）。"""
    _request_id_ctx.set(request_id or generate_request_id())
    _trace_id_ctx.set(trace_id or _request_id_ctx.get())
    if client_ip:
        _client_ip_ctx.set(client_ip)


def get_trace_context() -> TraceContext:
    """获取当前请求的追踪上下文。"""
    return TraceContext(
        request_id=_request_id_ctx.get(),
        trace_id=_trace_id_ctx.get(),
        client_ip=_client_ip_ctx.get(),
    )


def set_operation_context(
    user_id: str,
    username: str = "",
    role_ids: list[str] | None = None,
) -> None:
    """设置操作者上下文（由认证中间件或依赖注入调用）。"""
    _user_id_ctx.set(user_id or "-")
    _username_ctx.set(username or "-")
    _role_ids_ctx.set(role_ids or [])


def get_operation_context() -> OperationContext:
    """获取当前操作者上下文。"""
    return OperationContext(
        actor_id=_user_id_ctx.get(),
        username=_username_ctx.get(),
        role_ids=_role_ids_ctx.get(),
    )


def reset_context() -> None:
    """重置所有上下文（请求结束后调用）。"""
    _request_id_ctx.set("-")
    _trace_id_ctx.set("-")
    _client_ip_ctx.set("-")
    _user_id_ctx.set("-")
    _username_ctx.set("-")
    _role_ids_ctx.set([])


# =============================================================================
# 上下文管理器（用于非请求场景，如后台任务）
# =============================================================================
from contextlib import asynccontextmanager


@asynccontextmanager
async def trace_scope(request_id: str | None = None):
    """为后台任务创建独立的追踪范围。

    用法:
        async with trace_scope() as ctx:
            logger.info("后台任务执行")
    """
    rid = request_id or generate_request_id()
    set_trace_context(request_id=rid)
    try:
        yield get_trace_context()
    finally:
        reset_context()
