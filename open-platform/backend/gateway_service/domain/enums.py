"""网关服务枚举与字面量类型。"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal


class ApiKeyStatus(str, Enum):
    active = "active"
    revoked = "revoked"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class LogStatus(str, Enum):
    success = "success"
    client_error = "client_error"
    server_error = "server_error"


EnvName = Literal["live", "test"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
