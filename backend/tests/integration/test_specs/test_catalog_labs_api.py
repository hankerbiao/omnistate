"""Integration tests for catalog labs API."""
import pytest
from httpx import AsyncClient

from tests.integration.conftest import TestDataRegistry
from tests.integration.utils.helpers import delete_catalog_lab, register_created_lab, unique_id


async def _create_lab(
    client: AsyncClient,
    test_data_registry: TestDataRegistry,
    code: str | None = None,
    name: str | None = None,
) -> dict:
    suffix = unique_id()
    resp = await client.post(
        "/api/v1/catalog/labs",
        json={
            "code": code or f"L{suffix.replace('_', '')[-10:].upper()}",
            "name": name or f"Lab {suffix}",
            "sort_order": 0,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    register_created_lab(test_data_registry, data)
    return data


@pytest.mark.asyncio
async def test_list_labs(client_admin: AsyncClient):
    resp = await client_admin.get("/api/v1/catalog/labs")
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json()["data"], list)


@pytest.mark.asyncio
async def test_create_lab_preserves_code_case(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    suffix = unique_id()
    code = f"Mixed_{suffix[-6:]}"
    resp = await client_admin.post(
        "/api/v1/catalog/labs",
        json={"code": code, "name": f"Mixed Case {suffix}", "sort_order": 0},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    register_created_lab(test_data_registry, data)
    assert data["code"] == code
    assert data["lab_id"] == f"LAB-{code}"


@pytest.mark.asyncio
async def test_create_and_update_lab(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    created = await _create_lab(client_admin, test_data_registry)
    lab_id = created["lab_id"]

    update_resp = await client_admin.put(
        f"/api/v1/catalog/labs/{lab_id}",
        json={"name": "Updated Lab Name", "sort_order": 10},
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()["data"]
    assert updated["name"] == "Updated Lab Name"
    assert updated["sort_order"] == 10
    assert updated["code"] == created["code"]


@pytest.mark.asyncio
async def test_create_lab_duplicate_code_conflict(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    code = f"DUP{unique_id().replace('_', '')[-8:].upper()}"
    await _create_lab(client_admin, test_data_registry, code=code, name="First")
    dup_resp = await client_admin.post(
        "/api/v1/catalog/labs",
        json={"code": code, "name": "Second"},
    )
    assert dup_resp.status_code == 409


@pytest.mark.asyncio
async def test_deactivate_lab_migrates_cases(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    source = await _create_lab(client_admin, test_data_registry)
    target = await _create_lab(client_admin, test_data_registry)

    case_id = f"TC-CAT-{unique_id()}"
    from pymongo import MongoClient
    from app.shared.config import get_settings

    client = MongoClient(get_settings().mongodb.uri)
    db = client[get_settings().mongodb.db_name]
    db["test_cases"].insert_one(
        {
            "case_id": case_id,
            "ref_req_id": "REQ-MOCK",
            "title": "Catalog migration case",
            "lab_id": source["lab_id"],
            "catalog_path": ["integration"],
            "catalog_path_key": "integration",
            "is_deleted": False,
            "version": 1,
            "is_active": True,
            "required_env": {},
            "tags": [],
            "attachments": [],
            "custom_fields": {},
            "approval_history": [],
        }
    )
    client.close()
    test_data_registry.register_test_case(case_id)

    resp = await client_admin.post(
        f"/api/v1/catalog/labs/{source['lab_id']}/deactivate",
        json={"target_lab_id": target["lab_id"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["is_active"] is False
    assert data.get("migrated_case_count", 0) >= 1

    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    remaining = db["test_cases"].count_documents(
        {"lab_id": source["lab_id"], "is_deleted": False}
    )
    migrated = db["test_cases"].count_documents(
        {"lab_id": target["lab_id"], "is_deleted": False}
    )
    client.close()
    assert remaining == 0
    assert migrated >= 1


@pytest.mark.asyncio
async def test_delete_lab_only_when_zero_cases(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    lab = await _create_lab(client_admin, test_data_registry)

    case_id = f"TC-BLOCK-{unique_id()}"
    from pymongo import MongoClient
    from app.shared.config import get_settings

    client = MongoClient(get_settings().mongodb.uri)
    db = client[get_settings().mongodb.db_name]
    db["test_cases"].insert_one(
        {
            "case_id": case_id,
            "ref_req_id": "REQ-MOCK",
            "title": "Block delete",
            "lab_id": lab["lab_id"],
            "catalog_path": ["integration"],
            "catalog_path_key": "integration",
            "is_deleted": False,
            "version": 1,
            "is_active": True,
            "required_env": {},
            "tags": [],
            "attachments": [],
            "custom_fields": {},
            "approval_history": [],
        }
    )
    client.close()
    test_data_registry.register_test_case(case_id)

    blocked = await client_admin.delete(f"/api/v1/catalog/labs/{lab['lab_id']}")
    assert blocked.status_code == 409

    empty_lab = await _create_lab(client_admin, test_data_registry)
    try:
        ok = await client_admin.delete(f"/api/v1/catalog/labs/{empty_lab['lab_id']}")
        assert ok.status_code == 204
        test_data_registry._lab_ids.remove(empty_lab["lab_id"])
    finally:
        await delete_catalog_lab(client_admin, empty_lab["lab_id"])


@pytest.mark.asyncio
async def test_catalog_labs_read_without_manage(client_tester: AsyncClient):
    resp = await client_tester.get("/api/v1/catalog/labs")
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_catalog_labs_manage_forbidden_for_tester(client_tester: AsyncClient):
    resp = await client_tester.post(
        "/api/v1/catalog/labs",
        json={"code": f"X{unique_id()[:4].upper()}", "name": "Forbidden"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_catalog_labs_manage_allowed_for_tpm(
    client_tpm: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    resp = await client_tpm.post(
        "/api/v1/catalog/labs",
        json={"code": f"T{unique_id().replace('_', '')[-8:].upper()}", "name": "TPM Lab"},
    )
    assert resp.status_code == 201, resp.text
    register_created_lab(test_data_registry, resp.json()["data"])
