"""
WorkflowStatusQuery 默认实现

通过 WorkflowQueryService 查询工作流事项状态，供跨模块使用。
"""

from __future__ import annotations

from typing import Any

from app.modules.workflow.application.ports import WorkflowStatusQueryPort
from app.modules.workflow.application.query_service import WorkflowQueryService


class WorkflowStatusQuery(WorkflowStatusQueryPort):
    """WorkflowStatusQueryPort 的默认实现，委托给 WorkflowQueryService。"""

    def __init__(self, query_service: WorkflowQueryService | None = None) -> None:
        self._query_service = query_service or WorkflowQueryService()

    async def get_workflow_details(
        self, workflow_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """批量查询工作流事项状态。"""
        result: dict[str, dict[str, Any]] = {}
        for wid in workflow_ids:
            item = await self._query_service.get_item_by_id(wid)
            if item:
                result[wid] = {
                    "status": item.get("current_state"),
                    "creator": item.get("creator_id"),
                    "current_owner": item.get("current_owner_id"),
                }
        return result

    async def get_work_item_by_id(
        self, item_id: str
    ) -> dict[str, Any] | None:
        """查询单个工作流事项。"""
        return await self._query_service.get_item_by_id(item_id)
