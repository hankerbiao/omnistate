"""Integration test configuration and fixtures.

Sets up:
- FastAPI app with lifespan (MongoDB connection)
- Test users with various roles
- Authenticated HTTP clients for each role
- Test data cleanup mechanism

IMPORTANT: These tests require the MongoDB and other services to be running.
Before running tests, ensure test_admin user exists in MongoDB:
  python -c "
    from pymongo import MongoClient
    import hashlib, secrets
    def hash_password(password):
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return salt, pwd_hash
    client = MongoClient('mongodb://10.17.154.252:27018')
    db = client['workflow_db']
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
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


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

    async def cleanup(self):
        """Clean up all registered test data."""
        from pymongo import MongoClient

        client = MongoClient("mongodb://10.17.154.252:27018")
        db = client["workflow_db"]

        # Cleanup work items (soft delete by setting is_deleted=True)
        for item_id in self._work_item_ids:
            try:
                db["work_items"].update_one(
                    {"item_id": item_id}, {"$set": {"is_deleted": True}}
                )
            except Exception:
                pass

        # Cleanup test cases
        for case_id in self._case_ids:
            try:
                db["test_cases"].update_one(
                    {"case_id": case_id}, {"$set": {"is_deleted": True}}
                )
            except Exception:
                pass

        # Cleanup requirements
        for req_id in self._req_ids:
            try:
                db["requirements"].update_one(
                    {"req_id": req_id}, {"$set": {"is_deleted": True}}
                )
            except Exception:
                pass

        # Cleanup relations
        for relation_id in self._relation_ids:
            try:
                db["work_item_relations"].delete_many({"relation_id": relation_id})
            except Exception:
                pass

        # Cleanup users (not test_admin)
        for user_id in self._user_ids:
            if user_id != "test_admin":
                try:
                    db["users"].delete_many({"user_id": user_id})
                except Exception:
                    pass

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


@pytest_asyncio.fixture
async def test_users(app_with_lifespan, admin_token) -> dict[str, dict[str, Any]]:
    """Create test users and return their tokens.

    Returns dict mapping role name to {"user_id": ..., "token": ...}
    """
    timestamp = int(time.time())
    base_password = "Test@123"

    users_to_create = [
        {"user_id": f"test_tpm_{timestamp}", "role": "TPM", "name": "Test TPM"},
        {"user_id": f"test_reviewer_{timestamp}", "role": "REVIEWER", "name": "Test Reviewer"},
        {"user_id": f"test_dev_{timestamp}", "role": "MANUAL_DEV", "name": "Test Developer"},
        {"user_id": f"test_qa_{timestamp}", "role": "QA", "name": "Test QA"},
        {"user_id": f"test_tester_{timestamp}", "role": "TESTER", "name": "Test Tester"},
        {"user_id": f"test_auto_dev_{timestamp}", "role": "AUTO_DEV", "name": "Test Auto Dev"},
        {"user_id": f"test_no_role_{timestamp}", "role": None, "name": "Test No Role"},
    ]

    created_users = {}

    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {admin_token}"})

        for user_spec in users_to_create:
            resp = await client.post(
                "/api/v1/auth/users",
                json={
                    "user_id": user_spec["user_id"],
                    "username": user_spec["name"],
                    "password": base_password,
                    "email": f"{user_spec['user_id']}@test.local",
                },
            )
            # Register user for cleanup (except test_admin)
            _test_data_registry.register_user(user_spec["user_id"])

            if resp.status_code == 201:
                if user_spec["role"]:
                    role_resp = await client.patch(
                        f"/api/v1/auth/users/{user_spec['user_id']}/roles",
                        json={"role_ids": [user_spec["role"]]},
                    )
                    if role_resp.status_code != 200:
                        print(f"Warning: Failed to assign role {user_spec['role']}: {role_resp.text}")

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
                print(f"Warning: Failed to login {user_spec['user_id']}: {login_resp.status_code} {login_resp.text}")

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