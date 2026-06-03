"""Execution 模块业务上下文（contextvars）。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

_task_id_ctx: ContextVar[str] = ContextVar("execution_task_id", default="-")
_case_id_ctx: ContextVar[str] = ContextVar("execution_case_id", default="-")
_event_id_ctx: ContextVar[str] = ContextVar("execution_event_id", default="-")
_agent_id_ctx: ContextVar[str] = ContextVar("execution_agent_id", default="-")
_node_ctx: ContextVar[str] = ContextVar("execution_node", default="-")


@dataclass(slots=True)
class ExecutionContext:
    """执行任务业务上下文。"""

    task_id: str = "-"
    case_id: str = "-"
    event_id: str = "-"
    agent_id: str = "-"
    node: str = "-"

    def to_dict(self) -> dict[str, str]:
        return {
            "task_id": self.task_id,
            "case_id": self.case_id,
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "node": self.node,
        }


def set_execution_context(
    *,
    task_id: str | None = None,
    case_id: str | None = None,
    event_id: str | None = None,
    agent_id: str | None = None,
    node: str | None = None,
) -> None:
    """设置 execution 业务上下文（None 表示不修改该字段）。"""
    if task_id is not None:
        _task_id_ctx.set(task_id or "-")
    if case_id is not None:
        _case_id_ctx.set(case_id or "-")
    if event_id is not None:
        _event_id_ctx.set(event_id or "-")
    if agent_id is not None:
        _agent_id_ctx.set(agent_id or "-")
    if node is not None:
        _node_ctx.set(node or "-")


def get_execution_context() -> ExecutionContext:
    """获取当前 execution 业务上下文。"""
    return ExecutionContext(
        task_id=_task_id_ctx.get(),
        case_id=_case_id_ctx.get(),
        event_id=_event_id_ctx.get(),
        agent_id=_agent_id_ctx.get(),
        node=_node_ctx.get(),
    )


def reset_execution_context() -> None:
    """重置 execution 业务上下文。"""
    _task_id_ctx.set("-")
    _case_id_ctx.set("-")
    _event_id_ctx.set("-")
    _agent_id_ctx.set("-")
    _node_ctx.set("-")


@asynccontextmanager
async def execution_scope(
    *,
    task_id: str | None = None,
    case_id: str | None = None,
    event_id: str | None = None,
    agent_id: str | None = None,
    node: str | None = None,
):
    """为单条 execution 业务链路创建独立上下文范围。"""
    previous = get_execution_context()
    set_execution_context(
        task_id=task_id if task_id is not None else previous.task_id,
        case_id=case_id if case_id is not None else previous.case_id,
        event_id=event_id if event_id is not None else previous.event_id,
        agent_id=agent_id if agent_id is not None else previous.agent_id,
        node=node if node is not None else previous.node,
    )
    try:
        yield get_execution_context()
    finally:
        set_execution_context(
            task_id=previous.task_id,
            case_id=previous.case_id,
            event_id=previous.event_id,
            agent_id=previous.agent_id,
            node=previous.node,
        )


def bind_execution_context_from_payload(payload: dict[str, Any]) -> None:
    """从 Kafka / 事件 payload 提取 task_id、case_id、event_id 并写入上下文。"""
    task_id = payload.get("task_id") or payload.get("taskId")
    case_id = payload.get("case_id") or payload.get("caseId")
    event_id = payload.get("event_id") or payload.get("eventId")
    agent_id = payload.get("agent_id") or payload.get("agentId")
    set_execution_context(
        task_id=str(task_id) if task_id else None,
        case_id=str(case_id) if case_id else None,
        event_id=str(event_id) if event_id else None,
        agent_id=str(agent_id) if agent_id else None,
    )
