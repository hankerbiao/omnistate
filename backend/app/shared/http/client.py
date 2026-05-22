"""HTTP 客户端封装模块。

提供统一的 HTTP 请求能力，支持重试、超时等配置。
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.shared.config import get_settings
from app.shared.core.logger import log as logger

# 全局 HTTP 客户端实例
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """获取全局 HTTP 客户端实例（单例模式）。"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


async def close_http_client() -> None:
    """关闭全局 HTTP 客户端。"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


class HttpDispatchClient:
    """HTTP 下发客户端。"""

    def __init__(self) -> None:
        self._client = get_http_client()

    async def post_json(
        self,
        url: str,
        data: dict[str, Any],
        timeout_sec: int | None = None,
        headers: dict[str, str] | None = None,
        retry_times: int | None = None,
    ) -> tuple[bool, dict[str, Any], str | None]:
        """发送 POST JSON 请求。

        Args:
            url: 目标 URL
            data: 请求体数据
            timeout_sec: 超时秒数（默认从配置读取）
            headers: 请求头（默认从配置读取）
            retry_times: 重试次数（默认从配置读取）

        Returns:
            (success, response_data, error_message)
        """
        settings = get_settings()
        http_cfg = settings.execution.http_dispatch

        if timeout_sec is None:
            timeout_sec = http_cfg.timeout_sec
        if headers is None:
            headers = dict(http_cfg.headers)
        if retry_times is None:
            retry_times = http_cfg.retry_times

        # 添加默认 Content-Type
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        last_error: str | None = None

        # 调试日志：打印完整请求信息
        logger.debug(
            f"[HTTP DISPATCH] Preparing POST request:\n"
            f"  URL: {url}\n"
            f"  Headers: {headers}\n"
            f"  Body: {data}"
        )

        for attempt in range(retry_times):
            try:
                logger.info(
                    f"[HTTP DISPATCH] Sending POST attempt {attempt + 1}/{retry_times}: "
                    f"url={url}, timeout={timeout_sec}s"
                )

                response = await self._client.post(
                    url=url,
                    json=data,
                    headers=headers,
                    timeout=timeout_sec,
                )

                if response.status_code >= 200 and response.status_code < 300:
                    try:
                        response_data = response.json()
                    except Exception:
                        response_data = {"raw": response.text}

                    logger.info(
                        f"[HTTP DISPATCH] Success: url={url}, status={response.status_code}\n"
                        f"  Response: {response_data}"
                    )
                    return True, response_data, None

                # 非 2xx 状态码
                response_preview = response.text[:1000]
                last_error = f"HTTP {response.status_code}: {response_preview}"
                logger.warning(
                    f"[HTTP DISPATCH] Failed (attempt {attempt + 1}): "
                    f"url={url}, status={response.status_code}\n"
                    f"  Response: {response_preview}"
                )

            except httpx.TimeoutException as e:
                last_error = f"Timeout after {timeout_sec}s: {e}"
                logger.warning(
                    f"[HTTP DISPATCH] Timeout (attempt {attempt + 1}/{retry_times}): "
                    f"url={url}, error={last_error}"
                )

            except httpx.ConnectError as e:
                last_error = f"Connection error: {e}"
                logger.warning(
                    f"[HTTP DISPATCH] Connection error (attempt {attempt + 1}/{retry_times}): "
                    f"url={url}, error={last_error}"
                )

            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.error(
                    f"[HTTP DISPATCH] Unexpected error (attempt {attempt + 1}/{retry_times}): "
                    f"url={url}, error={last_error}"
                )

            # 非致命错误，等待后重试
            if attempt < retry_times - 1:
                await asyncio.sleep(1 * (attempt + 1))  # 递增等待时间

        # 所有重试都失败
        logger.error(
            f"[HTTP DISPATCH] Failed after {retry_times} attempts: "
            f"url={url}, last_error={last_error}"
        )
        return False, {}, last_error


# 全局客户端实例
_http_dispatch_client: HttpDispatchClient | None = None


def get_http_dispatch_client() -> HttpDispatchClient:
    """获取 HTTP 下发客户端实例（单例模式）。"""
    global _http_dispatch_client
    if _http_dispatch_client is None:
        _http_dispatch_client = HttpDispatchClient()
    return _http_dispatch_client
