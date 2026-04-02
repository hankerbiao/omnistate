from __future__ import annotations

from typing import Any, Protocol

from pymongo.asynchronous.client_session import AsyncClientSession


class WorkflowMutationHook(Protocol):
    async def before_delete(self, work_item: dict[str, Any]) -> None: ...

    async def after_delete(self, work_item: dict[str, Any]) -> None: ...


class WorkflowItemGateway(Protocol):
    async def create_work_item(
        self,
        type_code: str,
        title: str,
        content: str,
        creator_id: str,
        parent_item_id: str | None = None,
        session: AsyncClientSession | None = None,
    ) -> dict[str, Any]: ...

    async def get_work_item_by_id(self, item_id: str) -> dict[str, Any] | None: ...
