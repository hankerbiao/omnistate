"""DML V4 MCP Server 入口与只读工具。"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.mcp_server.client import DMLBackendClient
from app.mcp_server.config import MCPSettings

settings = MCPSettings.from_env()
mcp = FastMCP(
    "DML V4 Backend",
    instructions=(
        "用于查询 DML V4 自动化测试任务。默认只提供只读工具；"
        "所有数据访问均由 DML 后端 JWT 和权限系统控制。"
    ),
    json_response=True,
    host=settings.host,
    port=settings.port,
)


def get_backend_client() -> DMLBackendClient:
    """创建后端客户端；独立函数便于测试覆盖。"""
    return DMLBackendClient(settings)


@mcp.tool()
async def list_my_test_tasks(limit: int = 20) -> list[dict[str, Any]]:
    """查询当前 MCP 后端令牌所属用户最近创建的测试任务。

    Args:
        limit: 返回任务数量，范围 1 到 100。
    """
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    return await get_backend_client().list_my_test_tasks(limit=limit)


@mcp.tool()
async def get_test_task_status(task_id: str) -> dict[str, Any]:
    """查询一个测试任务的整体状态和执行进度。

    Args:
        task_id: 测试任务 ID，例如 ET-2026-000001。
    """
    normalized_task_id = task_id.strip()
    if not normalized_task_id:
        raise ValueError("task_id must not be empty")
    return await get_backend_client().get_test_task_status(normalized_task_id)


@mcp.tool()
async def get_test_task_timeline(task_id: str, limit: int = 100) -> dict[str, Any]:
    """查询一个测试任务的业务轨迹和执行事件时间线。

    Args:
        task_id: 测试任务 ID，例如 ET-2026-000001。
        limit: 最多返回的事件数量，范围 1 到 500。
    """
    normalized_task_id = task_id.strip()
    if not normalized_task_id:
        raise ValueError("task_id must not be empty")
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    return await get_backend_client().get_test_task_timeline(normalized_task_id, limit=limit)


def main() -> None:
    """启动 MCP 服务，默认 stdio，可通过环境变量切换 Streamable HTTP。"""
    mcp.run(transport=settings.transport)


if __name__ == "__main__":
    main()
