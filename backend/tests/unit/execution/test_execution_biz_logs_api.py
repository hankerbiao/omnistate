"""Execution biz-logs API 单元测试。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.execution.api.routes import get_task_query_service, router
from app.shared.auth import get_current_user


class FakeQueryService:
    last_limit: int | None = None

    async def list_task_biz_logs(self, task_id: str, limit: int = 200) -> list[dict[str, Any]]:
        self.last_limit = limit
        return [{"task_id": task_id, "limit": limit}]


async def fake_admin_user():
    return {"user_id": "admin", "role_ids": ["ADMIN"]}


def _build_client() -> tuple[TestClient, FakeQueryService]:
    app = FastAPI()
    app.include_router(router)
    service = FakeQueryService()
    app.dependency_overrides[get_task_query_service] = lambda: service
    app.dependency_overrides[get_current_user] = fake_admin_user
    return TestClient(app), service


def test_list_task_biz_logs_accepts_valid_limit():
    client, service = _build_client()

    response = client.get("/execution/tasks/ET-2026-000001/biz-logs?limit=100")

    assert response.status_code == 200
    assert service.last_limit == 100


def test_list_task_biz_logs_rejects_limit_out_of_range():
    client, _ = _build_client()

    too_small = client.get("/execution/tasks/ET-2026-000001/biz-logs?limit=0")
    too_large = client.get("/execution/tasks/ET-2026-000001/biz-logs?limit=501")

    assert too_small.status_code == 422
    assert too_large.status_code == 422
