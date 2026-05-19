"""Test case automation link integration tests."""
import pytest
from httpx import AsyncClient

from tests.integration.utils.helpers import unique_id


@pytest.mark.asyncio
async def test_link_automation_case_not_found(client_admin: AsyncClient):
    """6.1 - Link automation case with non-existent test case should return 404."""
    resp = await client_admin.post(
        "/api/v1/test-cases/nonexistent_case/automation-link",
        json={"auto_case_id": "AUTO-123", "version": "1.0"},
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_link_automation_case_no_permission(client_tester: AsyncClient):
    """6.2 - Link automation case without permission should return 403 or 404.

    Returns 403 if permission check happens first, or 404 if entity check happens first.
    """
    resp = await client_tester.post(
        "/api/v1/test-cases/some_case/automation-link",
        json={"auto_case_id": "AUTO-123", "version": "1.0"},
    )
    assert resp.status_code in (403, 404), f"Expected 403/404, got {resp.status_code}"