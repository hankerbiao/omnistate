"""轻量内存仓库。

生产环境可替换为数据库/Redis 实现；当前实现让开放平台后端可独立本地联调。
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Iterable, Protocol, runtime_checkable

from ..domain.models import (
    ApiKey,
    CallLog,
    ConsoleUser,
    CreatedApiKey,
    LogStatus,
    OverviewStats,
    UserQuota,
    WebhookRecord,
)
from ..domain.enums import utc_now_iso
from .database import hash_password, verify_password
from .seed_data import build_seed_keys, build_seed_users, mask_plaintext_key, resolve_upstream_user_id


@runtime_checkable
class Repository(Protocol):
    """网关数据访问契约。

    当前由内存实现 :class:`GatewayRepository` 满足；接入数据库 / Redis 时只需提供
    另一个满足该协议的对象，调用方（路由、管线）无需改动。
    """

    def list_keys(self, *, owner_user_id: str | None = None) -> list[ApiKey]: ...
    def list_users(self) -> list[ConsoleUser]: ...
    def get_user(self, user_id: str) -> ConsoleUser | None: ...
    def find_user_by_username(self, username: str) -> ConsoleUser | None: ...
    def verify_user_password(self, username: str, password: str) -> ConsoleUser | None: ...
    def create_user(
        self,
        *,
        username: str,
        password: str,
        name: str,
        email: str,
        role: str,
        team: str,
        allowed_capability_ids: list[str],
        quota: UserQuota,
        must_change_password: bool = False,
    ) -> ConsoleUser: ...
    def change_user_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> ConsoleUser | None: ...
    def update_user_permissions(self, user_id: str, capability_ids: list[str]) -> ConsoleUser | None: ...
    def update_user_quota(self, user_id: str, quota: UserQuota) -> ConsoleUser | None: ...
    def get_key(self, key_id: str) -> ApiKey | None: ...
    def find_key_by_plaintext(self, token: str) -> ApiKey | None: ...
    def create_key(
        self,
        *,
        name: str,
        env: str,
        scopes: Iterable[str],
        owner_user_id: str,
    ) -> CreatedApiKey: ...
    def revoke_key(self, key_id: str, *, owner_user_id: str | None = None) -> bool: ...
    def delete_key(self, key_id: str, *, owner_user_id: str | None = None) -> bool: ...
    def mark_key_used(self, key_id: str) -> None: ...
    def create_webhook(
        self,
        *,
        owner_user_id: str,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> WebhookRecord: ...
    def add_log(self, log: CallLog) -> None: ...
    def list_logs(self, *, limit: int = 200, owner_user_id: str | None = None) -> list[CallLog]: ...
    def overview(self, *, owner_user_id: str | None = None) -> OverviewStats: ...
    def describe(self) -> str: ...
    def close(self) -> None: ...


class GatewayRepository:
    """保存控制台与网关运行态数据（进程内内存实现）。"""

    def __init__(self, *, default_quota: UserQuota) -> None:
        self._default_quota = default_quota
        self._keys: dict[str, ApiKey] = {}
        self._logs: list[CallLog] = []
        self._webhooks: dict[str, WebhookRecord] = {}
        self._users: dict[str, ConsoleUser] = {}
        self._password_hashes: dict[str, str] = {}
        self._seed()

    def list_keys(self, *, owner_user_id: str | None = None) -> list[ApiKey]:
        keys: Iterable[ApiKey] = self._keys.values()
        if owner_user_id:
            keys = [key for key in keys if key.ownerUserId == owner_user_id]
        return sorted(keys, key=lambda item: item.createdAt, reverse=True)

    def list_users(self) -> list[ConsoleUser]:
        return list(self._users.values())

    def get_user(self, user_id: str) -> ConsoleUser | None:
        return self._users.get(user_id)

    def find_user_by_username(self, username: str) -> ConsoleUser | None:
        normalized = username.strip().lower()
        return next((user for user in self._users.values() if user.username == normalized), None)

    def verify_user_password(self, username: str, password: str) -> ConsoleUser | None:
        user = self.find_user_by_username(username)
        if not user or not verify_password(password, self._password_hashes.get(user.id)):
            return None
        return user

    def create_user(
        self,
        *,
        username: str,
        password: str,
        name: str,
        email: str,
        role: str,
        team: str,
        allowed_capability_ids: list[str],
        quota: UserQuota,
        must_change_password: bool = False,
    ) -> ConsoleUser:
        normalized = username.strip().lower()
        if self.find_user_by_username(normalized):
            raise ValueError("Username already exists")
        user = ConsoleUser(
            id=f"user_{secrets.token_hex(4)}",
            username=normalized,
            name=name.strip(),
            email=email.strip(),
            role=role,
            team=team.strip(),
            avatar=(name.strip()[:1] or normalized[:1]).upper(),
            allowedCapabilityIds=_dedupe(allowed_capability_ids),
            quota=quota,
            mustChangePassword=must_change_password,
        )
        self._users[user.id] = user
        self._password_hashes[user.id] = hash_password(password)
        return user

    def change_user_password(self, user_id: str, old_password: str, new_password: str) -> ConsoleUser | None:
        user = self._users.get(user_id)
        if not user or not verify_password(old_password, self._password_hashes.get(user.id)):
            return None
        self._password_hashes[user.id] = hash_password(new_password)
        updated = user.model_copy(update={"mustChangePassword": False})
        self._users[user.id] = updated
        return updated

    def update_user_permissions(self, user_id: str, capability_ids: list[str]) -> ConsoleUser | None:
        user = self._users.get(user_id)
        if not user:
            return None
        updated = user.model_copy(update={"allowedCapabilityIds": _dedupe(capability_ids)})
        self._users[user_id] = updated
        return updated

    def update_user_quota(self, user_id: str, quota: UserQuota) -> ConsoleUser | None:
        user = self._users.get(user_id)
        if not user:
            return None
        updated = user.model_copy(update={"quota": quota})
        self._users[user_id] = updated
        return updated

    def get_key(self, key_id: str) -> ApiKey | None:
        return self._keys.get(key_id)

    def find_key_by_plaintext(self, token: str) -> ApiKey | None:
        for key in self._keys.values():
            if key.plaintext == token:
                return key
        return None

    def create_key(self, *, name: str, env: str, scopes: Iterable[str], owner_user_id: str) -> CreatedApiKey:
        body = secrets.token_hex(16)
        prefix = "dml_live_" if env == "live" else "dml_test_"
        plaintext = f"{prefix}{body}"
        owner = self._users.get(owner_user_id)
        key = ApiKey(
            id=f"key_{secrets.token_hex(3)}",
            name=name.strip(),
            prefix=prefix,
            masked=mask_plaintext_key(prefix=prefix, plaintext=plaintext),
            status="active",
            scopes=_dedupe(scopes),
            createdAt=utc_now_iso(),
            lastUsedAt=None,
            callsToday=0,
            env=env,  # type: ignore[arg-type]
            plaintext=plaintext,
            ownerUserId=owner_user_id,
            upstreamUserId=resolve_upstream_user_id(owner_user_id, owner.username if owner else None),
            quota=self._default_quota,
        )
        self._keys[key.id] = key
        return CreatedApiKey(key=key, plaintext=plaintext)

    def revoke_key(self, key_id: str, *, owner_user_id: str | None = None) -> bool:
        key = self._keys.get(key_id)
        if not key or (owner_user_id and key.ownerUserId != owner_user_id):
            return False
        self._keys[key_id] = key.model_copy(update={"status": "revoked", "callsToday": 0})
        return True

    def delete_key(self, key_id: str, *, owner_user_id: str | None = None) -> bool:
        key = self._keys.get(key_id)
        if not key or (owner_user_id and key.ownerUserId != owner_user_id):
            return False
        self._keys.pop(key_id)
        return True

    def mark_key_used(self, key_id: str) -> None:
        key = self._keys.get(key_id)
        if not key:
            return
        self._keys[key_id] = key.model_copy(
            update={"lastUsedAt": utc_now_iso(), "callsToday": key.callsToday + 1}
        )

    def create_webhook(
        self,
        *,
        owner_user_id: str,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> WebhookRecord:
        record = WebhookRecord(
            id=f"wh_{secrets.token_hex(6)}",
            ownerUserId=owner_user_id,
            url=url,
            events=_dedupe(events),
            status="active",
            createdAt=utc_now_iso(),
        )
        self._webhooks[record.id] = record
        return record

    def add_log(self, log: CallLog) -> None:
        self._logs.insert(0, log)
        if len(self._logs) > 1000:
            self._logs = self._logs[:1000]

    def list_logs(self, *, limit: int = 200, owner_user_id: str | None = None) -> list[CallLog]:
        if not owner_user_id:
            return self._logs[:limit]
        owned_key_names = {key.name for key in self._keys.values() if key.ownerUserId == owner_user_id}
        return [log for log in self._logs if log.keyName in owned_key_names][:limit]

    def overview(self, *, owner_user_id: str | None = None) -> OverviewStats:
        today = datetime.now(timezone.utc).date()
        keys = self.list_keys(owner_user_id=owner_user_id)
        owned_key_names = {key.name for key in keys}
        logs = (
            self._logs
            if owner_user_id is None
            else [log for log in self._logs if log.keyName in owned_key_names]
        )
        today_logs = _logs_for_date(logs, today)
        total = len(today_logs)
        success = sum(1 for log in today_logs if log.status == LogStatus.success)
        success_rate = round((success / total) * 100, 1) if total else 100.0
        active_keys = sum(1 for key in keys if key.status == "active")
        quota_limit = sum(key.quota.monthlyLimit for key in keys if key.quota.monthlyLimit > 0)

        daily = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            day_logs = _logs_for_date(logs, day)
            daily.append(
                {
                    "date": day.strftime("%m-%d"),
                    "calls": len(day_logs),
                    "errors": sum(log.status != LogStatus.success for log in day_logs),
                }
            )

        by_endpoint: dict[str, int] = {}
        for log in logs:
            by_endpoint[log.endpoint] = by_endpoint.get(log.endpoint, 0) + 1
        top = sorted(by_endpoint.items(), key=lambda item: item[1], reverse=True)[:5]

        return OverviewStats(
            totalCallsToday=total,
            totalCallsTrend=0.0,
            successRate=success_rate,
            successRateTrend=0.0,
            activeKeys=active_keys,
            quotaUsed=sum(key.callsToday for key in keys),
            quotaLimit=quota_limit or 0,
            daily=daily,
            topCapabilities=[{"name": name, "calls": calls} for name, calls in top],
        )

    def close(self) -> None:
        """No-op for the in-memory implementation."""

    def describe(self) -> str:
        return "memory"

    def _seed(self) -> None:
        self._users = build_seed_users()
        self._password_hashes = {
            user.id: hash_password("admin123" if user.username == "admin" else "password123")
            for user in self._users.values()
        }
        self._keys = build_seed_keys(self._default_quota)


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _logs_for_date(logs: Iterable[CallLog], day) -> list[CallLog]:
    return [log for log in logs if _parse_date(log.timestamp) == day]


def _parse_date(value: str):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return datetime.now(timezone.utc).date()
