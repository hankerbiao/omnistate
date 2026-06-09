"""执行任务 case 解析 collaborator。

通过 TestCaseMetadataQueryPort 读取测试用例元数据，
不直接依赖 test_specs 的 persistence 模型。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.modules.test_specs.application.ports import (
    AutoCaseDispatchInfo,
    TestCaseMetadataQueryPort,
)
from app.shared.domain.exceptions import NotFoundError, ValidationError


@dataclass(frozen=True)
class AutoCaseDispatchBinding:
    """自动化用例到执行下发字段的解析结果。"""

    auto_case_id: str
    case_id: str
    script_entity_id: str | None
    script_path: str
    script_name: str


class ExecutionCaseResolver:
    """解析自动化用例的下发绑定关系。"""

    def __init__(self, case_metadata_query: TestCaseMetadataQueryPort) -> None:
        self._query = case_metadata_query

    async def resolve_case_dispatch_bindings_by_auto_case_ids(
        self,
        auto_case_ids: List[str],
    ) -> List[AutoCaseDispatchBinding]:
        """将 auto_case_id 列表解析为下发所需的完整脚本元数据。"""
        infos = await self._query.resolve_case_dispatch_bindings(auto_case_ids)

        bindings: List[AutoCaseDispatchBinding] = []
        for info in infos:
            bindings.append(
                AutoCaseDispatchBinding(
                    auto_case_id=info.auto_case_id,
                    case_id=info.case_id,
                    script_entity_id=info.script_entity_id,
                    script_path=info.script_path,
                    script_name=info.script_name,
                )
            )
        return bindings

    async def resolve_auto_case_ids_by_case_ids(self, case_ids: List[str]) -> List[str]:
        """根据平台 case_id 反查 auto_case_id，保留原始顺序。"""
        return await self._query.resolve_auto_case_ids(case_ids)
