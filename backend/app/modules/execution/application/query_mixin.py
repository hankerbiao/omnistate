"""执行任务查询相关服务能力。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.modules.execution.repository.models import ExecutionTaskDoc


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
