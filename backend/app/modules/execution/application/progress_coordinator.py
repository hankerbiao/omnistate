"""任务执行进度协调器。

负责当前 case 完成后决定：任务收口，还是自动推进下一条 case。
"""
from __future__ import annotations

from typing import Any

from app.modules.execution.application.constants import (
    FINAL_CASE_STATUSES,
    DispatchStatus,
    OverallStatus,
)
from app.modules.execution.application.task_dispatch_service import ExecutionDispatchService
from app.shared.core.logger import log as logger


class ExecutionProgressCoordinator:
    """串行编排的核心协调器。

    职责：
    1. 判断当前 case 是否已结束（event_type=progress + phase=case_finish）
    2. 判断是否需要推进下一条 case
    3. 如果是最后一条 → 收口任务状态
    4. 如果还有下一条 → 重建下发命令并自动推进
    5. 推进失败 → 标记任务为 FAILED
    """

    def __init__(self, dispatch_service: ExecutionDispatchService | None = None) -> None:
        self._dispatch_service = dispatch_service or ExecutionDispatchService()

    async def advance_after_case_finish(
        self,
        task_doc: Any,
        case_doc: Any,
        event: Any,
        event_time: Any,
        resolved_case_status: str | None,
    ) -> None:
        """当前 case 完成后自动推进或收口。

        触发条件（三项必须同时满足）：
        1. event_type == "progress" 且 phase == "case_finish"
        2. case 已进入终态（PASSED/FAILED/SKIPPED）
        3. event.case_id 必须等于 task.current_case_id（非乱序事件）

        三种分支：
        A. 不满足触发条件 → 直接返回，不做任何操作
        B. 已是最后一条 case → 收口任务
        C. 还有下一条 case → 重建下发命令并自动推送
        """
        # 条件一：必须是 progress + case_finish
        if event.event_type != "progress" or event.phase != "case_finish":
            return
        # 条件二：case 必须进入终态
        if case_doc is None or resolved_case_status not in FINAL_CASE_STATUSES:
            logger.debug(
                "Skipping task auto-advance because case is not final: "
                f"task_id={task_doc.task_id}, case_id={event.case_id}, "
                f"resolved_case_status={resolved_case_status}"
            )
            return
        # 条件三：事件的 case_id 必须等于任务当前游标指向的 case_id
        if event.case_id != getattr(task_doc, "current_case_id", None):
            logger.debug(
                "Skipping task auto-advance because event case is not current: "
                f"task_id={task_doc.task_id}, event_case_id={event.case_id}, "
                f"current_case_id={task_doc.current_case_id}"
            )
            return

        # 分支 B：最后一条 case，收口任务
        next_case_index = getattr(task_doc, "current_case_index", 0) + 1
        if next_case_index >= task_doc.case_count:
            task_doc.current_case_id = None
            task_doc.current_case_index = task_doc.case_count
            task_doc.finished_at = event_time
            task_doc.last_callback_at = event_time
            task_doc.overall_status = OverallStatus.FAILED if task_doc.failed_case_count > 0 else OverallStatus.PASSED
            if getattr(task_doc, "dispatch_status", None) not in {DispatchStatus.DISPATCH_FAILED, DispatchStatus.PENDING}:
                task_doc.dispatch_status = DispatchStatus.COMPLETED
            await task_doc.save()
            logger.info(
                "Execution task completed after final case: "
                f"task_id={task_doc.task_id}, final_case_id={event.case_id}, "
                f"overall_status={task_doc.overall_status}"
            )
            return

        # 分支 C：还有下一条 case，重建下发命令
        try:
            command = await self._dispatch_service.build_task_dispatch_command(
                task_doc, next_case_index
            )
        except Exception as exc:
            logger.error(
                "Failed to build dispatch command for auto-advance: "
                f"task_id={task_doc.task_id}, next_case_index={next_case_index}, error={exc}"
            )
            task_doc.dispatch_status = DispatchStatus.DISPATCH_FAILED
            task_doc.dispatch_error = f"Auto-advance build failed: {exc}"
            task_doc.overall_status = OverallStatus.FAILED
            task_doc.finished_at = event_time
            await task_doc.save()
            return

        # 下发下一条 case
        try:
            logger.info(
                "Auto-dispatching next execution case: "
                f"task_id={task_doc.task_id}, finished_case_id={event.case_id}, "
                f"next_case_id={command.dispatch_case_id}, next_case_index={next_case_index}"
            )
            await self._dispatch_service.dispatch_existing_task(task_doc, command)
        except Exception as exc:
            logger.error(
                "Failed to dispatch next case during auto-advance: "
                f"task_id={task_doc.task_id}, next_case_id={command.dispatch_case_id}, error={exc}"
            )
            task_doc.dispatch_status = DispatchStatus.DISPATCH_FAILED
            task_doc.dispatch_error = f"Auto-advance dispatch failed: {exc}"
            task_doc.overall_status = OverallStatus.FAILED
            task_doc.finished_at = event_time
            await task_doc.save()
