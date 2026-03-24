"""执行任务查询相关能力。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)


class ExecutionTaskQueryMixin:
    """提供任务查询与统一序列化能力。"""

    @staticmethod
    async def _load_task_case_map(task_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        if not task_ids:
            return {}

        case_docs = await (
            ExecutionTaskCaseDoc.find({"task_id": {"$in": task_ids}})
            .sort("order_no")
            .to_list()
        )
        cases_by_task: Dict[str, List[Dict[str, Any]]] = {}
        for case_doc in case_docs:
            cases_by_task.setdefault(case_doc.task_id, []).append(
                ExecutionTaskQueryMixin._serialize_task_case_doc(case_doc)
            )
        return cases_by_task

    @staticmethod
    def _serialize_task_doc(task_doc: ExecutionTaskDoc) -> Dict[str, Any]:
        """统一序列化任务摘要字段，避免重复手写响应。"""
        request_payload = getattr(task_doc, "request_payload", {}) or {}
        case_items = [
            case
            for case in request_payload.get("cases", [])
            if isinstance(case, dict)
        ]
        auto_case_ids = [
            case["auto_case_id"]
            for case in case_items
            if case.get("auto_case_id")
        ]
        current_case_index = getattr(task_doc, "current_case_index", 0)
        current_auto_case_id = None
        if 0 <= current_case_index < len(case_items):
            current_auto_case_id = case_items[current_case_index].get("auto_case_id")

        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "source_task_id": getattr(task_doc, "source_task_id", None),
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
            "auto_case_ids": auto_case_ids,
            "current_case_id": getattr(task_doc, "current_case_id", None),
            "current_auto_case_id": current_auto_case_id,
            "current_case_index": current_case_index,
            "planned_at": task_doc.planned_at,
            "triggered_at": task_doc.triggered_at,
            "created_at": task_doc.created_at,
            "updated_at": task_doc.updated_at,
        }

    @staticmethod
    def _serialize_task_case_doc(case_doc: ExecutionTaskCaseDoc) -> Dict[str, Any]:
        case_snapshot = dict(case_doc.case_snapshot or {})
        return {
            "task_id": case_doc.task_id,
            "case_id": case_doc.case_id,
            "auto_case_id": case_snapshot.get("auto_case_id"),
            "order_no": case_doc.order_no,
            "title": case_snapshot.get("title"),
            "status": case_doc.status,
            "progress_percent": case_doc.progress_percent,
            "dispatch_status": case_doc.dispatch_status,
            "dispatch_attempts": case_doc.dispatch_attempts,
            "event_count": getattr(case_doc, "event_count", 0),
            "failure_message": getattr(case_doc, "failure_message", None),
            "started_at": case_doc.started_at,
            "finished_at": case_doc.finished_at,
            "last_event_id": case_doc.last_event_id,
            "last_event_at": getattr(case_doc, "last_event_at", None),
            "result_data": dict(case_doc.result_data or {}),
        }

    async def list_tasks(self) -> List[Dict[str, Any]]:
        """列出全部未删除的执行任务。"""
        docs = await (
            ExecutionTaskDoc.find({"is_deleted": False})
            .sort("-created_at")
            .to_list()
        )
        serialized_tasks = [self._serialize_task_doc(task_doc) for task_doc in docs]
        task_ids = [task_doc.task_id for task_doc in docs]
        cases_by_task = await self._load_task_case_map(task_ids)

        for task_item in serialized_tasks:
            task_item["cases"] = cases_by_task.get(task_item["task_id"], [])
        return serialized_tasks

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态详情。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        result = self._serialize_task_doc(task_doc)
        result["consumed_at"] = task_doc.consumed_at
        result["dispatch_response"] = task_doc.dispatch_response
        result["dispatch_error"] = task_doc.dispatch_error
        result["request_payload"] = task_doc.request_payload
        return result
