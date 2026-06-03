"""Execution 模块结构化日志辅助。"""

from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Any

from app.modules.execution.shared.execution_context import (
    execution_scope,
    get_execution_context,
    set_execution_context,
)
from app.shared.context import get_operation_context, get_trace_context
from app.shared.core.logger import log as _logger

# 大对象字段在 JSON 日志中截断
_LARGE_FIELD_NAMES = frozenset({
    "payload", "case_payloads", "case_configs", "request_payload",
    "dispatch_response", "parameters", "data", "detail",
})
_MAX_FIELD_CHARS = 2048


class ExecutionNode(str, Enum):
    """Execution 业务节点枚举。"""

    TASK_CREATE = "task.create"
    TASK_DISPATCH = "task.dispatch"
    EVENT_INGEST = "event.ingest"
    CASE_UPDATE = "case.update"
    TASK_ADVANCE = "task.advance"
    TASK_COMPLETE = "task.complete"
    TASK_CANCEL = "task.cancel"
    TASK_DELETE = "task.delete"
    TASK_RERUN = "task.rerun"
    SCHEDULER_TICK = "scheduler.tick"
    KAFKA_BATCH = "kafka.batch"
    KAFKA_RESULT = "kafka.result"
    HTTP_DISPATCH_BG = "http.dispatch.bg"


def _truncate_value(value: Any) -> Any:
    """截断过大的日志字段，避免日志膨胀。"""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        serialized = json.dumps(value, default=str, ensure_ascii=False)
        if len(serialized) <= _MAX_FIELD_CHARS:
            return value
        return {"_truncated": True, "keys": list(value.keys()), "preview": serialized[:_MAX_FIELD_CHARS]}
    if isinstance(value, (list, tuple)):
        serialized = json.dumps(value, default=str, ensure_ascii=False)
        if len(serialized) <= _MAX_FIELD_CHARS:
            return value
        return {"_truncated": True, "length": len(value), "preview": serialized[:_MAX_FIELD_CHARS]}
    text = str(value)
    if len(text) <= _MAX_FIELD_CHARS:
        return text
    return f"{text[:_MAX_FIELD_CHARS]}...(truncated)"


def _prepare_log_fields(**ctx: Any) -> dict[str, Any]:
    """合并追踪、操作者与 execution 上下文。"""
    trace = get_trace_context()
    operation = get_operation_context()
    execution = get_execution_context()

    fields: dict[str, Any] = {
        "domain": "execution",
        "request_id": trace.request_id,
        "trace_id": trace.trace_id,
        "client_ip": trace.client_ip,
        "user_id": operation.actor_id,
        "task_id": execution.task_id,
        "case_id": execution.case_id,
        "event_id": execution.event_id,
        "agent_id": execution.agent_id,
        "node": execution.node,
    }

    for key, value in ctx.items():
        if key in _LARGE_FIELD_NAMES or key.endswith("_payload") or key.endswith("_data"):
            fields[key] = _truncate_value(value)
        else:
            fields[key] = value

    return fields


def _schedule_biz_log(
    node: str,
    message: str,
    level: str,
    fields: dict[str, Any],
) -> None:
    """异步写入业务轨迹（失败不影响主流程）。"""
    task_id = fields.get("task_id")
    if not task_id or task_id == "-":
        return
    if level.upper() == "DEBUG":
        return

    async def _insert() -> None:
        try:
            from app.modules.execution.repository.models.execution_biz_log import ExecutionBizLogDoc

            await ExecutionBizLogDoc(
                task_id=str(task_id),
                case_id=str(fields.get("case_id") or "-") if fields.get("case_id") != "-" else None,
                event_id=str(fields.get("event_id") or "-") if fields.get("event_id") != "-" else None,
                node=node,
                action=message,
                outcome=fields.get("outcome"),
                status_before=fields.get("before") if isinstance(fields.get("before"), dict) else None,
                status_after=fields.get("after") if isinstance(fields.get("after"), dict) else None,
                operator_id=str(fields.get("user_id") or "-") if fields.get("user_id") != "-" else None,
                request_id=str(fields.get("request_id") or "-") if fields.get("request_id") != "-" else None,
                detail={
                    k: v for k, v in fields.items()
                    if k not in {
                        "domain", "request_id", "trace_id", "client_ip", "user_id",
                        "task_id", "case_id", "event_id", "agent_id", "node",
                        "before", "after", "outcome",
                    }
                },
                level=level.upper(),
            ).insert()
        except Exception as exc:
            _logger.debug(
                "Failed to persist execution biz log: task_id={}, node={}, error={}",
                task_id,
                node,
                exc,
            )

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_insert())
    except RuntimeError:
        pass


def elog(
    level: str,
    node: ExecutionNode | str,
    message: str,
    *,
    outcome: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    duration_ms: float | None = None,
    **ctx: Any,
) -> None:
    """写入 execution 结构化日志。"""
    node_str = node.value if isinstance(node, ExecutionNode) else str(node)
    set_execution_context(node=node_str)

    log_fields = _prepare_log_fields(
        node=node_str,
        outcome=outcome,
        before=before,
        after=after,
        duration_ms=duration_ms,
        **ctx,
    )

    bound = _logger.bind(**{k: v for k, v in log_fields.items() if v is not None and v != "-"})
    log_fn = getattr(bound, level.lower(), bound.info)
    log_fn(message)

    _schedule_biz_log(node_str, message, level, log_fields)


__all__ = [
    "ExecutionNode",
    "elog",
    "execution_scope",
    "get_execution_context",
    "set_execution_context",
]
