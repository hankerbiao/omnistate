"""SQLite 数据库连接、Schema 创建与种子数据初始化。"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading

from ..domain.models import UserQuota
from .seed_data import build_seed_keys, build_seed_users

_local = threading.local()


def get_connection(db_path: str) -> sqlite3.Connection:
    """返回当前线程的 SQLite 连接（线程本地单例）。"""
    conn = getattr(_local, "conn", None)
    current_db_path = getattr(_local, "db_path", None)
    if conn is None or current_db_path != db_path or conn.execute("SELECT 1").fetchone() is None:
        if conn is not None:
            conn.close()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
        _local.db_path = db_path
    return conn


def close_connection() -> None:
    conn = getattr(_local, "conn", None)
    if conn:
        conn.close()
        _local.conn = None
        _local.db_path = None


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS api_keys (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    prefix        TEXT NOT NULL,
    masked        TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active',
    scopes        TEXT NOT NULL DEFAULT '[]',
    created_at    TEXT NOT NULL,
    last_used_at  TEXT,
    calls_today   INTEGER NOT NULL DEFAULT 0,
    env           TEXT NOT NULL,
    plaintext     TEXT,
    owner_user_id TEXT NOT NULL DEFAULT 'user_admin',
    upstream_user_id TEXT,
    quota_enabled           INTEGER NOT NULL DEFAULT 1,
    quota_monthly_limit     INTEGER NOT NULL DEFAULT 100000,
    quota_rpm_limit         INTEGER NOT NULL DEFAULT 120,
    quota_concurrency       INTEGER NOT NULL DEFAULT 10
);

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username      TEXT UNIQUE,
    password_hash TEXT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL,
    role          TEXT NOT NULL,
    team          TEXT NOT NULL,
    avatar        TEXT NOT NULL DEFAULT '',
    allowed_capability_ids TEXT NOT NULL DEFAULT '[]',
    quota_enabled           INTEGER NOT NULL DEFAULT 1,
    quota_monthly_limit     INTEGER NOT NULL DEFAULT 100000,
    quota_rpm_limit         INTEGER NOT NULL DEFAULT 120,
    quota_concurrency       INTEGER NOT NULL DEFAULT 10,
    must_change_password    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS call_logs (
    id                 TEXT PRIMARY KEY,
    timestamp          TEXT NOT NULL,
    request_id         TEXT NOT NULL,
    app_name           TEXT NOT NULL DEFAULT '',
    key_name           TEXT NOT NULL DEFAULT '',
    method             TEXT NOT NULL,
    endpoint           TEXT NOT NULL,
    status_code        INTEGER NOT NULL,
    status             TEXT NOT NULL,
    latency_ms         INTEGER NOT NULL DEFAULT 0,
    gateway_latency_ms INTEGER NOT NULL DEFAULT 0,
    ip                 TEXT DEFAULT '',
    request_body       TEXT DEFAULT '',
    response_body      TEXT DEFAULT '',
    error_code         TEXT,
    diagnosis          TEXT
);

CREATE TABLE IF NOT EXISTS webhooks (
    id            TEXT PRIMARY KEY,
    owner_user_id TEXT NOT NULL,
    url           TEXT NOT NULL,
    events        TEXT NOT NULL DEFAULT '[]',
    secret        TEXT,
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_call_logs_timestamp ON call_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_call_logs_status    ON call_logs(status);
CREATE INDEX IF NOT EXISTS idx_call_logs_endpoint  ON call_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_webhooks_owner      ON webhooks(owner_user_id);
"""


def ensure_schema(db_path: str) -> None:
    """创建表结构（幂等）。"""
    conn = get_connection(db_path)
    conn.executescript(_SCHEMA_SQL)
    _ensure_api_key_auth_columns(conn)
    _ensure_user_auth_columns(conn)
    conn.commit()


def _ensure_api_key_auth_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(api_keys)").fetchall()}
    if "upstream_user_id" not in columns:
        conn.execute("ALTER TABLE api_keys ADD COLUMN upstream_user_id TEXT")
    conn.execute(
        """UPDATE api_keys
           SET upstream_user_id = CASE owner_user_id
               WHEN 'user_admin' THEN 'admin'
               WHEN 'user_developer' THEN 'dev'
               WHEN 'user_zhaolei' THEN 'tester'
               ELSE upstream_user_id
           END
           WHERE owner_user_id IN ('user_admin', 'user_developer', 'user_zhaolei')
             AND (upstream_user_id IS NULL OR upstream_user_id = owner_user_id)"""
    )
    conn.execute(
        "UPDATE api_keys SET upstream_user_id = 'admin' WHERE id = 'key_01' AND upstream_user_id IS NULL"
    )
    conn.execute(
        """UPDATE api_keys SET upstream_user_id = 'dev'
           WHERE id IN ('key_02', 'key_03') AND upstream_user_id IS NULL"""
    )
    conn.execute(
        "UPDATE api_keys SET upstream_user_id = 'tester' WHERE id = 'key_04' AND upstream_user_id IS NULL"
    )


def _ensure_user_auth_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "username" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "password_hash" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "must_change_password" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    conn.execute(
        "UPDATE users SET username = 'admin' WHERE id = 'user_admin' AND (username IS NULL OR username = '')"
    )
    conn.execute(
        "UPDATE users SET username = id WHERE id != 'user_admin' AND (username IS NULL OR username = '')"
    )
    admin_hash = hash_password("admin123")
    conn.execute(
        """UPDATE users SET password_hash = ?
           WHERE id = 'user_admin' AND (password_hash IS NULL OR password_hash = '')""",
        (admin_hash,),
    )


def _is_seeded(db_path: str) -> bool:
    conn = get_connection(db_path)
    row = conn.execute("SELECT COUNT(*) AS cnt FROM api_keys").fetchone()
    return row["cnt"] > 0


def seed_data(db_path: str) -> None:
    """插入种子数据（幂等，已有数据则跳过）。"""
    if _is_seeded(db_path):
        return

    conn = get_connection(db_path)
    default_quota = UserQuota(enabled=True, monthlyLimit=100000, rpmLimit=120, concurrency=10)

    # 插入用户
    users = build_seed_users()
    for user in users.values():
        conn.execute(
            """INSERT INTO users
               (id, username, password_hash, name, email, role, team, avatar, allowed_capability_ids,
                quota_enabled, quota_monthly_limit, quota_rpm_limit, quota_concurrency, must_change_password)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user.id,
                user.username,
                hash_password("admin123" if user.username == "admin" else "password123"),
                user.name,
                user.email,
                user.role,
                user.team,
                user.avatar,
                json.dumps(user.allowedCapabilityIds, ensure_ascii=False),
                int(user.quota.enabled),
                user.quota.monthlyLimit,
                user.quota.rpmLimit,
                user.quota.concurrency,
                int(user.mustChangePassword),
            ),
        )

    # 插入 API Key
    keys = build_seed_keys(default_quota)
    for key in keys.values():
        conn.execute(
            """INSERT INTO api_keys
               (id, name, prefix, masked, status, scopes, created_at, last_used_at,
                calls_today, env, plaintext, owner_user_id, upstream_user_id,
                quota_enabled, quota_monthly_limit, quota_rpm_limit, quota_concurrency)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                key.id,
                key.name,
                key.prefix,
                key.masked,
                key.status.value,
                json.dumps(key.scopes, ensure_ascii=False),
                key.createdAt,
                key.lastUsedAt,
                key.callsToday,
                key.env,
                key.plaintext,
                key.ownerUserId,
                key.upstreamUserId,
                int(key.quota.enabled),
                key.quota.monthlyLimit,
                key.quota.rpmLimit,
                key.quota.concurrency,
            ),
        )

    conn.commit()

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "sha256":
        return False
    actual = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return secrets.compare_digest(actual, expected)
