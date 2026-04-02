from __future__ import annotations

from pymongo.asynchronous.client_session import AsyncClientSession

from app.modules.workflow.application.ports import WorkflowItemGateway
from app.modules.workflow.service.workflow_service import AsyncWorkflowService


class AsyncWorkflowServiceAdapter(WorkflowItemGateway):
    def __init__(self, workflow_service: AsyncWorkflowService) -> None:
        self._workflow_service = workflow_service

    async def create_work_item(
        self,
        type_code: str,
        title: str,
        content: str,
        creator_id: str,
        parent_item_id: str | None = None,
        session: AsyncClientSession | None = None,
    ) -> dict[str, object]:
        return await self._workflow_service.create_item(
            type_code=type_code,
            title=title,
            content=content,
            creator_id=creator_id,
            parent_item_id=parent_item_id,
            session=session,
        )

    async def get_work_item_by_id(self, item_id: str) -> dict[str, object] | None:
        return await self._workflow_service.get_item_by_id(item_id)
