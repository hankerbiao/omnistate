"""Integration test configuration and fixtures.

Sets up:
- FastAPI app with lifespan (MongoDB connection)
- Test users with various roles
- Authenticated HTTP clients for each role
- Test data cleanup mechanism

IMPORTANT: These tests require the MongoDB and other services to be running.
Before running tests, ensure test_admin user exists in MongoDB (recommended: cd backend && python scripts/create_user.py --user-id test_admin --username "Test Admin" --password Admin@123 --roles ADMIN --email test_admin@test.local --upsert):
  python -c "
    from pymongo import MongoClient
    import hashlib, secrets
    def hash_password(password):
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return salt, pwd_hash
    from app.shared.config import get_settings
    client = MongoClient(get_settings().mongodb.uri)
    db = client[get_settings().mongodb.db_name]
    db['users'].delete_one({'user_id': 'test_admin'})
    salt, pwd_hash = hash_password('Admin@123')
    db['users'].insert_one({
        'user_id': 'test_admin', 'username': 'Test Admin', 'email': 'test_admin@test.local',
        'password_salt': salt, 'password_hash': pwd_hash, 'role_ids': ['ADMIN'],
        'allowed_nav_views': [], 'status': 'ACTIVE'
    })
  "

RUNNING TESTS:
  cd backend
  pytest tests/integration/ -v

NOTE: Due to pytest-asyncio event loop scoping, tests work best when run individually
or with --dist=no flag for parallel execution.
"""
import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.shared.config import get_settings

logger = logging.getLogger(__name__)


# ==================== Test Data Registry ====================
# Tracks test data for cleanup after each test


class TestDataRegistry:
    """Registry to track test data for cleanup."""

    def __init__(self):
        self._work_item_ids: list[str] = []
        self._user_ids: list[str] = []
        self._case_ids: list[str] = []
        self._req_ids: list[str] = []
        self._relation_ids: list[str] = []
        self._perm_ids: list[str] = []
        self._nav_views: list[str] = []
        self._lab_ids: list[str] = []
        self._role_ids: list[str] = []

    def register_work_item(self, item_id: str):
        """Register a work item for cleanup."""
        self._work_item_ids.append(item_id)

    def register_user(self, user_id: str):
        """Register a user for cleanup."""
        self._user_ids.append(user_id)

    def register_test_case(self, case_id: str):
        """Register a test case for cleanup."""
        self._case_ids.append(case_id)

    def register_requirement(self, req_id: str):
        """Register a requirement for cleanup."""
        self._req_ids.append(req_id)

    def register_relation(self, relation_id: str):
        """Register a relation for cleanup."""
        self._relation_ids.append(relation_id)

    def register_permission(self, perm_id: str):
        """Register a permission for cleanup."""
        self._perm_ids.append(perm_id)

    def register_navigation_page(self, view: str):
        """Register a navigation page for cleanup."""
        self._nav_views.append(view)

    def register_lab(self, lab_id: str):
        """Register a catalog lab for cleanup."""
        self._lab_ids.append(lab_id)

    def register_role(self, role_id: str):
        """Register a test role for cleanup."""
        self._role_ids.append(role_id)

    async def cleanup(self):
        """Clean up all registered test data."""
        from bson import ObjectId
        from pymongo import MongoClient

        client = MongoClient(get_settings().mongodb.uri)
        db = client[get_settings().mongodb.db_name]

        def _warn(entity: str, entity_id: str, exc: Exception) -> None:
            logger.warning("Failed to cleanup %s %s: %s", entity, entity_id, exc)

        def _soft_delete_work_item(item_id: str) -> None:
            if not ObjectId.is_valid(item_id):
                return
            db["bus_work_items"].update_one(
                {"_id": ObjectId(item_id)},
                {"$set": {"is_deleted": True}},
            )

        # Cleanup work items (bus_work_items collection)
        for item_id in self._work_item_ids:
            try:
                _soft_delete_work_item(item_id)
            except Exception as exc:
                _warn("work_item", item_id, exc)

        # Cleanup test cases
        for case_id in self._case_ids:
            try:
                db["test_cases"].update_one(
                    {"case_id": case_id}, {"$set": {"is_deleted": True}}
                )
            except Exception as exc:
                _warn("test_case", case_id, exc)

        # Cleanup requirements (test_requirements collection)
        for req_id in self._req_ids:
            try:
                req_doc = db["test_requirements"].find_one(
                    {"req_id": req_id},
                    {"workflow_item_id": 1},
                )
                db["test_requirements"].update_one(
                    {"req_id": req_id}, {"$set": {"is_deleted": True}}
                )
                wf_id = (req_doc or {}).get("workflow_item_id")
                if wf_id:
                    _soft_delete_work_item(str(wf_id))
            except Exception as exc:
                _warn("requirement", req_id, exc)

        # Cleanup relations
        for relation_id in self._relation_ids:
            try:
                db["work_item_relations"].delete_many({"relation_id": relation_id})
            except Exception as exc:
                _warn("relation", relation_id, exc)

        # Cleanup users (not test_admin)
        for user_id in self._user_ids:
            if user_id != "test_admin":
                try:
                    db["users"].delete_many({"user_id": user_id})
                except Exception as exc:
                    _warn("user", user_id, exc)

        # Cleanup integration-test permissions (test_perm_* etc.)
        for perm_id in self._perm_ids:
            try:
                db["permissions"].delete_many({"perm_id": perm_id})
            except Exception as exc:
                _warn("permission", perm_id, exc)

        # Cleanup integration-test navigation pages
        for view in self._nav_views:
            try:
                db["navigation_pages"].delete_many({"view": view})
            except Exception as exc:
                _warn("navigation_page", view, exc)

        # Cleanup catalog labs (after test cases are soft-deleted)
        for lab_id in self._lab_ids:
            try:
                db["test_catalog_segments"].delete_many({"lab_id": lab_id})
                db["test_labs"].delete_many({"lab_id": lab_id})
            except Exception as exc:
                _warn("lab", lab_id, exc)

        # Cleanup integration-test roles (role_test_* etc.)
        for role_id in self._role_ids:
            if role_id not in {"ADMIN", "TPM", "REVIEWER", "MANUAL_DEV", "QA", "TESTER", "AUTO_DEV"}:
                try:
                    db["roles"].delete_many({"role_id": role_id})
                except Exception as exc:
                    _warn("role", role_id, exc)

        client.close()


# Global registry instance
_test_data_registry = TestDataRegistry()


@pytest.fixture
def test_data_registry():
    """Provide test data registry for tracking cleanup."""
    return _test_data_registry


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data():
    """Cleanup test data after each test runs.

    This fixture runs automatically after every test to clean up
    test data and prevent pollution of the database.
    """
    yield
    # Run cleanup after test completes
    await _test_data_registry.cleanup()
    # Clear the registry for next test
    _test_data_registry._work_item_ids.clear()
    _test_data_registry._user_ids.clear()
    _test_data_registry._case_ids.clear()
    _test_data_registry._req_ids.clear()
    _test_data_registry._relation_ids.clear()
    _test_data_registry._perm_ids.clear()
    _test_data_registry._nav_views.clear()
    _test_data_registry._lab_ids.clear()
    _test_data_registry._role_ids.clear()


@pytest_asyncio.fixture
async def app_with_lifespan():
    """FastAPI app with lifespan initialized for each test."""
    async with app.router.lifespan_context(app):
        yield app


@pytest_asyncio.fixture
async def admin_token(app_with_lifespan) -> str:
    """Get admin token for test setup. Requires test_admin user to exist in DB."""
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test")
        resp = await client.post(
            "/api/v1/auth/login",
            json={"user_id": "test_admin", "password": "Admin@123"},
        )
        if resp.status_code == 200:
            return resp.json()["data"]["access_token"]
        raise RuntimeError(f"Failed to login as admin: {resp.status_code} {resp.text}")


# Fixed integration-test accounts — reused across runs, not deleted per test.
INTEGRATION_TEST_USERS = [
    {"user_id": "integ_tpm", "role": "TPM", "name": "Integration TPM"},
    {"user_id": "integ_reviewer", "role": "REVIEWER", "name": "Integration Reviewer"},
    {"user_id": "integ_dev", "role": "MANUAL_DEV", "name": "Integration Developer"},
    {"user_id": "integ_qa", "role": "QA", "name": "Integration QA"},
    {"user_id": "integ_tester", "role": "TESTER", "name": "Integration Tester"},
    {"user_id": "integ_auto_dev", "role": "AUTO_DEV", "name": "Integration Auto Dev"},
    {"user_id": "integ_no_role", "role": None, "name": "Integration No Role"},
]


@pytest_asyncio.fixture
async def test_users(app_with_lifespan, admin_token) -> dict[str, dict[str, Any]]:
    """Ensure fixed integration users exist and return their tokens.

    Reuses stable user_id values (integ_*) instead of creating timestamped users
    on every test. Ephemeral users from individual tests are still tracked via
    TestDataRegistry and cleaned up after each test.
    """
    base_password = "Test@123"
    created_users: dict[str, dict[str, Any]] = {}

    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        for user_spec in INTEGRATION_TEST_USERS:
            resp = await client.post(
                "/api/v1/auth/users",
                json={
                    "user_id": user_spec["user_id"],
                    "username": user_spec["name"],
                    "password": base_password,
                    "email": f"{user_spec['user_id']}@test.local",
                },
            )
            if resp.status_code not in (201, 409):
                print(
                    f"Warning: ensure user {user_spec['user_id']}: "
                    f"{resp.status_code} {resp.text}"
                )

            if user_spec["role"]:
                role_resp = await client.patch(
                    f"/api/v1/auth/users/{user_spec['user_id']}/roles",
                    json={"role_ids": [user_spec["role"]]},
                )
                if role_resp.status_code != 200:
                    print(
                        f"Warning: Failed to assign role {user_spec['role']}: "
                        f"{role_resp.text}"
                    )

            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"user_id": user_spec["user_id"], "password": base_password},
            )
            if login_resp.status_code == 200:
                created_users[user_spec["role"] or "NO_ROLE"] = {
                    "user_id": user_spec["user_id"],
                    "token": login_resp.json()["data"]["access_token"],
                }
            else:
                print(
                    f"Warning: Failed to login {user_spec['user_id']}: "
                    f"{login_resp.status_code} {login_resp.text}"
                )

    return created_users


@pytest_asyncio.fixture
async def client_admin(app_with_lifespan, admin_token) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client as admin (uses test_admin user)."""
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {admin_token}"})
        yield client
        await client.aclose()


@pytest_asyncio.fixture
async def client_tpm(app_with_lifespan, test_users) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client as TPM."""
    token = test_users.get("TPM", test_users.get("NO_ROLE"))["token"]
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})
        yield client
        await client.aclose()


@pytest_asyncio.fixture
async def client_reviewer(app_with_lifespan, test_users) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client as REVIEWER."""
    token = test_users.get("REVIEWER", test_users.get("NO_ROLE"))["token"]
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})
        yield client
        await client.aclose()


@pytest_asyncio.fixture
async def client_dev(app_with_lifespan, test_users) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client as MANUAL_DEV."""
    token = test_users.get("MANUAL_DEV", test_users.get("NO_ROLE"))["token"]
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})
        yield client
        await client.aclose()


@pytest_asyncio.fixture
async def client_qa(app_with_lifespan, test_users) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client as QA."""
    token = test_users.get("QA", test_users.get("NO_ROLE"))["token"]
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})
        yield client
        await client.aclose()


@pytest_asyncio.fixture
async def client_tester(app_with_lifespan, test_users) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client as TESTER."""
    token = test_users.get("TESTER", test_users.get("NO_ROLE"))["token"]
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})
        yield client
        await client.aclose()


@pytest_asyncio.fixture
async def client_no_role(app_with_lifespan, test_users) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client with no role (for negative tests)."""
    token = test_users.get("NO_ROLE")["token"]
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})
        yield client
        await client.aclose()


@pytest_asyncio.fixture
async def client_auto_dev(app_with_lifespan, test_users) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client as AUTO_DEV."""
    token = test_users.get("AUTO_DEV", test_users.get("NO_ROLE"))["token"]
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})
        yield client
        await client.aclose()