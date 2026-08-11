from __future__ import annotations

from unittest.mock import call, patch

from app.shared.config import BootstrapSettings, RuntimeSettings
from app.shared.core.startup_diagnostics import (
    log_bootstrap_diagnostics,
    log_runtime_diagnostics,
    mask_url_credentials,
)


def test_mask_url_credentials_removes_secrets_and_query() -> None:
    uri = "mongodb://admin:p%40ss@mongo-1:27017,mongo-2:27017/dml?authSource=admin&token=secret"

    masked = mask_url_credentials(uri)

    assert masked == "mongodb://***:***@mongo-1:27017,mongo-2:27017/dml"
    assert "admin" not in masked
    assert "secret" not in masked


def test_bootstrap_diagnostics_log_environment_and_mongodb(monkeypatch) -> None:
    monkeypatch.setenv("DML_ENV", "dev")
    settings = BootstrapSettings.model_validate(
        {
            "app": {
                "debug": True,
                "host": "127.0.0.1",
                "port": 8801,
                "service_name": "dml-backend",
            },
            "mongodb": {
                "uri": "mongodb://user:password@mongo.internal:27017",
                "db_name": "dml_dev",
            },
        }
    )

    with patch("app.shared.core.startup_diagnostics.log.debug") as debug:
        log_bootstrap_diagnostics(settings)

    assert debug.call_args_list == [
        call(
            "启动环境 | service={} | environment={} | mode={} | app_debug={} | listen={}:{}",
            "dml-backend",
            "dev",
            "development",
            True,
            "127.0.0.1",
            8801,
        ),
        call(
            "外部服务连接 | service=MongoDB | endpoint={} | database={}",
            "mongodb://***:***@mongo.internal:27017",
            "dml_dev",
        ),
    ]


def test_bootstrap_diagnostics_identifies_production(monkeypatch) -> None:
    monkeypatch.setenv("DML_ENV", "production")
    settings = BootstrapSettings.model_validate(
        {
            "app": {"service_name": "dml-backend"},
            "mongodb": {"db_name": "dml"},
        }
    )

    with patch("app.shared.core.startup_diagnostics.log.debug") as debug:
        log_bootstrap_diagnostics(settings)

    assert debug.call_args_list[0].args[1:4] == (
        "dml-backend",
        "production",
        "production",
    )


def test_runtime_diagnostics_log_external_service_endpoints() -> None:
    settings = RuntimeSettings.model_validate(
        {
            "rabbitmq": {
                "host": "rabbit.internal",
                "port": 5671,
                "username": "app",
                "password": "rabbit-secret",
                "virtual_host": "/dml",
                "ssl_enabled": True,
            },
            "kafka": {
                "bootstrap_servers": ["kafka-1:9092", "kafka-2:9092"],
                "client_id": "dml-backend",
            },
            "minio": {
                "endpoint": "minio.internal:9000",
                "access_key": "access-secret",
                "secret_key": "minio-secret",
                "bucket": "attachments",
                "secure": True,
            },
            "redis": {
                "sentinel_hosts": ["redis-1:26379", "redis-2:26379"],
                "master_name": "dml-master",
                "password": "redis-secret",
                "db": 2,
            },
            "notification": {
                "enabled": True,
                "guangquan": {
                    "api_url": "https://bot:notify-secret@notify.internal/send?token=secret"
                },
            },
        }
    )

    with patch("app.shared.core.startup_diagnostics.log.debug") as debug:
        log_runtime_diagnostics(settings)

    rendered_arguments = " ".join(
        str(argument)
        for logged_call in debug.call_args_list
        for argument in logged_call.args
    )
    assert "rabbit.internal" in rendered_arguments
    assert "kafka-1:9092,kafka-2:9092" in rendered_arguments
    assert "minio.internal:9000" in rendered_arguments
    assert "redis-1:26379,redis-2:26379" in rendered_arguments
    assert "https://***:***@notify.internal/send" in rendered_arguments
    assert "rabbit-secret" not in rendered_arguments
    assert "access-secret" not in rendered_arguments
    assert "minio-secret" not in rendered_arguments
    assert "redis-secret" not in rendered_arguments
    assert "notify-secret" not in rendered_arguments
