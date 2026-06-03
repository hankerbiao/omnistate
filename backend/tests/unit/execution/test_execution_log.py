"""Execution 结构化日志与上下文单元测试。"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.modules.execution.shared.execution_context import (
    execution_scope,
    get_execution_context,
    reset_execution_context,
    set_execution_context,
)
from app.modules.execution.shared.execution_log import ExecutionNode, elog
from app.shared.context import reset_context, set_trace_context


@pytest.fixture(autouse=True)
def _clean_context():
    reset_context()
    reset_execution_context()
    yield
    reset_context()
    reset_execution_context()


def test_execution_scope_restores_previous_context():
    async def _run() -> None:
        set_execution_context(task_id="ET-1", node="task.create")
        async with execution_scope(task_id="ET-2", case_id="case-1", node="task.dispatch"):
            ctx = get_execution_context()
            assert ctx.task_id == "ET-2"
            assert ctx.case_id == "case-1"
            assert ctx.node == "task.dispatch"
        ctx = get_execution_context()
        assert ctx.task_id == "ET-1"
        assert ctx.case_id == "-"
        assert ctx.node == "task.create"

    asyncio.run(_run())


def test_elog_includes_execution_fields_in_json(tmp_path, monkeypatch):
    captured: list[str] = []

    def _capture_json(record: dict) -> str:
        from app.shared.core.logger import _get_trace_extra, _merge_execution_extra, _mask_sensitive_data

        trace_extra = _get_trace_extra()
        exec_extra = _merge_execution_extra()
        for key, value in {**trace_extra, **exec_extra}.items():
            record["extra"].setdefault(key, value)

        log_entry = {
            "level": record["level"].name,
            "message": _mask_sensitive_data(str(record.get("message", ""))),
            "request_id": record["extra"].get("request_id", "-"),
            "task_id": record["extra"].get("task_id", "-"),
            "node": record["extra"].get("node", "-"),
            "domain": record["extra"].get("domain", "-"),
            "outcome": record["extra"].get("outcome", "-"),
        }
        for key, value in record["extra"].items():
            if key not in log_entry and key not in {
                "user_id", "trace_id", "client_ip", "case_id", "event_id", "agent_id",
            }:
                log_entry[key] = value
        line = json.dumps(log_entry, default=str, ensure_ascii=False) + "\n"
        captured.append(line)
        return line

    from loguru import logger

    logger.remove()
    logger.add(lambda msg: None, format=_capture_json, level="DEBUG")

    set_trace_context(request_id="req_test_001")
    set_execution_context(task_id="ET-2026-000001", case_id="case-abc", node="-")

    elog(
        "info",
        ExecutionNode.TASK_DISPATCH,
        "dispatch finished",
        outcome="success",
        channel="RABBITMQ",
        before={"dispatch_status": "PENDING"},
        after={"dispatch_status": "DISPATCHED"},
    )

    assert captured
    payload = json.loads(captured[-1])
    assert payload["domain"] == "execution"
    assert payload["task_id"] == "ET-2026-000001"
    assert payload["node"] == ExecutionNode.TASK_DISPATCH.value
    assert payload["outcome"] == "success"
    assert payload["request_id"] == "req_test_001"
    assert payload["channel"] == "RABBITMQ"


def test_schedule_biz_log_skips_debug_level():
    """DEBUG 级别不应异步写入业务轨迹。"""
    from app.modules.execution.shared.execution_log import _schedule_biz_log

    async def _run() -> None:
        created: list[asyncio.Task] = []
        loop = asyncio.get_running_loop()
        original_create_task = loop.create_task

        def spy_create_task(coro):
            task = original_create_task(coro)
            created.append(task)
            return task

        loop.create_task = spy_create_task  # type: ignore[method-assign]

        _schedule_biz_log("task.create", "debug msg", "DEBUG", {"task_id": "ET-1"})
        _schedule_biz_log("task.create", "info msg", "INFO", {"task_id": "ET-1"})
        await asyncio.sleep(0.05)
        assert len(created) == 1

    asyncio.run(_run())


def test_schedule_biz_log_skips_missing_task_id():
    from app.modules.execution.shared.execution_log import _schedule_biz_log

    async def _run() -> None:
        created: list[asyncio.Task] = []
        loop = asyncio.get_running_loop()
        original_create_task = loop.create_task

        def spy_create_task(coro):
            task = original_create_task(coro)
            created.append(task)
            return task

        loop.create_task = spy_create_task  # type: ignore[method-assign]

        _schedule_biz_log("task.create", "info msg", "INFO", {"task_id": "-"})
        await asyncio.sleep(0.01)
        assert created == []

    asyncio.run(_run())

def test_elog_biz_log_insert_failure_logs_debug(monkeypatch):
    debug_messages: list[str] = []

    class FailingBizLogDoc:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def insert(self):
            raise RuntimeError("db unavailable")

    def fake_debug(message, *args):
        debug_messages.append(message.format(*args) if args else message)

    monkeypatch.setattr(
        "app.modules.execution.repository.models.execution_biz_log.ExecutionBizLogDoc",
        FailingBizLogDoc,
    )
    monkeypatch.setattr("app.modules.execution.shared.execution_log._logger.debug", fake_debug)

    async def _run() -> None:
        set_execution_context(task_id="ET-2026-000003")
        elog("info", ExecutionNode.TASK_CREATE, "task created", outcome="success")
        await asyncio.sleep(0.05)

    asyncio.run(_run())

    assert any("Failed to persist execution biz log" in msg for msg in debug_messages)
