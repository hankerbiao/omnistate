"""Seed data factory for the in-memory gateway repository."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from ..domain.models import ApiKey, ConsoleUser, UserQuota


CONSOLE_TO_UPSTREAM_USER_IDS = {
    "user_admin": "admin",
    "user_developer": "dev",
    "user_zhaolei": "tester",
}


def resolve_upstream_user_id(owner_user_id: str, username: str | None = None) -> str:
    """Map an Open Platform console user to the DML backend user id."""
    if owner_user_id in CONSOLE_TO_UPSTREAM_USER_IDS:
        return CONSOLE_TO_UPSTREAM_USER_IDS[owner_user_id]
    normalized_username = (username or "").strip()
    return normalized_username or owner_user_id


def build_seed_users() -> dict[str, ConsoleUser]:
    """Return demo console users keyed by user id."""
    return {
        "user_admin": ConsoleUser(
            id="user_admin",
            username="admin",
            name="李彪",
            email="libiao@dml.local",
            role="admin",
            team="DML 平台管理员",
            avatar="李",
            allowedCapabilityIds=[
                "cap_list_tasks",
                "cap_task_status",
                "cap_task_timeline",
                "cap_dispatch_task",
                "cap_rerun_task",
                "cap_task_biz_logs",
                "cap_list_specs",
                "cap_get_case",
                "cap_case_change_logs",
                "cap_list_requirements",
                "cap_get_requirement",
                "cap_list_projects",
                "cap_get_project",
                "cap_project_stats",
                "cap_project_blockers",
                "cap_project_activities",
                "cap_report",
                "cap_webhook",
            ],
            quota=UserQuota(enabled=True, monthlyLimit=500000, rpmLimit=600, concurrency=60),
        ),
        "user_developer": ConsoleUser(
            id="user_developer",
            username="developer",
            name="王小明",
            email="xiaoming@dml.local",
            role="developer",
            team="质量平台组",
            avatar="王",
            allowedCapabilityIds=["cap_list_tasks", "cap_task_status", "cap_report"],
            quota=UserQuota(enabled=True, monthlyLimit=100000, rpmLimit=120, concurrency=10),
        ),
        "user_zhaolei": ConsoleUser(
            id="user_zhaolei",
            username="zhaolei",
            name="赵雷",
            email="zhaolei@dml.local",
            role="developer",
            team="算法平台组",
            avatar="赵",
            allowedCapabilityIds=["cap_list_tasks", "cap_task_status", "cap_report", "cap_list_specs"],
            quota=UserQuota(enabled=False, monthlyLimit=0, rpmLimit=0, concurrency=0),
        ),
    }


def build_seed_keys(default_quota: UserQuota) -> dict[str, ApiKey]:
    """Return demo API keys keyed by key id."""
    seed_keys = [
        (
            "key_01",
            "CI 流水线集成",
            "live",
            "dml_live_demo_ci",
            ["execution_tasks:read"],
            "user_admin",
            "admin",
        ),
        (
            "key_02",
            "数据看板同步",
            "live",
            "dml_live_demo_dashboard",
            ["execution_tasks:read", "test_cases:read", "requirements:read"],
            "user_developer",
            "dev",
        ),
        (
            "key_03",
            "本地联调（测试）",
            "test",
            "dml_test_demo_local",
            ["execution_tasks:read"],
            "user_developer",
            "dev",
        ),
        (
            "key_04",
            "旧版报表脚本",
            "live",
            "dml_live_demo_revoked",
            ["execution_tasks:read"],
            "user_zhaolei",
            "tester",
        ),
    ]
    return {
        key_id: build_seed_key(
            key_id=key_id,
            name=name,
            env=env,
            plaintext=plaintext,
            scopes=scopes,
            default_quota=default_quota,
            owner_user_id=owner_user_id,
            upstream_user_id=upstream_user_id,
        )
        for key_id, name, env, plaintext, scopes, owner_user_id, upstream_user_id in seed_keys
    }


def build_seed_key(
    *,
    key_id: str,
    name: str,
    env: str,
    plaintext: str,
    scopes: Iterable[str],
    default_quota: UserQuota,
    owner_user_id: str,
    upstream_user_id: str | None = None,
) -> ApiKey:
    prefix = "dml_live_" if env == "live" else "dml_test_"
    status = "revoked" if key_id == "key_04" else "active"
    created_at = datetime.now(timezone.utc) - timedelta(days=30)
    last_used_at = datetime.now(timezone.utc) - timedelta(minutes=8)
    return ApiKey(
        id=key_id,
        name=name,
        prefix=prefix,
        masked=mask_plaintext_key(prefix=prefix, plaintext=plaintext),
        status=status,  # type: ignore[arg-type]
        scopes=list(scopes),
        createdAt=created_at.isoformat(),
        lastUsedAt=last_used_at.isoformat() if status == "active" else None,
        callsToday=0 if status == "revoked" else 12,
        env=env,  # type: ignore[arg-type]
        plaintext=plaintext,
        ownerUserId=owner_user_id,
        upstreamUserId=upstream_user_id,
        quota=default_quota,
    )


def mask_plaintext_key(*, prefix: str, plaintext: str) -> str:
    body = plaintext.removeprefix(prefix)
    return f"{prefix}{body[:4]}{'*' * 10}{plaintext[-4:]}"
