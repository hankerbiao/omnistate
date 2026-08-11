from __future__ import annotations

from pathlib import Path

import pytest

from app.shared.config import settings as settings_module


def _write_config(path: Path, service_name: str, db_name: str, debug: bool = False) -> None:
    path.write_text(
        "\n".join(
            [
                "app:",
                f"  debug: {str(debug).lower()}",
                f"  service_name: {service_name}",
                "mongodb:",
                f"  db_name: {db_name}",
            ]
        ),
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    settings_module.clear_runtime_settings()
    settings_module.get_bootstrap_settings.cache_clear()
    settings_module.get_settings.cache_clear()
    yield
    settings_module.clear_runtime_settings()
    settings_module.get_bootstrap_settings.cache_clear()
    settings_module.get_settings.cache_clear()


def test_production_ignores_dev_overlay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = tmp_path / "config.yaml"
    _write_config(base, "backend", "production_db")
    _write_config(tmp_path / "config_dev.yaml", "backend-dev", "development_db", debug=True)
    monkeypatch.setenv("CONFIG_PATH", str(base))
    monkeypatch.setenv("DML_ENV", "production")

    loaded = settings_module.get_bootstrap_settings()

    assert loaded.app.service_name == "backend"
    assert loaded.app.debug is False
    assert loaded.mongodb.db_name == "production_db"


def test_dev_environment_loads_dev_overlay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = tmp_path / "config.yaml"
    _write_config(base, "backend", "production_db")
    _write_config(tmp_path / "config_dev.yaml", "backend-dev", "development_db", debug=True)
    monkeypatch.setenv("CONFIG_PATH", str(base))
    monkeypatch.setenv("DML_ENV", "dev")

    loaded = settings_module.get_bootstrap_settings()

    assert loaded.app.service_name == "backend-dev"
    assert loaded.app.debug is True
    assert loaded.mongodb.db_name == "development_db"


def test_invalid_environment_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = tmp_path / "config.yaml"
    _write_config(base, "backend", "production_db")
    monkeypatch.setenv("CONFIG_PATH", str(base))
    monkeypatch.setenv("DML_ENV", "../dev")

    with pytest.raises(ValueError, match="Invalid DML_ENV"):
        settings_module.get_bootstrap_settings()


def test_missing_environment_overlay_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "config.yaml"
    _write_config(base, "backend", "production_db")
    monkeypatch.setenv("CONFIG_PATH", str(base))
    monkeypatch.setenv("DML_ENV", "dev")

    with pytest.raises(FileNotFoundError, match="禁止回退到生产配置"):
        settings_module.get_bootstrap_settings()


def test_effective_settings_require_runtime_activation() -> None:
    with pytest.raises(RuntimeError, match="Runtime settings are not loaded"):
        settings_module.get_settings()
