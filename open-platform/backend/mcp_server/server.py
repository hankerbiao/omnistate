"""DML Open Platform MCP service entrypoint."""

from typing import Any

from mcp.server.fastmcp import Context

from gateway_service.common.container import GatewayContainer
from gateway_service.common.logging_utils import configure_logging, logger

from .compat import CompatibleFastMCP
from .config import MCPSettings
from .tools import MCPToolService


settings = MCPSettings.from_env()
configure_logging(settings.gateway.log_level, log_file=settings.gateway.log_file)
container = GatewayContainer.build(settings.gateway)
tool_service = MCPToolService(container=container, default_api_key=settings.api_key)

mcp = CompatibleFastMCP(
    "DML V4 Open Platform",
    instructions=(
        "DML V4 开放平台 MCP 服务。默认提供只读工具，用开放平台 API Key 鉴权，"
        "并复用开放平台网关能力目录、权限和上游调用逻辑。"
    ),
    host=settings.host,
    port=settings.port,
    streamable_http_path=settings.path,
)


@mcp.tool(description="列出当前 API Key 已授权的开放能力及接口参数说明。")
def list_my_open_capabilities(ctx: Context) -> dict[str, Any]:
    return tool_service.list_my_open_capabilities(api_key=_api_key_from_context(ctx))


@mcp.tool(description="查询当前 API Key 所属账号最近创建的测试任务。")
async def list_my_test_tasks(limit: int = 20, ctx: Context = None) -> dict[str, Any]:  # type: ignore[assignment]
    return await tool_service.list_my_test_tasks(limit=limit, api_key=_api_key_from_context(ctx))


@mcp.tool(description="查询当前 API Key 已授权范围内的测试用例，支持按项目和状态过滤。")
async def list_test_cases(
    project_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    return await tool_service.list_test_cases(
        project_id=project_id,
        status=status,
        limit=limit,
        api_key=_api_key_from_context(ctx),
    )


@mcp.tool(description="查询单个测试任务的整体状态与执行进度。")
async def get_test_task_status(task_id: str, ctx: Context = None) -> dict[str, Any]:  # type: ignore[assignment]
    return await tool_service.get_test_task_status(task_id=task_id, api_key=_api_key_from_context(ctx))


@mcp.tool(description="查询测试任务的业务轨迹与执行事件时间线。")
async def get_test_task_timeline(
    task_id: str,
    limit: int = 100,
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    return await tool_service.get_test_task_timeline(
        task_id=task_id,
        limit=limit,
        api_key=_api_key_from_context(ctx),
    )


@mcp.tool(description="读取执行报告与失败分析摘要。")
async def get_execution_report(
    task_id: str,
    limit: int = 200,
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    return await tool_service.get_execution_report(
        task_id=task_id,
        limit=limit,
        api_key=_api_key_from_context(ctx),
    )


def _api_key_from_context(ctx: Context | None) -> str | None:
    """Best-effort extraction for streamable HTTP requests.

    FastMCP's stable public Context does not currently expose HTTP headers directly.
    Some transports still carry a lower-level request object in request_context, so
    this helper checks common attribute locations and falls back to DML_MCP_API_KEY.
    """
    if ctx is None:
        return None
    try:
        request_context = ctx.request_context
    except ValueError:
        return None

    for candidate_name in ("request", "http_request", "starlette_request"):
        candidate = getattr(request_context, candidate_name, None)
        token = _bearer_from_headers(getattr(candidate, "headers", None))
        if token:
            return token

    token = _bearer_from_headers(getattr(request_context, "headers", None))
    return token or None


def _bearer_from_headers(headers: Any) -> str:
    if not headers:
        return ""
    value = ""
    if hasattr(headers, "get"):
        value = headers.get("authorization", "") or headers.get("Authorization", "")
    if not value:
        return ""
    scheme, _, token = str(value).partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def main() -> None:
    logger.info(
        "mcp_server_start transport={} host={} port={} path={}",
        settings.transport,
        settings.host,
        settings.port,
        settings.path,
    )
    mcp.run(transport=settings.transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
