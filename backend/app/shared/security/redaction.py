"""请求与日志敏感信息脱敏工具。

集中维护敏感字段清单，供请求日志、审计日志、Debug HTTP 日志复用，
避免密码、密钥、Token 等明文出现在日志或审计记录中。

设计原则：
- 不在日志/审计中输出明文密码、密钥、Token。
- 无法解析的请求体不回显原文，直接返回占位符，避免绕过脱敏。
- 高风险路径（登录、令牌、凭证轮换）不记录请求体。
"""
from __future__ import annotations

import json
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode

# 需要脱敏的字段名（统一小写匹配）
SENSITIVE_FIELD_NAMES = {
    "password", "passwd", "pwd",
    "old_password", "new_password", "current_password", "password_confirm",
    "secret", "client_secret", "secret_key", "secret_access_key", "webhook_secret",
    "api_key", "apikey",
    "token", "access_token", "refresh_token",
    "authorization", "auth", "jwt",
    "cookie", "credential", "private_key", "privatekey",
    "x_api_key", "x_auth_token", "proxy_authorization",
    # 系统配置值：例如 ai.api_key、数据库口令、Webhook 地址等
    "config_value",
}

# 整体脱敏的请求头
SENSITIVE_HEADERS = {
    "authorization", "cookie", "x-api-key", "x-auth-token",
    "proxy-authorization", "x-amz-security-token",
}

REDACTED = "***REDACTED***"

# 不记录请求体的高风险路径后缀（登录、令牌、凭证轮换等）
SENSITIVE_BODY_PATH_SUFFIXES = (
    "/login",
    "/token",
    "/oauth/token",
    "/auth/token",
    "/credentials",
    "/credentials/rotate",
    "/rotate",
    "/password",
)

# 不记录请求体（仅匹配路径包含，用于含密钥/口令的业务路径）
SENSITIVE_BODY_PATH_CONTAINS = (
    "/system-configs",
)


def is_sensitive_field(name: str) -> bool:
    """判断字段名是否属于敏感字段。"""
    return name.strip().lower() in SENSITIVE_FIELD_NAMES


def redact_dict(data: Any, max_depth: int = 5) -> Any:
    """递归脱敏字典/列表中的敏感字段。"""
    if max_depth < 0:
        return REDACTED
    if isinstance(data, dict):
        return {
            key: (REDACTED if is_sensitive_field(key) else redact_dict(value, max_depth - 1))
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redact_dict(item, max_depth - 1) for item in data]
    return data


def redact_json_string(text: str, max_len: int | None = None) -> str:
    """脱敏 JSON 字符串。

    解析失败时返回占位符而非原文，避免绕过脱敏泄露敏感内容。
    """
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return "<unparseable-body-redacted>"
    redacted = redact_dict(parsed)
    try:
        out = json.dumps(redacted, ensure_ascii=False)
    except (TypeError, ValueError):
        return "<unserializable-body-redacted>"
    if max_len and len(out) > max_len:
        out = out[:max_len] + "...(truncated)"
    return out


def redact_query_params(params: Mapping[str, str]) -> dict[str, str]:
    """脱敏查询参数映射，供审计日志等结构化落点使用。"""
    return {
        key: (REDACTED if is_sensitive_field(key) else value)
        for key, value in params.items()
    }


def redact_query_string(query: str) -> str:
    """脱敏 URL 查询串，支持 URL 编码键和重复参数。"""
    if not query:
        return query
    pairs = parse_qsl(query, keep_blank_values=True)
    redacted = [
        (key, REDACTED if is_sensitive_field(key) else value)
        for key, value in pairs
    ]
    return urlencode(redacted, doseq=True, safe="*")


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """脱敏敏感请求头。"""
    return {
        key: (REDACTED if key.lower() in SENSITIVE_HEADERS else value)
        for key, value in headers.items()
    }


def should_skip_body_logging(path: str) -> bool:
    """高风险路径不记录请求体。"""
    lowered = (path or "").lower().rstrip("/")
    if any(lowered.endswith(suffix) for suffix in SENSITIVE_BODY_PATH_SUFFIXES):
        return True
    return any(token in lowered for token in SENSITIVE_BODY_PATH_CONTAINS)


async def safe_body_preview(request: Any, max_chars: int = 500) -> str:
    """生成安全的请求体预览。

    只对 JSON 做结构化脱敏；无法可靠解析的 text/form/xml 和二进制内容均不回显，
    避免调试日志因请求格式变化泄露密码、Token 或密钥。
    """
    if request.method.upper() in {"GET", "HEAD", "OPTIONS", "DELETE"}:
        return "-"
    if should_skip_body_logging(request.url.path):
        return "<body redacted>"

    content_type = (request.headers.get("content-type") or "").lower()
    if "json" not in content_type:
        return f"<{content_type or 'unknown'} body omitted>"

    raw_body = await request.body()
    if not raw_body:
        return "-"
    text = raw_body.decode("utf-8", errors="replace").strip()
    return redact_json_string(text, max_chars)
