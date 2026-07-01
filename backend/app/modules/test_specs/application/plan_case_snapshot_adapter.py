"""执行计划测试用例快照适配器。

由 test_specs 模块提供实现，适配到 execution_plan 的 CaseSnapshotResolverPort。
"""
from __future__ import annotations

from app.modules.execution_plan.application.ports import CaseSnapshot, CaseSnapshotResolverPort
from app.modules.test_specs.repository.models import AutomationTestCaseDoc, TestCaseDoc


class PlanCaseSnapshotAdapter(CaseSnapshotResolverPort):
    """适配 TestCaseDoc/AutomationTestCaseDoc 到 CaseSnapshotResolverPort。

    将 execution_plan 的用例快照查询转换为 test_specs 的 Document 查询，
    消除 execution_plan 对 test_specs.repository.models 的直接依赖。
    """

    async def resolve_case_snapshot(self, ref_type: str, case_id: str) -> CaseSnapshot:
        if ref_type == "manual":
            case_doc = await TestCaseDoc.find_one(
                TestCaseDoc.case_id == case_id,
                TestCaseDoc.is_deleted == False,  # noqa: E712
            )
            if not case_doc:
                raise ValueError(f"手工用例不存在: {case_id}")
            component = case_doc.lab_id or ""
            if case_doc.catalog_path:
                component = "/".join(case_doc.catalog_path[:2]) or component
            return CaseSnapshot(
                case_title=case_doc.title,
                component=component,
                priority=case_doc.priority or "",
                manual_case_id=case_doc.case_id,
            )

        auto_doc = await AutomationTestCaseDoc.find_one(
            AutomationTestCaseDoc.auto_case_id == case_id,
            AutomationTestCaseDoc.is_deleted == False,  # noqa: E712
        )
        if not auto_doc:
            raise ValueError(f"自动化用例不存在: {case_id}")
        manual_doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == auto_doc.linked_manual_case_id,
            TestCaseDoc.is_deleted == False,  # noqa: E712
        )
        component = ""
        priority = ""
        if manual_doc:
            component = manual_doc.lab_id or ""
            if manual_doc.catalog_path:
                component = "/".join(manual_doc.catalog_path[:2]) or component
            priority = manual_doc.priority or ""
        return CaseSnapshot(
            case_title=auto_doc.name,
            component=component,
            priority=priority,
            manual_case_id=auto_doc.linked_manual_case_id,
        )
