"""Lightweight runtime metrics endpoints."""
from __future__ import annotations

from app.shared.api.schemas.base import APIResponse
from app.shared.observability.http_metrics import get_http_metrics_snapshot

from fastapi import APIRouter

router = APIRouter()


@router.get("/metrics", summary="HTTP 请求性能指标")
def http_metrics():
    """Return in-process HTTP latency metrics for P0 performance triage."""
    return APIResponse(data=get_http_metrics_snapshot())
