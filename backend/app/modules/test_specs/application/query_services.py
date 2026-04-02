"""Test specs query services."""

from __future__ import annotations

from typing import Optional

from app.modules.test_specs.service import RequirementService, TestCaseService


class RequirementQueryService:
    """Requirement read-side queries."""

    def __init__(self, requirement_service: RequirementService) -> None:
        self._requirement_service = requirement_service

    async def get_requirement(self, req_id: str) -> dict:
        return await self._requirement_service.get_requirement(req_id)

    async def list_requirements(
        self,
        status: Optional[str] = None,
        tpm_owner_id: Optional[str] = None,
        manual_dev_id: Optional[str] = None,
        auto_dev_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        return await self._requirement_service.list_requirements(
            status=status,
            tpm_owner_id=tpm_owner_id,
            manual_dev_id=manual_dev_id,
            auto_dev_id=auto_dev_id,
            limit=limit,
            offset=offset,
        )


class TestCaseQueryService:
    """Test case read-side queries."""

    def __init__(self, test_case_service: TestCaseService) -> None:
        self._test_case_service = test_case_service

    async def get_test_case(self, case_id: str) -> dict:
        return await self._test_case_service.get_test_case(case_id)

    async def list_test_cases(
        self,
        ref_req_id: Optional[str] = None,
        status: Optional[str] = None,
        owner_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        priority: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        return await self._test_case_service.list_test_cases(
            ref_req_id=ref_req_id,
            status=status,
            owner_id=owner_id,
            reviewer_id=reviewer_id,
            priority=priority,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
