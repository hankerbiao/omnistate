"""UTC datetime utilities."""

from __future__ import annotations

from datetime import datetime, timezone


def ensure_utc_datetime(value: datetime | str) -> datetime:
    """将 naive/aware datetime 或 ISO 时间字符串统一规范为 UTC aware datetime。"""
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        value = datetime.fromisoformat(normalized)
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
