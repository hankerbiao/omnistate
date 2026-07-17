"""系统配置默认值、加密存储与响应脱敏测试。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet

import app.modules.system_config.service.config_service as service_mod
from app.modules.system_config.service.config_crypto import (
    MASKED_CONFIG_VALUE,
    decrypt_config_value,
    encrypt_config_value,
)
from app.modules.system_config.service.config_service import ConfigService


def test_infrastructure_defaults_follow_static_settings(monkeypatch):
    settings = SimpleNamespace(
        redis=SimpleNamespace(
            sentinel_hosts=["redis-a:26379", "redis-b:26379"],
            master_name="prod-master",
            username="svc",
            password="",
            db=4,
            socket_timeout=5,
            max_connections=250,
            service_registry_key="prod:registry",
        ),
        kafka=SimpleNamespace(
            bootstrap_servers=["kafka-a:9092", "kafka-b:9092"],
            client_id="prod-api",
            result_topic="prod.results",
            dead_letter_topic="prod.dead",
            test_events_topic="prod.events",
            execution_result_group_id="prod-result-group",
            test_events_group_id="prod-event-group",
            producer_options=SimpleNamespace(model_dump=lambda: {"acks": "all"}),
            consumer_options=SimpleNamespace(model_dump=lambda: {"enable_auto_commit": False}),
        ),
    )
    monkeypatch.setattr(service_mod, "get_settings", lambda: settings)

    defaults = {
        item["config_key"]: item["config_value"]
        for item in ConfigService._infrastructure_default_configs()
    }

    assert defaults["redis.sentinel_hosts"] == '["redis-a:26379","redis-b:26379"]'
    assert defaults["kafka.bootstrap_servers"] == '["kafka-a:9092","kafka-b:9092"]'
    assert "localhost" not in defaults["redis.sentinel_hosts"]
    assert "localhost" not in defaults["kafka.bootstrap_servers"]


def test_sensitive_config_encrypts_and_decrypts(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DML_SYSTEM_CONFIG_ENCRYPTION_KEY", key)

    stored = encrypt_config_value("secret-value")

    assert stored != "secret-value"
    assert decrypt_config_value(stored) == "secret-value"


@pytest.mark.asyncio
async def test_masked_sensitive_update_keeps_existing_value(monkeypatch):
    doc = SimpleNamespace(is_encrypted=True, config_value="enc:v1:existing")

    # 用轻量替身替换 Beanie Document：仅让 `SystemConfigDoc.config_key == key`
    # 可求值，且 find_one 被 mock，避免未初始化集合时触发类属性访问异常。
    class _FakeConfigDoc:
        config_key: str = "config_key"
        find_one = staticmethod(AsyncMock(return_value=doc))

    monkeypatch.setattr(service_mod, "SystemConfigDoc", _FakeConfigDoc)

    result = await ConfigService.set_config("redis.password", MASKED_CONFIG_VALUE)

    assert result is doc
