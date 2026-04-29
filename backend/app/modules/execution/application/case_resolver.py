"""执行任务 case 解析 collaborator。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.modules.test_specs.repository.models import AutomationTestCaseDoc, TestCaseDoc


@dataclass(frozen=True)
class AutoCaseDispatchBinding:
    """自动化用例到执行下发字段的解析结果。"""

    auto_case_id: str
    case_id: str
    script_entity_id: str | None
    script_path: str
    script_name: str


class ExecutionCaseResolver:
    """解析测试用例与自动化用例的下发绑定关系。"""

    async def resolve_case_dispatch_bindings_by_auto_case_ids(
        self,
        auto_case_ids: List[str],
    ) -> List[AutoCaseDispatchBinding]:
        """将 auto_case_id 列表解析为下发所需的完整脚本元数据。"""
        auto_docs = await AutomationTestCaseDoc.find({
            "auto_case_id": {"$in": auto_case_ids},
            "is_deleted": False,
        }).to_list()
        auto_doc_mapping = {doc.auto_case_id: doc for doc in auto_docs}

        missing_auto_case_ids = [
            auto_case_id for auto_case_id in auto_case_ids if auto_case_id not in auto_doc_mapping
        ]
        if missing_auto_case_ids:
            raise KeyError(f"Automation test cases not found: {missing_auto_case_ids}")

        source_case_ids = [auto_doc_mapping[auto_case_id].dml_manual_case_id for auto_case_id in auto_case_ids]
        docs = await TestCaseDoc.find({
            "case_id": {"$in": source_case_ids},
            "is_deleted": False,
        }).to_list()

        found_case_ids = {getattr(doc, "case_id", None) for doc in docs}
        missing_source_case_ids = [
            source_case_id for source_case_id in source_case_ids if source_case_id not in found_case_ids
        ]
        if missing_source_case_ids:
            missing_bindings = [
                {
                    "auto_case_id": auto_case_id,
                    "dml_manual_case_id": auto_doc_mapping[auto_case_id].dml_manual_case_id,
                }
                for auto_case_id in auto_case_ids
                if auto_doc_mapping[auto_case_id].dml_manual_case_id in missing_source_case_ids
            ]
            raise KeyError(
                "Automation test cases linked manual cases not found: "
                f"{missing_bindings}"
            )

        mapping: dict[str, List[str]] = {}
        for doc in docs:
            source_case_id = getattr(doc, "case_id", None)
            if not source_case_id:
                continue
            mapping.setdefault(source_case_id, []).append(doc.case_id)

        ambiguous = {
            source_case_id: case_ids
            for source_case_id, case_ids in mapping.items()
            if len(case_ids) > 1
        }
        if ambiguous:
            raise ValueError(f"Automation test cases linked to multiple test cases: {ambiguous}")

        bindings: List[AutoCaseDispatchBinding] = []
        for auto_case_id in auto_case_ids:
            auto_doc = auto_doc_mapping[auto_case_id]
            case_id = mapping[auto_doc.dml_manual_case_id][0]
            script_path = getattr(auto_doc, "script_path", None)
            script_name = getattr(auto_doc, "script_name", None)
            if not script_path:
                raise ValueError(f"script_path is required for automation test case: {auto_case_id}")
            if not script_name:
                raise ValueError(f"script_name is required for automation test case: {auto_case_id}")
            bindings.append(
                AutoCaseDispatchBinding(
                    auto_case_id=auto_case_id,
                    case_id=case_id,
                    script_entity_id=getattr(getattr(auto_doc, "script_ref", None), "entity_id", None),
                    script_path=script_path,
                    script_name=script_name,
                )
            )
        return bindings

    async def resolve_auto_case_ids_by_case_ids(self, case_ids: List[str]) -> List[str]:
        """根据平台 case_id 反查 auto_case_id，保留原始顺序。"""
        auto_docs = await AutomationTestCaseDoc.find({
            "dml_manual_case_id": {"$in": case_ids},
            "is_deleted": False,
        }).to_list()
        auto_mapping = {doc.dml_manual_case_id: doc.auto_case_id for doc in auto_docs}
        missing_case_ids = [case_id for case_id in case_ids if case_id not in auto_mapping]
        if missing_case_ids:
            raise KeyError(f"Test cases not linked to automation test cases: {missing_case_ids}")
        return [auto_mapping[case_id] for case_id in case_ids]
