"""Integration tests for test case catalog fields."""
import json

import pytest
from httpx import AsyncClient

from tests.integration.conftest import TestDataRegistry
from tests.integration.utils.helpers import (
    create_test_case_data,
    register_created_requirement,
    register_created_test_case,
    unique_id,
)


async def _ensure_default_lab(client: AsyncClient) -> str:
    resp = await client.get("/api/v1/catalog/labs")
    assert resp.status_code == 200
    for lab in resp.json().get("data") or []:
        if lab.get("code") == "DEFAULT":
            return lab["lab_id"]

    create_resp = await client.post(
        "/api/v1/catalog/labs",
        json={"code": "DEFAULT", "name": "默认", "sort_order": 0},
    )
    if create_resp.status_code == 201:
        return create_resp.json()["data"]["lab_id"]
    if create_resp.status_code == 409:
        resp = await client.get("/api/v1/catalog/labs")
        for lab in resp.json().get("data") or []:
            if lab.get("code") == "DEFAULT":
                return lab["lab_id"]
    raise AssertionError(f"Failed to ensure default lab: {create_resp.text}")


@pytest.mark.asyncio
async def test_create_test_case_requires_catalog_fields(client_admin: AsyncClient):
    resp = await client_admin.post(
        "/api/v1/test-cases",
        json={"title": f"No catalog {unique_id()}"},
    )
    assert resp.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_create_test_case_with_catalog(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    lab_id = await _ensure_default_lab(client_admin)
    req_resp = await client_admin.post(
        "/api/v1/requirements",
        json={"title": f"Req {unique_id()}", "description": "catalog test"},
    )
    ref_req_id = None
    if req_resp.status_code == 201:
        ref_req_id = req_resp.json()["data"]["req_id"]
        register_created_requirement(test_data_registry, req_resp.json()["data"])

    payload = create_test_case_data(
        ref_req_id=ref_req_id,
        lab_id=lab_id,
        catalog_path=["BIOS", "Release"],
    )
    resp = await client_admin.post("/api/v1/test-cases", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    register_created_test_case(test_data_registry, data)
    assert data["lab_id"] == lab_id
    assert data["catalog_path"] == ["bios", "release"]
    assert data.get("catalog_breadcrumb")


@pytest.mark.asyncio
async def test_list_test_cases_filter_by_lab_and_prefix(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    lab_id = await _ensure_default_lab(client_admin)
    prefix = [f"prefix_{unique_id()[:6].lower()}"]
    resp = await client_admin.post(
        "/api/v1/test-cases",
        json=create_test_case_data(lab_id=lab_id, catalog_path=prefix + ["child"]),
    )
    assert resp.status_code == 201, resp.text
    register_created_test_case(test_data_registry, resp.json()["data"])

    list_resp = await client_admin.get(
        "/api/v1/test-cases",
        params={
            "lab_id": lab_id,
            "catalog_prefix": json.dumps(prefix),
            "limit": 50,
        },
    )
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()["data"]
    assert any(item.get("catalog_path", [])[: len(prefix)] == prefix for item in items)


@pytest.mark.asyncio
async def test_catalog_suggestions_and_tree(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    lab_id = await _ensure_default_lab(client_admin)
    segment = f"seg_{unique_id()[:5].lower()}"
    resp = await client_admin.post(
        "/api/v1/test-cases",
        json=create_test_case_data(lab_id=lab_id, catalog_path=[segment]),
    )
    assert resp.status_code == 201, resp.text
    register_created_test_case(test_data_registry, resp.json()["data"])

    sug_resp = await client_admin.get(
        "/api/v1/catalog/suggestions",
        params={"lab_id": lab_id, "parent_path": "[]"},
    )
    assert sug_resp.status_code == 200, sug_resp.text
    segments = sug_resp.json()["data"]["segments"]
    assert segment in segments

    tree_resp = await client_admin.get("/api/v1/catalog/tree", params={"lab_id": lab_id})
    assert tree_resp.status_code == 200, tree_resp.text
    assert tree_resp.json()["data"]["lab_id"] == lab_id
