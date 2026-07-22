"""请求中间件单元测试。"""

from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.api.errors.handlers import setup_exception_handlers
from app.shared.context import reset_context
from app.shared.middleware.request_logging import RequestLoggingMiddleware
from app.shared.observability.http_metrics import get_http_metrics_snapshot, reset_http_metrics


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


def test_request_logging_middleware_records_route_metrics():
    reset_http_metrics()

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/items/{item_id}")
    async def get_item(item_id: str):
        return {"item_id": item_id}

    client = TestClient(app)
    response = client.get("/items/abc")

    assert response.status_code == 200
    snapshot = get_http_metrics_snapshot()
    assert snapshot["summary"]["request_count"] == 1
    route = snapshot["routes"][0]
    assert route["method"] == "GET"
    assert route["path"] == "/items/{item_id}"
    assert route["status_class"] == "2xx"
    assert route["count"] == 1


def test_request_logging_middleware_logs_slow_request(monkeypatch):
    warning_calls: list[dict] = []

    def tracking_warning(message, **kwargs):
        warning_calls.append({"message": message, **kwargs})

    monkeypatch.setattr("app.shared.middleware.request_logging.log.warning", tracking_warning)
    monkeypatch.setattr(
        "app.shared.middleware.request_logging.RequestLoggingMiddleware._slow_request_threshold_ms",
        staticmethod(lambda: 1),
    )

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/slow/{item_id}")
    async def slow(item_id: str):
        time.sleep(0.01)
        return {"item_id": item_id}

    client = TestClient(app)
    response = client.get("/slow/abc?token=secret-token")

    assert response.status_code == 200
    assert len(warning_calls) == 1
    warning = warning_calls[0]
    assert warning["event"] == "http_slow_request"
    assert warning["http_path"] == "/slow/{item_id}"
    assert warning["http_raw_path"] == "/slow/abc"
    assert warning["slow_threshold_ms"] == 1
    assert "secret-token" not in warning["query"]


def test_request_logging_middleware_keeps_health_paths_silent(monkeypatch):
    warning_calls: list[dict] = []

    def tracking_warning(message, **kwargs):
        warning_calls.append({"message": message, **kwargs})

    monkeypatch.setattr("app.shared.middleware.request_logging.log.warning", tracking_warning)
    monkeypatch.setattr(
        "app.shared.middleware.request_logging.RequestLoggingMiddleware._slow_request_threshold_ms",
        staticmethod(lambda: 0),
    )

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/health/ready")
    async def ready():
        return {"status": "ready"}

    client = TestClient(app)
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert warning_calls == []
