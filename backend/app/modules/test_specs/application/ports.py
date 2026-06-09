"""
测试规格模块的查询端口定义。

允许 execution 等模块通过此端口读取测试用例元数据，
而不直接依赖 persistence 模型。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AutoCaseDispatchInfo:
    """自动化用例分发所需的信息。"""
    auto_case_id: str
    case_id: str
    script_entity_id: str | None
    script_path: str
    script_name: str


class TestCaseMetadataQueryPort(ABC):
    """测试用例元数据查询端口。

    允许 execution 模块通过此端口读取测试用例元数据以构建分发指令，
    而不直接导入 test_specs 的 repository 模型。
    """

    @abstractmethod
    async def resolve_case_dispatch_bindings(
        self, auto_case_ids: list[str]
    ) -> list[AutoCaseDispatchInfo]:
        """根据自动化用例 ID 列表解析分发所需的绑定信息。"""
        ...

    @abstractmethod
    async def resolve_auto_case_ids(self, case_ids: list[str]) -> list[str]:
        """根据手工用例 ID 列表解析关联的自动化用例 ID。"""
        ...

    @abstractmethod
    async def get_automation_case(self, auto_case_id: str) -> dict[str, Any] | None:
        """获取单个自动化用例的完整数据。"""
        ...
