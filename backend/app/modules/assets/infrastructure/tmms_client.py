"""TMMS 外部系统 HTTP 客户端"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

import requests

from app.shared.config.settings import get_settings

logger = logging.getLogger(__name__)


class TMMSSyncError(Exception):
    """TMMS 同步异常"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class TMMSClient:
    """TMMS 测试机管理系统 HTTP 客户端"""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        settings = get_settings()
        self._base_url = (base_url or settings.tmms.api_base_url).rstrip("/")
        self._timeout = timeout or settings.tmms.api_timeout_sec
        self._token = settings.tmms.api_token

    @property
    def base_url(self) -> str:
        return self._base_url

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def fetch_machines(
        self,
        regions: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """从 TMMS 获取全量机器列表。

        Args:
            regions: 限定区域列表，为空则获取全部

        Returns:
            机器列表，每项至少包含: id, name, bmc_ip, os_ip
        """
        all_machines: List[Dict[str, Any]] = []
        page = 1
        page_size = 200

        while True:
            params: Dict[str, Any] = {"page": page, "page_size": page_size}
            if regions:
                params["regions"] = ",".join(regions)

            try:
                data = await self._request("GET", "/machines", params=params)
            except TMMSSyncError:
                raise
            except Exception as exc:
                raise TMMSSyncError(f"TMMS API 请求失败: {exc}") from exc

            items = data.get("items") or data.get("data") or []
            all_machines.extend(items)

            total = data.get("total", 0)
            if len(all_machines) >= total or len(items) < page_size:
                break
            page += 1

        logger.info("Fetched %d machines from TMMS", len(all_machines))
        return all_machines

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retries: int = 1,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求（同步执行，通过 asyncio.to_thread 包装）。"""
        url = f"{self._base_url}{path}"

        def _do_request() -> requests.Response:
            return requests.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                json=json_data,
                timeout=self._timeout,
            )

        last_exc: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                resp = await asyncio.to_thread(_do_request)
                if resp.status_code < 400:
                    return resp.json() if resp.text else {}
                last_exc = TMMSSyncError(
                    f"TMMS API 返回错误状态码 {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                )
            except requests.RequestException as exc:
                last_exc = TMMSSyncError(f"TMMS API 网络异常: {exc}")
            except Exception as exc:
                last_exc = exc

            if attempt < retries:
                logger.warning("TMMS request failed (attempt %d/%d), retrying...", attempt + 1, retries + 1)
                await asyncio.sleep(1.0)

        raise last_exc  # type: ignore[misc]
