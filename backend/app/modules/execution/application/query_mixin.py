"""执行任务查询相关服务能力。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.modules.execution.repository.models import (
    ExecutionTaskDoc,
    ExecutionTaskRunCaseDoc,
    ExecutionTaskRunDoc,
)


class ExecutionTaskQueryMixin:
    """任务查询与统一序列化能力。"""

    @staticmethod
    def _serialize_task_doc(task_doc: ExecutionTaskDoc) -> Dict[str, Any]:
        """统一序列化任务摘要字段，避免重复手写响应。"""
        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "framework": task_doc.framework,
            "agent_id": task_doc.agent_id,
            "dispatch_channel": task_doc.dispatch_channel,
            "dedup_key": task_doc.dedup_key,
            "schedule_type": task_doc.schedule_type,
            "schedule_status": task_doc.schedule_status,
            "dispatch_status": task_doc.dispatch_status,
            "consume_status": task_doc.consume_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
            "latest_run_no": getattr(task_doc, "latest_run_no", 0),
            "current_run_no": getattr(task_doc, "current_run_no", 0),
            "current_case_id": getattr(task_doc, "current_case_id", None),
            "current_case_index": getattr(task_doc, "current_case_index", 0),
            "planned_at": task_doc.planned_at,
            "triggered_at": task_doc.triggered_at,
            "created_at": task_doc.created_at,
            "updated_at": task_doc.updated_at,
        }

    async def list_tasks(
        self,
        schedule_type: str | None = None,
        schedule_status: str | None = None,
        dispatch_status: str | None = None,
        consume_status: str | None = None,
        overall_status: str | None = None,
        created_by: str | None = None,
        agent_id: str | None = None,
        framework: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出执行任务，支持按状态和时间窗口过滤。"""
        query: Dict[str, Any] = {"is_deleted": False}
        if schedule_type:
            query["schedule_type"] = schedule_type.upper()
        if schedule_status:
            query["schedule_status"] = schedule_status.upper()
        if dispatch_status:
            query["dispatch_status"] = dispatch_status.upper()
        if consume_status:
            query["consume_status"] = consume_status.upper()
        if overall_status:
            query["overall_status"] = overall_status.upper()
        if created_by:
            query["created_by"] = created_by
        if agent_id:
            query["agent_id"] = agent_id
        if framework:
            query["framework"] = framework
        if date_from or date_to:
            created_at_query: Dict[str, datetime] = {}
            if date_from:
                created_at_query["$gte"] = self._ensure_utc_datetime(date_from)
            if date_to:
                created_at_query["$lte"] = self._ensure_utc_datetime(date_to)
            query["created_at"] = created_at_query

        docs = await (
            ExecutionTaskDoc.find(query)
            .sort("-created_at")
            .skip(max(offset, 0))
            .limit(max(limit, 1))
            .to_list()
        )
        return [self._serialize_task_doc(task_doc) for task_doc in docs]

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态详情。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        result = self._serialize_task_doc(task_doc)
        result["consumed_at"] = task_doc.consumed_at
        result["dispatch_response"] = task_doc.dispatch_response
        result["dispatch_error"] = task_doc.dispatch_error
        return result

    @staticmethod
    def _serialize_run_doc(run_doc: ExecutionTaskRunDoc) -> Dict[str, Any]:
        return {
            "task_id": run_doc.task_id,
            "run_no": run_doc.run_no,
            "trigger_type": run_doc.trigger_type,
            "triggered_by": run_doc.triggered_by,
            "overall_status": run_doc.overall_status,
            "dispatch_status": run_doc.dispatch_status,
            "case_count": run_doc.case_count,
            "reported_case_count": run_doc.reported_case_count,
            "started_at": run_doc.started_at,
            "finished_at": run_doc.finished_at,
            "created_at": run_doc.created_at,
            "updated_at": run_doc.updated_at,
        }

    async def list_task_runs(self, task_id: str) -> List[Dict[str, Any]]:
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        run_docs = await (
            ExecutionTaskRunDoc.find({"task_id": task_id})
            .sort("-run_no")
            .to_list()
        )
        return [self._serialize_run_doc(run_doc) for run_doc in run_docs]

    async def get_task_run_detail(self, task_id: str, run_no: int) -> Dict[str, Any]:
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        run_doc = await ExecutionTaskRunDoc.find_one({"task_id": task_id, "run_no": run_no})
        if not run_doc:
            raise KeyError(f"Task run not found: {task_id}/{run_no}")

        case_docs = await (
            ExecutionTaskRunCaseDoc.find({"task_id": task_id, "run_no": run_no})
            .sort("order_no")
            .to_list()
        )
        result = self._serialize_run_doc(run_doc)
        result["dispatch_channel"] = run_doc.dispatch_channel
        result["dispatch_response"] = run_doc.dispatch_response
        result["dispatch_error"] = run_doc.dispatch_error
        result["last_callback_at"] = run_doc.last_callback_at
        result["cases"] = [
            {
                "case_id": case_doc.case_id,
                "order_no": case_doc.order_no,
                "status": case_doc.status,
                "dispatch_status": case_doc.dispatch_status,
                "dispatch_attempts": case_doc.dispatch_attempts,
                "progress_percent": case_doc.progress_percent,
                "step_total": case_doc.step_total,
                "step_passed": case_doc.step_passed,
                "step_failed": case_doc.step_failed,
                "step_skipped": case_doc.step_skipped,
                "started_at": case_doc.started_at,
                "finished_at": case_doc.finished_at,
                "result_data": case_doc.result_data,
            }
            for case_doc in case_docs
        ]
        return result
