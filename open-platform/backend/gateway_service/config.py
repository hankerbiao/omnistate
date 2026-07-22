"""网关服务配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True, slots=True)
class GatewaySettings:
    """运行时配置，全部可通过环境变量覆盖。"""

    host: str = "127.0.0.1"
    port: int = 8820
    upstream_base_urls: tuple[str, ...] = ("http://127.0.0.1:8801",)
    request_timeout_seconds: float = 15.0
    connect_timeout_seconds: float = 3.0
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8808",
        "http://127.0.0.1:8808",
        "http://localhost:8809",
        "http://127.0.0.1:8809",
    )
    console_token: str = "dev-console-token"
    log_level: str = "INFO"
    log_file: str | None = None
    service_name: str = "dml-open-platform-gateway"
    trusted_proxy_headers: bool = True
    upstream_auth_secret: str = "dev-open-platform-gateway-secret-change-me"
    upstream_auth_algorithm: str = "HS256"
    upstream_auth_issuer: str = "dml-open-platform"
    upstream_auth_audience: str = "dml-backend"
    upstream_auth_ttl_seconds: int = 300
    extra_headers: dict[str, str] = field(default_factory=dict)
    db_path: str = field(
        default_factory=lambda: str(Path(__file__).resolve().parent / "gateway.db")
    )

    @classmethod
    def from_env(cls) -> "GatewaySettings":
        port = int(os.getenv("DML_GATEWAY_PORT", "8820"))
        if not 1 <= port <= 65535:
            raise ValueError("DML_GATEWAY_PORT must be between 1 and 65535")

        upstreams = _split_csv(os.getenv("DML_GATEWAY_UPSTREAMS", "http://127.0.0.1:8801"))
        if not upstreams:
            raise ValueError("DML_GATEWAY_UPSTREAMS must contain at least one upstream URL")

        timeout = float(os.getenv("DML_GATEWAY_REQUEST_TIMEOUT", "15"))
        connect_timeout = float(os.getenv("DML_GATEWAY_CONNECT_TIMEOUT", "3"))
        if min(timeout, connect_timeout) <= 0:
            raise ValueError("Gateway timeout values must be greater than 0")

        upstream_auth_secret = os.getenv(
            "DML_GATEWAY_UPSTREAM_AUTH_SECRET", "dev-open-platform-gateway-secret-change-me"
        ).strip()
        if not upstream_auth_secret:
            raise ValueError("DML_GATEWAY_UPSTREAM_AUTH_SECRET must not be empty")
        upstream_auth_ttl_seconds = int(os.getenv("DML_GATEWAY_UPSTREAM_AUTH_TTL_SECONDS", "300"))
        if upstream_auth_ttl_seconds <= 0:
            raise ValueError("DML_GATEWAY_UPSTREAM_AUTH_TTL_SECONDS must be greater than 0")

        return cls(
            host=os.getenv("DML_GATEWAY_HOST", "127.0.0.1").strip(),
            port=port,
            upstream_base_urls=tuple(url.rstrip("/") for url in upstreams),
            request_timeout_seconds=timeout,
            connect_timeout_seconds=connect_timeout,
            cors_origins=tuple(
                _split_csv(
                    os.getenv(
                        "DML_GATEWAY_CORS_ORIGINS",
                        (
                            "http://localhost:3000,http://127.0.0.1:3000,"
                            "http://localhost:8808,http://127.0.0.1:8808,"
                            "http://localhost:8809,http://127.0.0.1:8809"
                        ),
                    )
                )
            ),
            console_token=os.getenv("DML_GATEWAY_CONSOLE_TOKEN", "dev-console-token").strip(),
            log_level=os.getenv("DML_GATEWAY_LOG_LEVEL", "INFO").upper(),
            log_file=os.getenv("DML_GATEWAY_LOG_FILE", "").strip() or None,
            upstream_auth_secret=upstream_auth_secret,
            upstream_auth_algorithm=(
                os.getenv("DML_GATEWAY_UPSTREAM_AUTH_ALGORITHM", "HS256").strip() or "HS256"
            ),
            upstream_auth_issuer=os.getenv("DML_GATEWAY_UPSTREAM_AUTH_ISSUER", "dml-open-platform").strip(),
            upstream_auth_audience=os.getenv("DML_GATEWAY_UPSTREAM_AUTH_AUDIENCE", "dml-backend").strip(),
            upstream_auth_ttl_seconds=upstream_auth_ttl_seconds,
            db_path=os.getenv("DML_GATEWAY_DB_PATH", "").strip()
            or str(Path(__file__).resolve().parent / "gateway.db"),
        )
