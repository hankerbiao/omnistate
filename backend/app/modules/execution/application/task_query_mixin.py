"""执行任务查询相关能力。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.execution.application.task_serializer import ExecutionTaskSerializer
from app.modules.execution.repository.models import (
    ExecutionTaskDoc,
)


class ExecutionTaskQueryMixin:
    """提供任务查询与统一序列化能力。"""

    @staticmethod
    async def _load_task_case_map(task_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        return await ExecutionTaskSerializer.load_task_case_map(task_ids)

    @staticmethod
    def _serialize_task_doc(task_doc: ExecutionTaskDoc) -> Dict[str, Any]:
        return ExecutionTaskSerializer.serialize_task_doc(task_doc)

    @staticmethod
    def _serialize_task_case_doc(case_doc: Any) -> Dict[str, Any]:
        return ExecutionTaskSerializer.serialize_task_case_doc(case_doc)

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
