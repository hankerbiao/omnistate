"""Shared user validation and persistence helpers for operational scripts."""
from __future__ import annotations

from typing import Literal

from app.modules.auth.repository.models import RoleDoc, UserDoc
from app.shared.auth import hash_password

ExistingUserPolicy = Literal["error", "skip", "update"]
UserWriteResult = Literal["created", "skipped", "updated"]


async def validate_role_ids(role_ids: list[str]) -> None:
    """Fail when any requested role has not been initialized."""
    unique_role_ids = set(role_ids)
    if not unique_role_ids:
        return

    existing_role_ids = {
        role.role_id
        async for role in RoleDoc.find({"role_id": {"$in": sorted(unique_role_ids)}})
    }
    missing = sorted(unique_role_ids - existing_role_ids)
    if missing:
        raise RuntimeError(
            f"角色不存在: {missing}。请先执行 scripts/init/sync_rbac.py 初始化角色。"
        )


async def write_user(
    *,
    user_id: str,
    username: str,
    password: str,
    role_ids: list[str],
    email: str | None = None,
    status: str = "ACTIVE",
    existing_policy: ExistingUserPolicy = "error",
) -> UserWriteResult:
    """Create a user or apply an explicit policy when it already exists."""
    if existing_policy not in {"error", "skip", "update"}:
        raise ValueError(f"不支持的 existing_policy: {existing_policy}")
    role_ids = list(dict.fromkeys(role_ids))
    await validate_role_ids(role_ids)
    existing = await UserDoc.find_one(UserDoc.user_id == user_id)
    if existing and existing_policy == "error":
        raise RuntimeError(f"用户已存在: {user_id}（如需覆盖请加 --upsert）")
    if existing and existing_policy == "skip":
        return "skipped"

    salt, password_hash = hash_password(password)
    if existing:
        existing.username = username
        existing.email = email
        existing.status = status
        existing.role_ids = role_ids
        existing.password_salt = salt
        existing.password_hash = password_hash
        await existing.save()
        return "updated"

    await UserDoc(
        user_id=user_id,
        username=username,
        email=email,
        status=status,
        role_ids=role_ids,
        password_salt=salt,
        password_hash=password_hash,
    ).insert()
    return "created"
