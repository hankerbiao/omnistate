from __future__ import annotations

from typing import Any

from app.modules.test_specs.repository.models import TestCaseDoc, TestRequirementDoc


class TestSpecsWorkflowProjectionHook:
    """测试规格模块的工作流投影钩子，用于同步工作项删除与业务投影文档状态。"""

    async def before_delete(self, work_item: dict[str, Any]) -> None:
        """
        工作项删除前校验：
        - 需求必须存在对应的需求投影；
        - 需求下仍有关联测试用例时，不允许删除；
        - 测试用例必须存在对应的用例投影。
        """
        work_item_id = str(work_item.get("id") or "")
        type_code = str(work_item.get("type_code") or "")
        if type_code == "REQUIREMENT":
            requirement = await TestRequirementDoc.find_one(
                {"workflow_item_id": work_item_id, "is_deleted": False}
            )
            if requirement is None:
                raise ValueError("linked requirement not found")

            # 需求作为测试用例的上游引用，存在下游用例时需要先清理依赖关系。
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
        """工作项删除成功后，将对应的需求或测试用例投影标记为软删除。"""
        work_item_id = str(work_item.get("id") or "")
        type_code = str(work_item.get("type_code") or "")
        projection_doc = await self._find_projection_doc(work_item_id, type_code)
        if projection_doc is None:
            return

        projection_doc.is_deleted = True
        await projection_doc.save()

    @staticmethod
    async def _find_projection_doc(work_item_id: str, type_code: str) -> Any | None:
        """根据工作项类型查找对应的未删除投影文档。"""
        if type_code == "REQUIREMENT":
            return await TestRequirementDoc.find_one(
                {"workflow_item_id": work_item_id, "is_deleted": False}
            )
        if type_code == "TEST_CASE":
            return await TestCaseDoc.find_one(
                {"workflow_item_id": work_item_id, "is_deleted": False}
            )
        return None
