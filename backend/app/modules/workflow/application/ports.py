from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from pymongo.asynchronous.client_session import AsyncClientSession


class WorkflowMutationHook(Protocol):
    """工作项变更钩子协议。

    由具体实现类决定在删除前后需要执行什么副作用逻辑，
    例如审计、通知、联动清理等。
    """

    async def before_delete(self, work_item: dict[str, Any]) -> None: ...

    async def after_delete(self, work_item: dict[str, Any]) -> None: ...

    async def after_transition(self, transition_result: dict[str, Any]) -> None:
        """状态流转完成后触发。

        Args:
            transition_result: 包含 work_item_id, from_state, to_state,
                                action, new_owner_id, work_item 等字段。

        当 new_owner_id 与操作人不同时，通常需要发送通知。
        """
        ...

    async def after_reassign(self, reassign_result: dict[str, Any]) -> None:
        """重新分配完成后触发。

        Args:
            reassign_result: 包含 current_owner_id, title, type_code 等字段。

        当 current_owner_id 与操作人不同时，通常需要发送通知。
        """
        ...


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
        initial_state: str | None = None,
        session: AsyncClientSession | None = None,
    ) -> dict[str, Any]: ...

    async def get_work_item_by_id(self, item_id: str) -> dict[str, Any] | None: ...


class WorkflowStatusQueryPort(ABC):
    """工作流状态查询端口。

    允许跨模块通过此端口读取工作流事项的状态信息，
    而不直接依赖 workflow 的 persistence 模型。
    """

    @abstractmethod
    async def get_workflow_details(
        self, workflow_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """批量查询工作流事项的状态信息。

        Args:
            workflow_ids: 工作流事项 ID 列表。

        Returns:
            {workflow_id: {status, creator, current_owner, ...}} 的映射。
            不存在的 ID 不会出现在结果中。
        """
        ...

    @abstractmethod
    async def get_work_item_by_id(
        self, item_id: str
    ) -> dict[str, Any] | None:
        """查询单个工作流事项。"""
        ...
