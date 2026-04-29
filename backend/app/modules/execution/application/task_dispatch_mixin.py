"""执行任务下发能力。"""

from __future__ import annotations

from typing import List

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_dispatch_coordinator import ExecutionTaskDispatchCoordinator
from app.modules.execution.repository.models import (
    ExecutionTaskDoc,
)


class ExecutionTaskDispatchMixin:
    """处理命令构造与任务下发。"""

    @classmethod
    def _build_case_dispatch_command(
        cls,
        task_doc: ExecutionTaskDoc,
        case_ids: List[str],
        auto_case_ids: List[str],
        script_entity_ids: List[str | None],
        case_configs: List[dict],
        case_payloads: List[dict],
        dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        """构建单 case 下发命令。"""
        return ExecutionTaskDispatchCoordinator.build_case_dispatch_command(
            task_doc,
            case_ids,
            auto_case_ids,
            script_entity_ids,
            case_configs,
            case_payloads,
            dispatch_case_index,
            cls._ensure_utc_datetime,
        )

    async def _build_task_dispatch_command(
        self,
        task_doc: ExecutionTaskDoc,
        dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        return await ExecutionTaskDispatchCoordinator(self._dispatcher).build_task_dispatch_command(
            task_doc,
            dispatch_case_index,
            self._resolve_task_case_pairs,
            self._ensure_utc_datetime,
        )

    async def _dispatch_task_if_needed(
        self,
        task_doc: ExecutionTaskDoc,
        should_dispatch_now: bool,
        dispatch_case_index: int = 0,
    ) -> None:
        """按需下发指定索引的 case。"""
        await ExecutionTaskDispatchCoordinator(self._dispatcher).dispatch_task_if_needed(
            task_doc,
            should_dispatch_now,
            dispatch_case_index,
            self._resolve_task_case_pairs,
            self._ensure_utc_datetime,
        )

    async def _dispatch_existing_task(
        self,
        task_doc: ExecutionTaskDoc,
        command: DispatchExecutionTaskCommand,
    ) -> None:
        """对已有任务执行真正下发。"""
        await ExecutionTaskDispatchCoordinator(self._dispatcher).dispatch_existing_task(task_doc, command)
