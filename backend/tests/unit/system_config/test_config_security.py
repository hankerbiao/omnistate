"""系统配置来源边界测试。"""
from __future__ import annotations

import pytest

import app.modules.system_config.service.config_service as service_mod
from app.modules.system_config.service.config_service import ConfigService


def test_runtime_allowlist_excludes_bootstrap_keys() -> None:
    assert ConfigService._is_runtime_config_key("ai.model") is True
    assert ConfigService._is_runtime_config_key("redis.password") is False
    assert ConfigService._is_runtime_config_key("kafka.bootstrap_servers") is False
    assert ConfigService._is_runtime_config_key("execution.default_repo_url") is False


@pytest.mark.asyncio
async def test_set_config_rejects_bootstrap_key_without_db_write(monkeypatch):
    touched_db = False

    class _FakeConfigDoc:
        config_key: str = "config_key"

        @staticmethod
        async def find_one(_query):
            nonlocal touched_db
            touched_db = True
            return None

    monkeypatch.setattr(service_mod, "SystemConfigDoc", _FakeConfigDoc)

    with pytest.raises(ValueError, match="不属于运行时配置"):
        await ConfigService.set_config("redis.password", "secret")

    assert touched_db is False


@pytest.mark.asyncio
async def test_get_config_ignores_bootstrap_keys_without_db_read(monkeypatch):
    touched_db = False

    class _FakeConfigDoc:
        config_key: str = "config_key"

        @staticmethod
        async def find_one(_query):
            nonlocal touched_db
            touched_db = True
            return None

    monkeypatch.setattr(service_mod, "SystemConfigDoc", _FakeConfigDoc)

    value = await ConfigService.get_config("kafka.bootstrap_servers", default=["yaml-only"])

    assert value == ["yaml-only"]
    assert touched_db is False


@pytest.mark.asyncio
async def test_init_defaults_only_inserts_runtime_configs(monkeypatch):
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
            {"config_key": "ai.model", "config_value": "qwen", "config_type": "string", "category": "ai"},
            {"config_key": "ai.timeout", "config_value": "60", "config_type": "integer", "category": "ai"},
        ],
    )

    await ConfigService.init_default_configs()

    assert [item["config_key"] for item in inserted] == ["ai.model", "ai.timeout"]
