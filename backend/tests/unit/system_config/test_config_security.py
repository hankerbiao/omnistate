"""System configuration ownership and strict-source tests."""
from __future__ import annotations

import pytest

import app.modules.system_config.service.config_service as service_mod
from app.modules.system_config.constants.ai_analysis import (
    AI_PENDING_TASKS_SYSTEM_PROMPT_CONFIG_KEY,
    AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY,
)
from app.modules.system_config.service.config_service import ConfigService


def test_runtime_allowlist_includes_infrastructure_and_excludes_bootstrap() -> None:
    assert ConfigService._is_runtime_config_key("ai.model") is True
    assert ConfigService._is_runtime_config_key("redis.password") is True
    assert ConfigService._is_runtime_config_key("kafka.bootstrap_servers") is True
    assert ConfigService._is_runtime_config_key("execution.default_repo_url") is True
    assert ConfigService._is_runtime_config_key("app.port") is False
    assert ConfigService._is_runtime_config_key("mongodb.uri") is False
    assert ConfigService._is_runtime_config_key("logging.log_dir") is False


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
        await ConfigService.set_config("app.port", "9000")

    assert touched_db is False


@pytest.mark.asyncio
async def test_get_config_rejects_missing_database_value(monkeypatch):
    class _FakeConfigDoc:
        config_key: str = "config_key"

        @staticmethod
        async def find_one(_query):
            return None

    monkeypatch.setattr(service_mod, "SystemConfigDoc", _FakeConfigDoc)

    with pytest.raises(RuntimeError, match="运行配置缺失"):
        await ConfigService.get_config("kafka.bootstrap_servers")


def test_startup_default_seeding_is_removed() -> None:
    assert not hasattr(ConfigService, "init_default_configs")
    assert all(item["needs_restart"] for item in ConfigService.RUNTIME_CONFIGS)


def test_runtime_config_descriptions_are_chinese() -> None:
    descriptions = [item["description"] for item in ConfigService.RUNTIME_CONFIGS]

    assert len(descriptions) == 72
    assert all(any("\u4e00" <= char <= "\u9fff" for char in value) for value in descriptions)


def test_ai_analysis_prompts_are_database_configurations() -> None:
    prompt_configs = {item["config_key"]: item for item in ConfigService.AI_CONFIGS}

    for key in (
        AI_PENDING_TASKS_SYSTEM_PROMPT_CONFIG_KEY,
        AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY,
    ):
        assert ConfigService._is_runtime_config_key(key)
        assert prompt_configs[key]["config_type"] == "string"
        assert prompt_configs[key]["needs_restart"] is False
