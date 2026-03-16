from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.modules.execution.api import routes as execution_routes
from app.shared.auth import jwt_auth


class FakeExecutionService:
    async def register_agent(self, payload):
        now = datetime(2026, 3, 16, tzinfo=timezone.utc)
        return {
            "agent_id": payload["agent_id"],
            "hostname": payload["hostname"],
            "ip": payload["ip"],
            "port": payload.get("port"),
            "base_url": payload.get("base_url"),
            "region": payload["region"],
            "status": payload.get("status", "ONLINE"),
            "registered_at": now,
            "last_heartbeat_at": now,
            "heartbeat_ttl_seconds": payload.get("heartbeat_ttl_seconds", 90),
            "is_online": True,
            "created_at": now,
            "updated_at": now,
        }

    async def heartbeat_agent(self, agent_id, payload):
        now = datetime(2026, 3, 16, tzinfo=timezone.utc)
        return {
            "agent_id": agent_id,
            "hostname": "host-01",
            "ip": "10.0.0.10",
            "port": 9000,
            "base_url": "http://10.0.0.10:9000",
            "region": "cn-shanghai",
            "status": payload.get("status", "ONLINE"),
            "registered_at": now,
            "last_heartbeat_at": now,
            "heartbeat_ttl_seconds": 90,
            "is_online": True,
            "created_at": now,
            "updated_at": now,
        }

    async def list_agents(self, region=None, status=None, online_only=False):
        now = datetime(2026, 3, 16, tzinfo=timezone.utc)
        return [{
            "agent_id": "agent-01",
            "hostname": "host-01",
            "ip": "10.0.0.10",
            "port": 9000,
            "base_url": "http://10.0.0.10:9000",
            "region": region or "cn-shanghai",
            "status": status or "ONLINE",
            "registered_at": now,
            "last_heartbeat_at": now,
            "heartbeat_ttl_seconds": 90,
            "is_online": True,
            "created_at": now,
            "updated_at": now,
        }]

    async def get_agent(self, agent_id):
        rows = await self.list_agents()
        row = rows[0]
        row["agent_id"] = agent_id
        return row


@pytest.fixture()
def app(app, monkeypatch):
    app.dependency_overrides[execution_routes.get_execution_service] = lambda: FakeExecutionService()

    async def _fake_current_user():
        return {"user_id": "test-user"}

    async def _fake_get_user_permissions(_user_id: str):
        return [
            "execution_agents:read",
            "execution_tasks:read",
            "execution_tasks:write",
        ]

    app.dependency_overrides[jwt_auth.get_current_user] = _fake_current_user
    monkeypatch.setattr(jwt_auth, "get_user_permissions", _fake_get_user_permissions)
    return app


def test_register_agent_envelope(client):
    response = client.post(
        "/api/v1/execution/agents/register",
        json={
            "agent_id": "agent-01",
            "hostname": "host-01",
            "ip": "10.0.0.10",
            "region": "cn-shanghai",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["agent_id"] == "agent-01"
    assert payload["data"]["hostname"] == "host-01"
    assert payload["data"]["status"] == "ONLINE"


def test_heartbeat_agent_envelope(client):
    response = client.post(
        "/api/v1/execution/agents/agent-01/heartbeat",
        json={
            "status": "ONLINE",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["agent_id"] == "agent-01"
    assert payload["data"]["status"] == "ONLINE"


def test_list_agents_envelope(app):
    client = TestClient(app)
    response = client.get("/api/v1/execution/agents?online_only=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert len(payload["data"]) == 1
    assert payload["data"][0]["hostname"] == "host-01"
    assert payload["data"][0]["is_online"] is True


def test_get_agent_envelope(client):
    response = client.get("/api/v1/execution/agents/agent-99")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["agent_id"] == "agent-99"
