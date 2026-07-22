"""In-process HTTP latency metrics for fast P0 diagnostics.

This module intentionally avoids external dependencies. It keeps a bounded sample
window per route key so operators can quickly see slow endpoints from health
routes or structured logs.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import time
from typing import Deque


@dataclass(slots=True)
class RouteMetrics:
    """Aggregated metrics for one method/path/status-class bucket."""

    count: int = 0
    error_count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    last_status_code: int = 0
    last_seen_epoch: float = 0.0
    samples: Deque[float] = field(default_factory=lambda: deque(maxlen=512))


class HttpMetricsRegistry:
    """Small thread-safe registry for request latency samples."""

    def __init__(self, *, max_routes: int = 512, sample_size: int = 512) -> None:
        self._max_routes = max_routes
        self._sample_size = sample_size
        self._lock = Lock()
        self._routes: dict[tuple[str, str, str], RouteMetrics] = {}

    def record(self, *, method: str, path: str, status_code: int, elapsed_ms: float) -> None:
        """Record one completed request."""
        status_class = f"{int(status_code / 100)}xx" if status_code else "unknown"
        key = (method.upper(), path, status_class)
        now = time()
        with self._lock:
            metrics = self._routes.get(key)
            if metrics is None:
                if len(self._routes) >= self._max_routes:
                    self._drop_oldest_route()
                metrics = RouteMetrics(samples=deque(maxlen=self._sample_size))
                self._routes[key] = metrics

            metrics.count += 1
            if status_code >= 500:
                metrics.error_count += 1
            metrics.total_ms += elapsed_ms
            metrics.max_ms = max(metrics.max_ms, elapsed_ms)
            metrics.last_status_code = status_code
            metrics.last_seen_epoch = now
            metrics.samples.append(elapsed_ms)

    def snapshot(self) -> dict:
        """Return a JSON-serializable point-in-time metrics snapshot."""
        with self._lock:
            routes = [
                self._serialize_route(method, path, status_class, metrics)
                for (method, path, status_class), metrics in self._routes.items()
            ]

        routes.sort(key=lambda item: (item["p95_ms"], item["max_ms"]), reverse=True)
        total_count = sum(item["count"] for item in routes)
        total_errors = sum(item["error_count"] for item in routes)
        return {
            "summary": {
                "route_buckets": len(routes),
                "request_count": total_count,
                "error_count": total_errors,
                "error_rate": round(total_errors / total_count, 6) if total_count else 0,
            },
            "routes": routes,
        }

    def reset(self) -> None:
        """Clear all in-memory metrics."""
        with self._lock:
            self._routes.clear()

    def _drop_oldest_route(self) -> None:
        if not self._routes:
            return
        oldest_key = min(self._routes.items(), key=lambda item: item[1].last_seen_epoch)[0]
        self._routes.pop(oldest_key, None)

    @staticmethod
    def _serialize_route(method: str, path: str, status_class: str, metrics: RouteMetrics) -> dict:
        samples = sorted(metrics.samples)
        return {
            "method": method,
            "path": path,
            "status_class": status_class,
            "count": metrics.count,
            "error_count": metrics.error_count,
            "avg_ms": round(metrics.total_ms / metrics.count, 2) if metrics.count else 0,
            "p50_ms": _percentile(samples, 50),
            "p95_ms": _percentile(samples, 95),
            "p99_ms": _percentile(samples, 99),
            "max_ms": round(metrics.max_ms, 2),
            "last_status_code": metrics.last_status_code,
            "last_seen_epoch": round(metrics.last_seen_epoch, 3),
        }


def _percentile(sorted_samples: list[float], percentile: int) -> float:
    """Nearest-rank percentile for a small bounded sample set."""
    if not sorted_samples:
        return 0
    index = max(0, min(len(sorted_samples) - 1, round((percentile / 100) * (len(sorted_samples) - 1))))
    return round(sorted_samples[index], 2)


http_metrics = HttpMetricsRegistry()


def get_http_metrics_snapshot() -> dict:
    """Expose metrics without leaking the mutable registry."""
    return http_metrics.snapshot()


def reset_http_metrics() -> None:
    """Reset metrics, primarily for tests and local diagnostics."""
    http_metrics.reset()
