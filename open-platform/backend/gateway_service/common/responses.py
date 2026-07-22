"""网关统一 HTTP 响应构造。

把开放 API 网关的「错误响应信封」「错误码/诊断映射」「请求 ID 提取」收敛到
单一模块，避免路由处理函数内联重复构造，并让新增状态码的处理只改一处。
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from fastapi import Request, Response

from ..domain.models import APIResponse


_ERROR_CODES: dict[int, str] = {
    401: "AUTHENTICATION_FAILED",
    403: "PERMISSION_DENIED",
    404: "ROUTE_NOT_FOUND",
    429: "RATE_LIMIT_EXCEEDED",
    503: "UPSTREAM_SERVICE_UNAVAILABLE",
}

_DIAGNOSES: dict[int, str] = {
    401: "请检查 Authorization Bearer API Key 是否正确且未被撤销。",
    403: "当前密钥缺少访问该开放能力所需的 scope。",
    404: "请确认请求方法和开放 API 路径是否匹配能力目录。",
    429: "请求超过限额，请降低并发或稍后重试。",
    503: "上游服务当前不可用，请稍后重试。",
}


def request_id_from(request: Request) -> str:
    """返回请求携带的 x-request-id，缺失时生成一个新的。"""
    return request.headers.get("x-request-id") or f"req_{secrets.token_hex(8)}"


def error_code_for(status_code: int) -> str:
    """网关错误码：已知状态码返回语义码，未知返回 GATEWAY_ERROR。"""
    return _ERROR_CODES.get(status_code, "GATEWAY_ERROR")


def diagnosis_for(status_code: int) -> str:
    """面向调用方的诊断建议：未知状态码给出通用排障提示。"""
    return _DIAGNOSES.get(status_code, "请求被网关拒绝，请携带 Request ID 排查。")


def gateway_error_payload(
    *, status_code: int, message: str, error_code: str | None = None
) -> dict[str, Any]:
    """构造网关错误响应信封的载荷（dict），供日志与 HTTP 响应复用。"""
    code = error_code or error_code_for(status_code)
    return APIResponse(code=status_code, message=message, data={"error": code}).model_dump()


def build_gateway_error_response(
    *, request_id: str, status_code: int, payload: dict[str, Any]
) -> Response:
    """构造统一的网关错误响应。

    固定 JSON 信封、application/json 与 x-request-id 回传，便于调用方排障。
    """
    return Response(
        content=json.dumps(payload, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
        headers={"x-request-id": request_id},
    )
