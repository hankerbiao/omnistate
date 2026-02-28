from fastapi.testclient import TestClient
import pytest

from app.modules.workflow.api import routes as workflow_routes
from app.shared.auth import jwt_auth
from tests.fakes.workflow import FakeWorkflowService


@pytest.fixture()
def app(app, monkeypatch):
    # 用 FakeWorkflowService 覆盖真实依赖，避免访问数据库
    app.dependency_overrides[workflow_routes.get_workflow_service] = lambda: FakeWorkflowService()

    # 覆盖鉴权依赖，避免测试时访问数据库
    async def _fake_current_user():
        return {"user_id": "test-user"}

    async def _fake_get_user_permissions(_user_id: str):
        return [
            "work_items:read",
            "work_items:write",
            "work_items:transition",
        ]

    app.dependency_overrides[jwt_auth.get_current_user] = _fake_current_user
    monkeypatch.setattr(jwt_auth, "get_user_permissions", _fake_get_user_permissions)
    return app


def test_health_envelope(client):
    # 验证健康检查接口的统一响应格式
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0
    assert payload["message"] == "ok"
    assert payload["data"]["status"] == "healthy"


def test_get_types_envelope(client):
    # 验证类型列表接口返回结构与字段
    resp = client.get("/api/v1/work-items/types")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0
    assert payload["message"] == "ok"
    assert isinstance(payload["data"], list)
    assert payload["data"][0]["code"] == "REQ"


def test_get_item_not_found_envelope(client):
    # 验证不存在事项时返回 404 的错误 envelope
    resp = client.get("/api/v1/work-items/507f1f77bcf86cd799439011")
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["code"] == 404
    assert payload["message"] == "HTTP Error 404"
    assert payload["data"]["error"] == "HTTP Error 404"
    assert "不存在" in payload["data"]["detail"]


def test_create_item_envelope(client):
    # 验证创建事项接口返回结构与默认字段
    resp = client.post(
        "/api/v1/work-items",
        json={
            "type_code": "REQ",
            "title": "T1",
            "content": "C1",
            "creator_id": "u1",
            "parent_item_id": None,
        },
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["code"] == 0
    assert payload["message"] == "ok"
    assert payload["data"]["type_code"] == "REQ"
    assert payload["data"]["current_state"] == "DRAFT"


def test_error_envelope_on_internal_exception(app):
    # 验证内部异常被统一包装为 500 错误响应
    client = TestClient(app, raise_server_exceptions=False)

    class FakeWorkflowServiceBoom(FakeWorkflowService):
        async def list_items(self, *args, **kwargs):
            raise RuntimeError("boom")

    app.dependency_overrides[workflow_routes.get_workflow_service] = lambda: FakeWorkflowServiceBoom()

    resp = client.get("/api/v1/work-items")
    assert resp.status_code == 500
    payload = resp.json()
    assert payload["code"] == 500
    assert payload["message"] == "InternalServerError"
    assert payload["data"]["error"] == "InternalServerError"


def test_batch_logs_invalid_item_ids_returns_400(client):
    resp = client.get("/api/v1/work-items/logs/batch?item_ids=invalid-id,507f1f77bcf86cd799439011")
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["code"] == 400
    assert payload["message"] == "HTTP Error 400"
    assert "invalid item_ids" in payload["data"]["detail"]
