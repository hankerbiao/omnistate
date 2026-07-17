"""DML 后端 HTTP 客户端。"""

from __future__ import annotations

from typing import Any

import httpx

from app.mcp_server.config import MCPSettings


class BackendAPIError(RuntimeError):
    """后端 API 调用失败，返回适合 MCP 客户端展示的安全错误。"""


class DMLBackendClient:
    """调用现有 DML API，并沿用后端 JWT 与权限校验。"""

    def __init__(self, settings: MCPSettings) -> None:
        self._settings = settings

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._settings.backend_token:
            headers["Authorization"] = f"Bearer {self._settings.backend_token}"
        return headers

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        """发送 GET 请求并解包项目统一 APIResponse。"""
        url = f"{self._settings.backend_base_url}{path}"
        try:
            async with httpx.AsyncClient(
                headers=self._headers(),
                timeout=self._settings.request_timeout_seconds,
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 401:
                detail = "后端拒绝访问，请配置有效的 DML_MCP_BACKEND_TOKEN"
            elif status_code == 403:
                detail = "当前令牌没有访问该工具所需的后端权限"
            elif status_code == 404:
                detail = "请求的数据不存在"
            else:
                detail = f"后端请求失败，HTTP 状态码 {status_code}"
            raise BackendAPIError(detail) from exc
        except httpx.RequestError as exc:
            raise BackendAPIError("无法连接 DML 后端，请检查 DML_MCP_BACKEND_URL 和后端状态") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendAPIError("后端返回了非 JSON 响应") from exc

        if not isinstance(payload, dict):
            raise BackendAPIError("后端响应格式无效")
        if payload.get("code", 0) != 0:
            raise BackendAPIError("后端返回业务错误，请查看后端审计日志获取详情")
        return payload.get("data")

    async def health(self) -> dict[str, Any]:
        """检查后端基础健康接口。"""
        return await self.get("/health")

    async def list_my_test_tasks(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """查询令牌所属用户的测试任务。"""
        data = await self.get("/api/v1/execution/tasks/my", params={"limit": limit})
        if not isinstance(data, list):
            raise BackendAPIError("测试任务列表响应格式无效")
        return data

    async def get_test_task_status(self, task_id: str) -> dict[str, Any]:
        """查询指定测试任务状态。"""
        data = await self.get(f"/api/v1/execution/tasks/{task_id}/status")
        if not isinstance(data, dict):
            raise BackendAPIError("测试任务状态响应格式无效")
        return data

    async def get_test_task_timeline(self, task_id: str, *, limit: int = 100) -> dict[str, Any]:
        """查询指定测试任务时间线。"""
        data = await self.get(
            f"/api/v1/execution/tasks/{task_id}/timeline",
            params={"limit": limit},
        )
        if not isinstance(data, dict):
            raise BackendAPIError("测试任务时间线响应格式无效")
        return data
