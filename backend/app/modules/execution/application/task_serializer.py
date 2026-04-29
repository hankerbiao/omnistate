"""执行任务响应序列化 collaborator。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)


class ExecutionTaskSerializer:
    """统一序列化任务与任务用例响应。"""

    @staticmethod
    async def load_task_case_map(task_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
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
                ExecutionTaskSerializer.serialize_task_case_doc(case_doc)
            )
        return cases_by_task

    @staticmethod
    def serialize_task_doc(task_doc: ExecutionTaskDoc) -> Dict[str, Any]:
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
    def serialize_task_case_doc(case_doc: ExecutionTaskCaseDoc) -> Dict[str, Any]:
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
