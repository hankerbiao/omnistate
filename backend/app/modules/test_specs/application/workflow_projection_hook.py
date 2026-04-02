from __future__ import annotations

from typing import Any

from app.modules.test_specs.repository.models import TestCaseDoc, TestRequirementDoc


class TestSpecsWorkflowProjectionHook:
    async def before_delete(self, work_item: dict[str, Any]) -> None:
        work_item_id = str(work_item.get("id") or "")
        type_code = str(work_item.get("type_code") or "")
        if type_code == "REQUIREMENT":
            requirement = await TestRequirementDoc.find_one(
                {"workflow_item_id": work_item_id, "is_deleted": False}
            )
            if requirement is None:
                raise ValueError("linked requirement not found")

            related_cases = await TestCaseDoc.find(
                {"ref_req_id": requirement.req_id, "is_deleted": False}
            ).count()
            if related_cases > 0:
                raise ValueError("requirement has related test cases")
            return

        if type_code == "TEST_CASE":
            test_case = await TestCaseDoc.find_one(
                {"workflow_item_id": work_item_id, "is_deleted": False}
            )
            if test_case is None:
                raise ValueError("linked test case not found")

    async def after_delete(self, work_item: dict[str, Any]) -> None:
        work_item_id = str(work_item.get("id") or "")
        type_code = str(work_item.get("type_code") or "")
        projection_doc = await self._find_projection_doc(work_item_id, type_code)
        if projection_doc is None:
            return

        projection_doc.is_deleted = True
        await projection_doc.save()

    @staticmethod
    async def _find_projection_doc(work_item_id: str, type_code: str) -> Any | None:
        if type_code == "REQUIREMENT":
            return await TestRequirementDoc.find_one(
                {"workflow_item_id": work_item_id, "is_deleted": False}
            )
        if type_code == "TEST_CASE":
            return await TestCaseDoc.find_one(
                {"workflow_item_id": work_item_id, "is_deleted": False}
            )
        return None
