from __future__ import annotations

from pymongo.asynchronous.client_session import AsyncClientSession

from app.modules.workflow.application import (
    WorkflowItemGateway,
    WorkflowStatusQueryPort,
    WorkflowQueryService,
)
from app.modules.workflow.application.mutation_service import WorkflowMutationService


class WorkflowServicesAdapter(WorkflowItemGateway, WorkflowStatusQueryPort):
    """Adapter exposing workflow query/mutation services as a test-specs gateway."""

    def __init__(
        self,
        mutation_service: WorkflowMutationService,
        query_service: WorkflowQueryService | None = None,
    ) -> None:
        self._mutation_service = mutation_service
        self._query_service = query_service

    async def create_work_item(
        self,
        type_code: str,
        title: str,
        content: str,
        creator_id: str,
        parent_item_id: str | None = None,
        initial_state: str | None = None,
        session: AsyncClientSession | None = None,
    ) -> dict[str, object]:
        return await self._mutation_service.create_item(
            type_code=type_code,
            title=title,
            content=content,
            creator_id=creator_id,
            parent_item_id=parent_item_id,
            initial_state=initial_state,
            session=session,
        )

    async def get_work_item_by_id(self, item_id: str) -> dict[str, object] | None:
        if self._query_service is None:
            raise RuntimeError("query_service is required to load work items")
        return await self._query_service.get_item_by_id(item_id)

    async def get_workflow_details(
        self, workflow_ids: list[str]
    ) -> dict[str, dict[str, object]]:
        if self._query_service is None:
            raise RuntimeError("query_service is required to load work item details")
        details: dict[str, dict[str, object]] = {}
        for workflow_id in workflow_ids:
            item = await self._query_service.get_item_by_id(workflow_id)
            if item is not None:
                details[workflow_id] = item
        return details

    async def list_work_item_ids_by_state(self, state: str) -> list[str]:
        if self._query_service is None:
            raise RuntimeError("query_service is required to load work item ids")
        return await self._query_service.list_work_item_ids_by_state(state)
