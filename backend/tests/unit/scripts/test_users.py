from __future__ import annotations

from dataclasses import dataclass

import pytest

from scripts.common import users


class FakeField:
    def __eq__(self, other: object) -> tuple[str, object]:
        return ("user_id", other)


class FakeUserDoc:
    user_id = FakeField()
    existing = None
    inserted: list["FakeUserDoc"] = []

    def __init__(self, **values: object) -> None:
        for key, value in values.items():
            setattr(self, key, value)

    @classmethod
    async def find_one(cls, expression: object):
        return cls.existing

    async def insert(self) -> None:
        self.inserted.append(self)


@dataclass
class ExistingUser:
    username: str = "old"
    saved: bool = False

    async def save(self) -> None:
        self.saved = True


@pytest.fixture(autouse=True)
def fake_user_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeUserDoc.existing = None
    FakeUserDoc.inserted = []

    async def valid_roles(role_ids: list[str]) -> None:
        return None

    monkeypatch.setattr(users, "UserDoc", FakeUserDoc)
    monkeypatch.setattr(users, "validate_role_ids", valid_roles)
    monkeypatch.setattr(users, "hash_password", lambda password: ("salt", f"hash:{password}"))


async def test_write_user_creates_with_hashed_password() -> None:
    result = await users.write_user(
        user_id="admin",
        username="管理员",
        password="secret",
        role_ids=["ADMIN", "ADMIN"],
    )

    assert result == "created"
    assert FakeUserDoc.inserted[0].password_hash == "hash:secret"
    assert FakeUserDoc.inserted[0].role_ids == ["ADMIN"]


async def test_write_user_skips_without_rehashing(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeUserDoc.existing = ExistingUser()
    monkeypatch.setattr(
        users,
        "hash_password",
        lambda password: pytest.fail("skipped users must not be rehashed"),
    )

    result = await users.write_user(
        user_id="admin",
        username="管理员",
        password="secret",
        role_ids=["ADMIN"],
        existing_policy="skip",
    )

    assert result == "skipped"


async def test_write_user_updates_existing_user() -> None:
    existing = ExistingUser()
    FakeUserDoc.existing = existing

    result = await users.write_user(
        user_id="admin",
        username="系统管理员",
        password="new-secret",
        role_ids=["ADMIN"],
        existing_policy="update",
    )

    assert result == "updated"
    assert existing.saved is True
    assert existing.password_hash == "hash:new-secret"
