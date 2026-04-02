from __future__ import annotations

from typing import Any

from app.modules.workflow.application.mutation_service import WorkflowMutationService
from app.modules.workflow.application.query_service import WorkflowQueryService


class AsyncWorkflowService:
    """兼容层：对外保留旧入口，内部委托到 query/mutation services。"""

    def __init__(
        self,
        query_service: WorkflowQueryService | None = None,
        mutation_service: WorkflowMutationService | None = None,
    ) -> None:
        self._query_service = query_service or WorkflowQueryService()
        self._mutation_service = mutation_service or WorkflowMutationService()

    async def get_work_types(self) -> list[dict[str, Any]]:
        return await self._query_service.get_work_types()

    async def get_workflow_states(self) -> list[dict[str, Any]]:
        return await self._query_service.get_workflow_states()

    async def get_workflow_configs(self, type_code: str) -> list[dict[str, Any]]:
        return await self._query_service.get_workflow_configs(type_code)

    async def list_items(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await self._query_service.list_items(*args, **kwargs)

    async def list_items_sorted(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await self._query_service.list_items_sorted(*args, **kwargs)

    async def search_items(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return await self._query_service.search_items(*args, **kwargs)

    async def get_item_by_id(self, item_id: str) -> dict[str, Any] | None:
        return await self._query_service.get_item_by_id(item_id)

    async def get_logs(self, item_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._query_service.get_logs(item_id, limit)

    async def batch_get_logs(self, item_ids: list[str], limit: int = 20) -> dict[str, list[dict[str, Any]]]:
        return await self._query_service.batch_get_logs(item_ids, limit)

    async def get_item_with_transitions(self, item_id: str) -> dict[str, Any]:
        return await self._query_service.get_item_with_transitions(item_id)

    async def list_test_cases_for_requirement(self, requirement_id: str) -> list[dict[str, Any]]:
        return await self._query_service.list_test_cases_for_requirement(requirement_id)

    async def get_requirement_for_test_case(self, test_case_id: str) -> dict[str, Any] | None:
        return await self._query_service.get_requirement_for_test_case(test_case_id)

    async def create_item(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self._mutation_service.create_item(*args, **kwargs)

    async def handle_transition(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self._mutation_service.handle_transition(*args, **kwargs)

    async def delete_item(self, *args: Any, **kwargs: Any) -> bool:
        return await self._mutation_service.delete_item(*args, **kwargs)

    async def reassign_item(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self._mutation_service.reassign_item(*args, **kwargs)
