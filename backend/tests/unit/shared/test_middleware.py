"""请求中间件单元测试。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.api.errors.handlers import setup_exception_handlers
from app.shared.context import reset_context
from app.shared.middleware.request_logging import RequestLoggingMiddleware


def test_request_logging_middleware_injects_request_id_and_calls_reset(monkeypatch):
    reset_calls: list[bool] = []

    def tracking_reset():
        reset_calls.append(True)
        reset_context()

    monkeypatch.setattr("app.shared.middleware.request_logging.reset_context", tracking_reset)

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ok")
    async def ok():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ok", headers={"X-Request-ID": "req_ok_001"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req_ok_001"
    assert reset_calls == [True]


def test_request_logging_middleware_calls_reset_when_call_next_raises(monkeypatch):
    reset_calls: list[bool] = []

    def tracking_reset():
        reset_calls.append(True)
        reset_context()

    monkeypatch.setattr("app.shared.middleware.request_logging.reset_context", tracking_reset)

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    setup_exception_handlers(app)

    @app.get("/fail")
    async def fail():
        raise RuntimeError("middleware failure")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/fail")

    assert response.status_code == 500
    assert reset_calls == [True]
