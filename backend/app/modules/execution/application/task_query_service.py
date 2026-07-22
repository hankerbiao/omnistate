"""执行任务查询应用服务。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.execution.application.task_serializer import ExecutionTaskSerializer
from app.modules.execution_plan.application.ports import ExecutionResultStatsPort
from app.modules.execution.repository.models import ExecutionBizLogDoc, ExecutionTaskDoc


class ExecutionTaskQueryService(ExecutionResultStatsPort):
    """任务查询与序列化能力。"""

    @staticmethod
    async def _load_task_case_map(task_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        return await ExecutionTaskSerializer.load_task_case_map(task_ids)

    @staticmethod
    def _serialize_task_doc(task_doc: ExecutionTaskDoc) -> Dict[str, Any]:
        return ExecutionTaskSerializer.serialize_task_doc(task_doc)

    @staticmethod
    def _serialize_task_case_doc(case_doc: Any) -> Dict[str, Any]:
        return ExecutionTaskSerializer.serialize_task_case_doc(case_doc)

    async def count_passed_tasks(self, task_ids: List[str]) -> int:
        """统计指定任务里最终通过的数量。

        这是给 execution_plan 使用的只读端口实现，避免计划模块直接读 execution 仓储模型。
        """
        unique_task_ids = list(dict.fromkeys(task_ids))
        if not unique_task_ids:
            return 0
        docs = await ExecutionTaskDoc.find(
            ExecutionTaskDoc.task_id.is_in(unique_task_ids),
            ExecutionTaskDoc.is_deleted == False,  # noqa: E712
        ).to_list()
        return sum(1 for doc in docs if doc.overall_status == "PASSED")

    async def list_tasks(self) -> List[Dict[str, Any]]:
        """列出全部未删除的执行任务。"""
        docs = await (
            ExecutionTaskDoc.find({"is_deleted": False})
            .sort("-created_at")
            .to_list()
        )
        return await self._serialize_tasks_with_cases(docs)

    @staticmethod
    async def _serialize_tasks_with_cases(docs: List[ExecutionTaskDoc]) -> List[Dict[str, Any]]:
        serialized_tasks = [ExecutionTaskSerializer.serialize_task_doc(task_doc) for task_doc in docs]
        task_ids = [task_doc.task_id for task_doc in docs]
        cases_by_task = await ExecutionTaskSerializer.load_task_case_map(task_ids)

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
        # 补充 case 列表，供前端展示执行结果
        case_map = await self._load_task_case_map([task_id])
        result["cases"] = case_map.get(task_id, [])
        return result

    async def get_task_timeline(self, task_id: str, limit: int = 200) -> Dict[str, Any]:
        """获取任务平台侧业务轨迹日志时间线。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        biz_logs = await self.list_task_biz_logs(task_id, limit=limit)

        return {
            "biz_logs": biz_logs,
            "events": [],
        }

    async def list_task_biz_logs(self, task_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """查询任务平台侧业务轨迹日志。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        docs = await (
            ExecutionBizLogDoc.find(ExecutionBizLogDoc.task_id == task_id)
            .sort("-created_at")
            .limit(limit)
            .to_list()
        )
        return [
            {
                "id": str(doc.id),
                "task_id": doc.task_id,
                "case_id": doc.case_id,
                "event_id": doc.event_id,
                "node": doc.node,
                "action": doc.action,
                "outcome": doc.outcome,
                "status_before": doc.status_before,
                "status_after": doc.status_after,
                "operator_id": doc.operator_id,
                "request_id": doc.request_id,
                "detail": doc.detail,
                "level": doc.level,
                "created_at": doc.created_at,
            }
            for doc in docs
        ]
