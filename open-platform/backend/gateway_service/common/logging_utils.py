"""日志服务（基于 loguru）。

对外暴露：
- ``logger``：统一日志实例（来自 loguru），全项目共用一个
- ``configure_logging``：幂等配置控制台 + 可选文件 sink（按大小轮转）
- ``request_context``：上下文管理器，把单次请求的关键字段注入后续所有日志
- ``request_log_fields``：从 FastAPI ``Request`` 抽取标准日志上下文字段
- 审计辅助：``now_ms`` / ``client_ip`` / ``classify_status`` / ``build_call_log``

设计要点
--------
日志格式固定携带 5 个结构化上下文字段，保证任意日志行都能关联到具体请求：

    request_id | method | path | key_id | client_ip

这些字段通过 ``request_context``（底层是 ``loguru.contextualize``）注入，
调用方无需在每条日志里手动拼装。``request_context`` 可嵌套，
鉴权成功后再次 ``contextualize(key_id=...)`` 即可让后续日志带上 key 维度。
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from typing import Any, Iterator

from fastapi import Request
from loguru import logger as _logger

from ..domain.models import ApiKey, CallLog, LogStatus
from ..domain.enums import utc_now_iso


# ---- 日志上下文默认字段（保证 format 中 extra[...] 始终存在）----
_DEFAULT_FIELDS: dict[str, str] = {
    "request_id": "-",
    "method": "-",
    "path": "-",
    "key_id": "-",
    "client_ip": "-",
}

# 控制台带颜色；文件版本去掉颜色标签（避免写入转义序列）
_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[request_id]}</cyan> | "
    "<cyan>{extra[method]}</cyan> | "
    "<cyan>{extra[path]}</cyan> | "
    "<cyan>{extra[key_id]}</cyan> | "
    "<cyan>{extra[client_ip]}</cyan> | "
    "<level>{message}</level>"
)

_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{extra[request_id]} | "
    "{extra[method]} | "
    "{extra[path]} | "
    "{extra[key_id]} | "
    "{extra[client_ip]} | "
    "{message}"
)


# 对外暴露统一 logger（模块级单例）
logger = _logger


def configure_logging(level: str = "INFO", *, log_file: str | None = None) -> None:
    """配置 loguru 日志输出。可重复调用，每次先清除旧 handler 再重建（幂等）。

    通过 ``logger.configure(extra=...)`` 为所有日志设置上下文默认值，
    使非请求场景（启动/关闭）也能正常渲染 ``{extra[...]}``；请求场景用
    ``request_context`` 覆盖这些默认值。

    :param level: 日志级别（DEBUG/INFO/WARNING/ERROR）
    :param log_file: 可选日志文件路径，启用文件 sink（10MB 轮转，保留 5 份）
    """
    _logger.remove()
    _logger.configure(extra=dict(_DEFAULT_FIELDS))
    lvl = level.upper()

    _logger.add(
        sys.stderr,
        level=lvl,
        format=_CONSOLE_FORMAT,
        colorize=True,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    if log_file:
        _logger.add(
            log_file,
            level=lvl,
            format=_FILE_FORMAT,
            rotation="10 MB",
            retention=5,
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

    _logger.debug("logging_configured level={} file={}", lvl, log_file or "none")


@contextmanager
def request_context(**fields: str) -> Iterator[None]:
    """进入请求上下文，后续所有日志自动携带给定字段。

    用法::

        with request_context(request_id="r1", method="GET", path="/x"):
            logger.info("handling request")  # 自动带上 request_id/method/path
    """
    with _logger.contextualize(**fields):
        yield


def request_log_fields(request: Request, request_id: str) -> dict[str, str]:
    """从 FastAPI ``Request`` 抽取标准日志上下文字段。"""
    return {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": client_ip(request),
        "key_id": "-",
    }


# ---------------------------------------------------------------------------
# 审计日志辅助（写入 SQLite 调用日志，非进程日志）
# ---------------------------------------------------------------------------


def now_ms() -> float:
    return time.perf_counter() * 1000


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def classify_status(status_code: int) -> LogStatus:
    if status_code < 400:
        return LogStatus.success
    if status_code < 500:
        return LogStatus.client_error
    return LogStatus.server_error


def build_call_log(
    *,
    request_id: str,
    request: Request,
    key: ApiKey | None,
    status_code: int,
    started_ms: float,
    gateway_latency_ms: int,
    request_body: bytes | None,
    response_body: bytes | str | dict[str, Any],
    error_code: str | None = None,
    diagnosis: str | None = None,
) -> CallLog:
    total_latency = max(1, round(now_ms() - started_ms))
    return CallLog(
        id=f"log_{request_id}",
        timestamp=utc_now_iso(),
        requestId=request_id,
        appName=key.name if key else "未认证应用",
        keyName=key.name if key else "unknown",
        method=request.method,  # type: ignore[arg-type]
        endpoint=request.url.path,
        statusCode=status_code,
        status=classify_status(status_code),
        latencyMs=total_latency,
        gatewayLatencyMs=gateway_latency_ms,
        ip=client_ip(request),
        requestBody=_safe_body(request_body),
        responseBody=_safe_response(response_body),
        errorCode=error_code,
        diagnosis=diagnosis,
    )


def _safe_body(body: bytes | None) -> str | None:
    if not body:
        return None
    text = body.decode("utf-8", errors="replace")
    return text[:4000]


def _safe_response(body: bytes | str | dict[str, Any]) -> str:
    if isinstance(body, dict):
        return json.dumps(body, ensure_ascii=False, indent=2)[:4000]
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")[:4000]
    return body[:4000]
