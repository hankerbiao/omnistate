"""系统配置默认值与明文存储测试。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.modules.system_config.service.config_service as service_mod
from app.modules.system_config.service.config_service import ConfigService


def test_infrastructure_defaults_follow_static_settings(monkeypatch):
    settings = SimpleNamespace(
        redis=SimpleNamespace(
            sentinel_hosts=["redis-a:26379", "redis-b:26379"],
            master_name="prod-master",
            username="svc",
            password="plain-password",
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
    assert defaults["redis.password"] == "plain-password"
    assert defaults["kafka.bootstrap_servers"] == '["kafka-a:9092","kafka-b:9092"]'
    assert "localhost" not in defaults["redis.sentinel_hosts"]
    assert "localhost" not in defaults["kafka.bootstrap_servers"]


@pytest.mark.asyncio
async def test_set_config_stores_plain_text(monkeypatch):
    inserted: list[dict] = []

    class _FakeConfigDoc:
        config_key: str = "config_key"

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.id = None

        @staticmethod
        async def find_one(_query):
            return None

        async def insert(self):
            inserted.append(self.kwargs)
            return self

    monkeypatch.setattr(service_mod, "SystemConfigDoc", _FakeConfigDoc)

    async def fake_invalidate(_key=None):
        return None

    monkeypatch.setattr(service_mod.ConfigCache, "invalidate", staticmethod(fake_invalidate))
    monkeypatch.setattr(
        ConfigService,
        "_DEFAULTS_MAP",
        {"redis.password": {"config_type": "string", "category": "system", "needs_restart": True}},
    )

    await ConfigService.set_config("redis.password", "secret")

    assert inserted == [
        {
            "config_key": "redis.password",
            "config_value": "secret",
            "config_type": "string",
            "category": "system",
            "description": None,
            "needs_restart": True,
            "updated_by": None,
        }
    ]


@pytest.mark.asyncio
async def test_init_defaults_inserts_sensitive_values_as_plain_text(monkeypatch):
    inserted: list[dict] = []

    class _FakeConfigDoc:
        config_key: str = "config_key"

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @staticmethod
        async def find_one(_query):
            return None

        async def insert(self):
            inserted.append(self.kwargs)

    monkeypatch.setattr(service_mod, "SystemConfigDoc", _FakeConfigDoc)
    monkeypatch.setattr(
        ConfigService,
        "DEFAULT_CONFIGS",
        [
            {"config_key": "plain.key", "config_value": "plain", "config_type": "string", "category": "test"},
            {"config_key": "secret.key", "config_value": "secret", "config_type": "string", "category": "test"},
        ],
    )
    monkeypatch.setattr(ConfigService, "_infrastructure_default_configs", classmethod(lambda cls: []))

    await ConfigService.init_default_configs()

    assert [item["config_key"] for item in inserted] == ["plain.key", "secret.key"]
    assert inserted[1]["config_value"] == "secret"
