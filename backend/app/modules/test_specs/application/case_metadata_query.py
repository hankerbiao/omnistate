"""
TestCaseMetadataQuery 默认实现

读取 test_specs 的 Beanie 模型，实现 TestCaseMetadataQueryPort 接口。
execution 模块通过此端口访问用例元数据时，无需直接导入 repository 模型。
"""

from __future__ import annotations

from typing import Any

from app.modules.test_specs.application.ports import (
    AutoCaseDispatchInfo,
    TestCaseMetadataQueryPort,
)
from app.modules.test_specs.repository.models import AutomationTestCaseDoc


class TestCaseMetadataQuery(TestCaseMetadataQueryPort):
    """TestCaseMetadataQueryPort 的默认实现。"""

    async def resolve_case_dispatch_bindings(
        self, auto_case_ids: list[str]
    ) -> list[AutoCaseDispatchInfo]:
        """将 auto_case_id 列表解析为下发所需的完整脚本元数据。"""
        from app.shared.domain.exceptions import NotFoundError, ValidationError

        auto_docs = await AutomationTestCaseDoc.find({
            "auto_case_id": {"$in": auto_case_ids},
            "is_deleted": False,
        }).to_list()
        auto_doc_mapping = {doc.auto_case_id: doc for doc in auto_docs}

        missing = [aid for aid in auto_case_ids if aid not in auto_doc_mapping]
        if missing:
            raise NotFoundError(f"Automation test cases not found: {missing}")

        bindings: list[AutoCaseDispatchInfo] = []
        for auto_case_id in auto_case_ids:
            doc = auto_doc_mapping[auto_case_id]
            script_path = getattr(doc, "script_path", None)
            script_name = getattr(doc, "script_name", None)
            if not script_path:
                raise ValidationError(
                    f"script_path is required for automation test case: {auto_case_id}"
                )
            if not script_name:
                raise ValidationError(
                    f"script_name is required for automation test case: {auto_case_id}"
                )
            bindings.append(
                AutoCaseDispatchInfo(
                    auto_case_id=auto_case_id,
                    case_id=doc.dml_manual_case_id or auto_case_id,
                    script_entity_id=getattr(
                        getattr(doc, "script_ref", None), "entity_id", None
                    ),
                    script_path=script_path,
                    script_name=script_name,
                )
            )
        return bindings

    async def resolve_auto_case_ids(self, case_ids: list[str]) -> list[str]:
        """根据平台 case_id 反查 auto_case_id，保留原始顺序。"""
        from app.shared.domain.exceptions import NotFoundError

        auto_docs = await AutomationTestCaseDoc.find({
            "dml_manual_case_id": {"$in": case_ids},
            "is_deleted": False,
        }).to_list()
        mapping = {doc.dml_manual_case_id: doc.auto_case_id for doc in auto_docs}
        missing = [case_id for case_id in case_ids if case_id not in mapping]
        if missing:
            raise NotFoundError(
                f"Test cases not linked to automation test cases: {missing}"
            )
        return [mapping[case_id] for case_id in case_ids]

    async def get_automation_case(self, auto_case_id: str) -> dict[str, Any] | None:
        """获取单个自动化用例数据。"""
        doc = await AutomationTestCaseDoc.find_one({
            "auto_case_id": auto_case_id,
            "is_deleted": False,
        })
        if doc is None:
            return None
        return doc.model_dump()
