"""HTTP 客户端模块。

提供统一的 HTTP 请求能力，支持重试、超时等配置。
"""

from app.shared.http.client import (
    HttpDispatchClient,
    close_http_client,
    get_http_client,
    get_http_dispatch_client,
)

__all__ = [
    "HttpDispatchClient",
    "close_http_client",
    "get_http_client",
    "get_http_dispatch_client",
]
