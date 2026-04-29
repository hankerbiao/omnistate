from __future__ import annotations

from typing import Any, Protocol

from pymongo.asynchronous.client_session import AsyncClientSession


class WorkflowMutationHook(Protocol):
    """工作项变更钩子协议。

    由具体实现类决定在删除前后需要执行什么副作用逻辑，
    例如审计、通知、联动清理等。
    """

    async def before_delete(self, work_item: dict[str, Any]) -> None: ...

    async def after_delete(self, work_item: dict[str, Any]) -> None: ...


class WorkflowItemGateway(Protocol):
    """工作项访问网关协议。

    应用层通过这个抽象访问工作项数据，而不直接依赖具体仓储实现。
    这样可以把业务流程与数据库实现解耦，便于测试和替换底层存储。
    """

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
