from __future__ import annotations

from argparse import Namespace

import pytest

from scripts.init.create_user import resolve_password


def _args(password: str | None = None, password_env: str | None = None) -> Namespace:
    return Namespace(password=password, password_env=password_env)


def test_resolve_password_uses_direct_argument() -> None:
    assert resolve_password(_args(password="direct-secret")) == "direct-secret"


def test_resolve_password_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DML_TEST_ADMIN_PASSWORD", "environment-secret")

    assert (
        resolve_password(_args(password_env="DML_TEST_ADMIN_PASSWORD"))
        == "environment-secret"
    )


def test_resolve_password_rejects_missing_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DML_TEST_ADMIN_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="密码环境变量未设置或为空"):
        resolve_password(_args(password_env="DML_TEST_ADMIN_PASSWORD"))
