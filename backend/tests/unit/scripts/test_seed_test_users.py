from __future__ import annotations

import pytest

from scripts.dev.seed_test_users import ensure_development_environment


@pytest.mark.parametrize("environment", [None, "production", "prod", "staging"])
def test_seed_users_rejects_production_like_environments(
    monkeypatch: pytest.MonkeyPatch,
    environment: str | None,
) -> None:
    if environment is None:
        monkeypatch.delenv("DML_ENV", raising=False)
    with pytest.raises(RuntimeError, match="测试用户只能"):
        ensure_development_environment(environment)


@pytest.mark.parametrize("environment", ["dev", "development", "test", "testing", "local"])
def test_seed_users_accepts_explicit_development_environments(environment: str) -> None:
    assert ensure_development_environment(environment) in {"dev", "test", "local"}
