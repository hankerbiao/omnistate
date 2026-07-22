"""SQLite 实现的 Repository，替代内存 GatewayRepository 用于开发调试。"""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Iterable

from ..domain.models import (
    ApiKey,
    ApiKeyStatus,
    CallLog,
    ConsoleUser,
    CreatedApiKey,
    LogStatus,
    OverviewStats,
    UserQuota,
    WebhookRecord,
)
from ..domain.enums import utc_now_iso
from .database import (
    close_connection,
    ensure_schema,
    get_connection,
    hash_password,
    seed_data,
    verify_password,
)
from .repository import Repository
from .seed_data import mask_plaintext_key, resolve_upstream_user_id


class SQLiteRepository(Repository):
    """基于 SQLite 的仓库实现，数据持久化到文件。"""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        ensure_schema(db_path)
        seed_data(db_path)

    # ---- keys ----

    def list_keys(self, *, owner_user_id: str | None = None) -> list[ApiKey]:
        if owner_user_id:
            rows = self._query(
                "SELECT * FROM api_keys WHERE owner_user_id = ? ORDER BY created_at DESC",
                (owner_user_id,),
            )
        else:
            rows = self._query("SELECT * FROM api_keys ORDER BY created_at DESC")
        return [_row_to_key(r) for r in rows]

    def get_key(self, key_id: str) -> ApiKey | None:
        row = self._query_one("SELECT * FROM api_keys WHERE id = ?", (key_id,))
        return _row_to_key(row) if row else None

    def find_key_by_plaintext(self, token: str) -> ApiKey | None:
        row = self._query_one("SELECT * FROM api_keys WHERE plaintext = ?", (token,))
        return _row_to_key(row) if row else None

    def create_key(self, *, name: str, env: str, scopes: Iterable[str], owner_user_id: str) -> CreatedApiKey:
        body = secrets.token_hex(16)
        prefix = "dml_live_" if env == "live" else "dml_test_"
        plaintext = f"{prefix}{body}"
        key_id = f"key_{secrets.token_hex(3)}"
        scopes_list = list(dict.fromkeys(scopes))
        now = utc_now_iso()
        owner = self.get_user(owner_user_id)
        upstream_user_id = resolve_upstream_user_id(owner_user_id, owner.username if owner else None)

        self._execute(
            """INSERT INTO api_keys
               (id, name, prefix, masked, status, scopes, created_at, last_used_at,
                calls_today, env, plaintext, owner_user_id, upstream_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                key_id,
                name.strip(),
                prefix,
                mask_plaintext_key(prefix=prefix, plaintext=plaintext),
                "active",
                json.dumps(scopes_list, ensure_ascii=False),
                now,
                None,
                0,
                env,
                plaintext,
                owner_user_id,
                upstream_user_id,
            ),
        )
        key = self.get_key(key_id)
        return CreatedApiKey(key=key, plaintext=plaintext)  # type: ignore[arg-type]

    def revoke_key(self, key_id: str, *, owner_user_id: str | None = None) -> bool:
        if owner_user_id:
            cur = self._execute(
                "UPDATE api_keys SET status = ?, calls_today = 0 WHERE id = ? AND owner_user_id = ?",
                ("revoked", key_id, owner_user_id),
            )
        else:
            cur = self._execute(
                "UPDATE api_keys SET status = ?, calls_today = 0 WHERE id = ?",
                ("revoked", key_id),
            )
        return cur.rowcount > 0

    def delete_key(self, key_id: str, *, owner_user_id: str | None = None) -> bool:
        if owner_user_id:
            cur = self._execute(
                "DELETE FROM api_keys WHERE id = ? AND owner_user_id = ?",
                (key_id, owner_user_id),
            )
        else:
            cur = self._execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        return cur.rowcount > 0

    def mark_key_used(self, key_id: str) -> None:
        self._execute(
            "UPDATE api_keys SET last_used_at = ?, calls_today = calls_today + 1 WHERE id = ?",
            (utc_now_iso(), key_id),
        )

    def create_webhook(
        self,
        *,
        owner_user_id: str,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> WebhookRecord:
        webhook_id = f"wh_{secrets.token_hex(6)}"
        now = utc_now_iso()
        self._execute(
            """INSERT INTO webhooks
               (id, owner_user_id, url, events, secret, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                webhook_id,
                owner_user_id,
                url,
                json.dumps(list(dict.fromkeys(events)), ensure_ascii=False),
                secret,
                "active",
                now,
            ),
        )
        return WebhookRecord(
            id=webhook_id,
            ownerUserId=owner_user_id,
            url=url,
            events=list(dict.fromkeys(events)),
            status="active",
            createdAt=now,
        )

    # ---- users ----

    def list_users(self) -> list[ConsoleUser]:
        rows = self._query("SELECT * FROM users")
        return [_row_to_user(r) for r in rows]

    def get_user(self, user_id: str) -> ConsoleUser | None:
        return self._get_user(user_id)

    def find_user_by_username(self, username: str) -> ConsoleUser | None:
        row = self._query_one("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
        return _row_to_user(row) if row else None

    def verify_user_password(self, username: str, password: str) -> ConsoleUser | None:
        row = self._query_one("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
        if not row or not verify_password(password, row["password_hash"]):
            return None
        return _row_to_user(row)

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
        user_id = f"user_{secrets.token_hex(4)}"
        avatar = (name.strip()[:1] or normalized[:1]).upper()
        try:
            self._execute(
                """INSERT INTO users
                   (id, username, password_hash, name, email, role, team, avatar,
                    allowed_capability_ids, quota_enabled, quota_monthly_limit,
                    quota_rpm_limit, quota_concurrency, must_change_password)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    normalized,
                    hash_password(password),
                    name.strip(),
                    email.strip(),
                    role,
                    team.strip(),
                    avatar,
                    json.dumps(list(dict.fromkeys(allowed_capability_ids)), ensure_ascii=False),
                    int(quota.enabled),
                    quota.monthlyLimit,
                    quota.rpmLimit,
                    quota.concurrency,
                    int(must_change_password),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Username already exists") from exc
        created = self._get_user(user_id)
        return created  # type: ignore[return-value]

    def change_user_password(self, user_id: str, old_password: str, new_password: str) -> ConsoleUser | None:
        row = self._query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if not row or not verify_password(old_password, row["password_hash"]):
            return None
        self._execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
            (hash_password(new_password), user_id),
        )
        return self._get_user(user_id)

    def update_user_permissions(self, user_id: str, capability_ids: list[str]) -> ConsoleUser | None:
        ids = list(dict.fromkeys(capability_ids))
        cur = self._execute(
            "UPDATE users SET allowed_capability_ids = ? WHERE id = ?",
            (json.dumps(ids, ensure_ascii=False), user_id),
        )
        if cur.rowcount == 0:
            return None
        return self._get_user(user_id)

    def update_user_quota(self, user_id: str, quota: UserQuota) -> ConsoleUser | None:
        cur = self._execute(
            """UPDATE users
               SET quota_enabled = ?, quota_monthly_limit = ?, quota_rpm_limit = ?, quota_concurrency = ?
               WHERE id = ?""",
            (int(quota.enabled), quota.monthlyLimit, quota.rpmLimit, quota.concurrency, user_id),
        )
        if cur.rowcount == 0:
            return None
        return self._get_user(user_id)

    # ---- logs ----

    def add_log(self, log: CallLog) -> None:
        self._execute(
            """INSERT INTO call_logs
               (id, timestamp, request_id, app_name, key_name, method, endpoint,
                status_code, status, latency_ms, gateway_latency_ms, ip,
                request_body, response_body, error_code, diagnosis)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                log.id,
                log.timestamp,
                log.requestId,
                log.appName,
                log.keyName,
                log.method.value,
                log.endpoint,
                log.statusCode,
                log.status.value,
                log.latencyMs,
                log.gatewayLatencyMs,
                log.ip,
                log.requestBody or "",
                log.responseBody,
                log.errorCode,
                log.diagnosis,
            ),
        )

    def list_logs(self, *, limit: int = 200, owner_user_id: str | None = None) -> list[CallLog]:
        safe_limit = max(1, min(limit, 500))
        if owner_user_id:
            rows = self._query(
                """SELECT logs.* FROM call_logs logs
                   JOIN api_keys keys ON keys.name = logs.key_name
                   WHERE keys.owner_user_id = ?
                   ORDER BY logs.timestamp DESC LIMIT ?""",
                (owner_user_id, safe_limit),
            )
        else:
            rows = self._query(
                "SELECT * FROM call_logs ORDER BY timestamp DESC LIMIT ?",
                (safe_limit,),
            )
        return [_row_to_log(r) for r in rows]

    # ---- stats ----

    def overview(self, *, owner_user_id: str | None = None) -> OverviewStats:
        today = datetime.now(timezone.utc).date().isoformat()
        conn = get_connection(self._db_path)

        log_join = "JOIN api_keys keys ON keys.name = logs.key_name" if owner_user_id else ""
        owner_where = "AND keys.owner_user_id = ?" if owner_user_id else ""
        owner_params: tuple[Any, ...] = (owner_user_id,) if owner_user_id else ()

        row = conn.execute(
            f"""SELECT COUNT(*) AS total,
                       SUM(CASE WHEN logs.status = 'success' THEN 1 ELSE 0 END) AS success
                FROM call_logs logs {log_join}
                WHERE logs.timestamp >= ? {owner_where}""",
            (today, *owner_params),
        ).fetchone()
        total = row["total"] or 0
        success = row["success"] or 0
        success_rate = round((success / total) * 100, 1) if total else 100.0

        if owner_user_id:
            active_keys = conn.execute(
                "SELECT COUNT(*) AS cnt FROM api_keys WHERE status = 'active' AND owner_user_id = ?",
                (owner_user_id,),
            ).fetchone()["cnt"]
        else:
            active_keys = conn.execute(
                "SELECT COUNT(*) AS cnt FROM api_keys WHERE status = 'active'"
            ).fetchone()["cnt"]

        if owner_user_id:
            quota_row = conn.execute(
                """SELECT SUM(calls_today) AS used, SUM(quota_monthly_limit) AS qlimit
                   FROM api_keys WHERE status = 'active' AND owner_user_id = ?""",
                (owner_user_id,),
            ).fetchone()
        else:
            quota_row = conn.execute(
                """SELECT SUM(calls_today) AS used, SUM(quota_monthly_limit) AS qlimit
                   FROM api_keys WHERE status = 'active'"""
            ).fetchone()
        quota_used = quota_row["used"] or 0
        quota_limit = quota_row["qlimit"] or 0

        daily = []
        for offset in range(6, -1, -1):
            day = (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()
            next_day = (datetime.now(timezone.utc) - timedelta(days=offset - 1)).date().isoformat()
            day_row = conn.execute(
                f"""SELECT COUNT(*) AS calls,
                           SUM(CASE WHEN logs.status != 'success' THEN 1 ELSE 0 END) AS errors
                    FROM call_logs logs {log_join}
                    WHERE logs.timestamp >= ? AND logs.timestamp < ? {owner_where}""",
                (day, next_day, *owner_params),
            ).fetchone()
            daily.append({
                "date": day[-5:],
                "calls": day_row["calls"] or 0,
                "errors": day_row["errors"] or 0,
            })

        top_rows = conn.execute(
            f"""SELECT logs.endpoint, COUNT(*) AS cnt
                FROM call_logs logs {log_join}
                WHERE 1 = 1 {owner_where}
                GROUP BY logs.endpoint ORDER BY cnt DESC LIMIT 5""",
            owner_params,
        ).fetchall()
        top_capabilities = [{"name": r["endpoint"], "calls": r["cnt"]} for r in top_rows]

        return OverviewStats(
            totalCallsToday=total,
            totalCallsTrend=0.0,
            successRate=success_rate,
            successRateTrend=0.0,
            activeKeys=active_keys,
            quotaUsed=quota_used,
            quotaLimit=quota_limit,
            daily=daily,
            topCapabilities=top_capabilities,
        )

    # ---- helpers ----

    def _query(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return get_connection(self._db_path).execute(sql, params).fetchall()

    def _query_one(self, sql: str, params: tuple[Any, ...] = ()):
        return get_connection(self._db_path).execute(sql, params).fetchone()

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        conn = get_connection(self._db_path)
        cur = conn.execute(sql, params)
        conn.commit()
        return cur

    def _get_user(self, user_id: str) -> ConsoleUser | None:
        row = self._query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return _row_to_user(row) if row else None

    def close(self) -> None:
        close_connection()

    def describe(self) -> str:
        return f"sqlite://{self._db_path}"


# ---- Row → Model 转换 ----

def _row_to_key(row: sqlite3.Row) -> ApiKey:
    return ApiKey(
        id=row["id"],
        name=row["name"],
        prefix=row["prefix"],
        masked=row["masked"],
        status=ApiKeyStatus(row["status"]),
        scopes=json.loads(row["scopes"]),
        createdAt=row["created_at"],
        lastUsedAt=row["last_used_at"],
        callsToday=row["calls_today"],
        env=row["env"],  # type: ignore[arg-type]
        plaintext=row["plaintext"],
        ownerUserId=row["owner_user_id"],
        upstreamUserId=row["upstream_user_id"],
        quota=UserQuota(
            enabled=bool(row["quota_enabled"]),
            monthlyLimit=row["quota_monthly_limit"],
            rpmLimit=row["quota_rpm_limit"],
            concurrency=row["quota_concurrency"],
        ),
    )


def _row_to_user(row: sqlite3.Row) -> ConsoleUser:
    return ConsoleUser(
        id=row["id"],
        username=row["username"],
        name=row["name"],
        email=row["email"],
        role=row["role"],
        team=row["team"],
        avatar=row["avatar"],
        allowedCapabilityIds=json.loads(row["allowed_capability_ids"]),
        quota=UserQuota(
            enabled=bool(row["quota_enabled"]),
            monthlyLimit=row["quota_monthly_limit"],
            rpmLimit=row["quota_rpm_limit"],
            concurrency=row["quota_concurrency"],
        ),
        mustChangePassword=bool(row["must_change_password"]),
    )


def _row_to_log(row: sqlite3.Row) -> CallLog:
    return CallLog(
        id=row["id"],
        timestamp=row["timestamp"],
        requestId=row["request_id"],
        appName=row["app_name"],
        keyName=row["key_name"],
        method=row["method"],  # type: ignore[arg-type]
        endpoint=row["endpoint"],
        statusCode=row["status_code"],
        status=LogStatus(row["status"]),
        latencyMs=row["latency_ms"],
        gatewayLatencyMs=row["gateway_latency_ms"],
        ip=row["ip"] or "",
        requestBody=row["request_body"] or None,
        responseBody=row["response_body"] or "",
        errorCode=row["error_code"],
        diagnosis=row["diagnosis"],
    )
