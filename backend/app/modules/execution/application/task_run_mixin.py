"""执行任务 run 历史能力。"""

from __future__ import annotations

from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskRunCaseDoc,
    ExecutionTaskRunDoc,
)


class ExecutionTaskRunMixin:
    """处理 run 与 run_case 历史快照。"""

    @staticmethod
    async def _create_task_run_docs(
        task_doc,
        trigger_type: str,
        triggered_by: str,
    ) -> None:
        """为当前任务创建一轮新的执行历史。"""
        run_no = task_doc.latest_run_no + 1
        task_doc.latest_run_no = run_no
        task_doc.current_run_no = run_no

        case_docs = await (
            ExecutionTaskCaseDoc.find({"task_id": task_doc.task_id})
            .sort("order_no")
            .to_list()
        )
        await ExecutionTaskRunDoc(
            task_id=task_doc.task_id,
            run_no=run_no,
            trigger_type=trigger_type,
            triggered_by=triggered_by,
            overall_status=task_doc.overall_status,
            dispatch_status=task_doc.dispatch_status,
            dispatch_channel=task_doc.dispatch_channel,
            case_count=task_doc.case_count,
            stop_mode=task_doc.stop_mode,
            stop_requested_at=task_doc.stop_requested_at,
            stop_requested_by=task_doc.stop_requested_by,
            stop_reason=task_doc.stop_reason,
        ).insert()
        for case_doc in case_docs:
            await ExecutionTaskRunCaseDoc(
                task_id=task_doc.task_id,
                run_no=run_no,
                case_id=case_doc.case_id,
                order_no=case_doc.order_no,
                case_snapshot=dict(case_doc.case_snapshot or {}),
                dispatch_status=case_doc.dispatch_status,
                dispatch_attempts=case_doc.dispatch_attempts,
                status=case_doc.status,
                progress_percent=case_doc.progress_percent,
                started_at=case_doc.started_at,
                finished_at=case_doc.finished_at,
                dispatched_at=case_doc.dispatched_at,
                last_seq=case_doc.last_seq,
                last_event_id=case_doc.last_event_id,
                result_data=dict(case_doc.result_data or {}),
            ).insert()
