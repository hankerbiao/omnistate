from __future__ import annotations

import pytest

from app.shared.config import RuntimeSettings
from scripts.migrations.migrate_runtime_config_to_db import _validate_runtime_source


def _complete_source() -> dict:
    return RuntimeSettings().model_dump()


def test_complete_runtime_source_is_accepted() -> None:
    runtime = _validate_runtime_source(_complete_source())

    assert runtime.jwt.algorithm == "HS256"


def test_missing_runtime_value_is_rejected() -> None:
    source = _complete_source()
    del source["jwt"]["secret_key"]

    with pytest.raises(RuntimeError, match="jwt.secret_key"):
        _validate_runtime_source(source)


def test_unknown_runtime_value_is_rejected() -> None:
    source = _complete_source()
    source["jwt"]["legacy_secret"] = "not-supported"

    with pytest.raises(RuntimeError, match="jwt.legacy_secret"):
        _validate_runtime_source(source)
