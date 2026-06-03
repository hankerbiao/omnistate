"""全局异常处理器单元测试。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.api.errors.handlers import setup_exception_handlers
from app.shared.context import reset_context, set_operation_context, set_trace_context


def test_generic_exception_handler_returns_500_without_secondary_crash():
    """未捕获异常应正常返回 500，且不会二次崩溃。"""
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("test failure")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["message"] == "InternalServerError"
    reset_context()


def test_generic_exception_handler_uses_operation_context_user_id(monkeypatch):
    """异常日志应读取 operation context 的 user_id，而非 TraceContext。"""
    captured: dict[str, str] = {}

    def fake_exception(message, **kwargs):
        captured["message"] = message
        captured["user_id"] = kwargs.get("user_id", "")

    monkeypatch.setattr("app.shared.api.errors.handlers.log.exception", fake_exception)

    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        set_operation_context(user_id="operator_99")
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    assert captured["user_id"] == "operator_99"
    reset_context()


def test_generic_exception_handler_calls_reset_context(monkeypatch):
    """异常处理完成后应重置上下文，避免泄漏到后续请求。"""
    reset_calls: list[bool] = []

    def tracking_reset():
        reset_calls.append(True)

    monkeypatch.setattr("app.shared.api.errors.handlers.reset_context", tracking_reset)

    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    assert reset_calls == [True]
