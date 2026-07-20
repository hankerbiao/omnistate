from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.modules.attachments.api import routes


class _Attachment:
    uploaded_by = "owner"


class _UploadFile:
    def __init__(self, chunks: list[bytes]):
        self._chunks = list(chunks)

    async def read(self, size: int = -1) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


async def test_owner_can_access_attachment(monkeypatch) -> None:
    async def fail_manage_check(current_user):
        raise AssertionError("owner should not require manage permission")

    monkeypatch.setattr(routes, "_can_manage_attachments", fail_manage_check)

    await routes._ensure_attachment_access(_Attachment(), {"user_id": "owner"})


async def test_other_user_requires_manage_permission(monkeypatch) -> None:
    async def cannot_manage(current_user):
        return False

    monkeypatch.setattr(routes, "_can_manage_attachments", cannot_manage)

    with pytest.raises(HTTPException) as exc_info:
        await routes._ensure_attachment_access(_Attachment(), {"user_id": "other"})

    assert exc_info.value.status_code == 403


async def test_manager_can_access_other_users_attachment(monkeypatch) -> None:
    async def can_manage(current_user):
        return True

    monkeypatch.setattr(routes, "_can_manage_attachments", can_manage)

    await routes._ensure_attachment_access(_Attachment(), {"user_id": "other"})


async def test_can_manage_attachments_accepts_admin_role(monkeypatch) -> None:
    async def fail_permissions(user_id):
        raise AssertionError("admin role should not query permissions")

    monkeypatch.setattr(routes, "get_user_permissions", fail_permissions)

    assert await routes._can_manage_attachments({"user_id": "u-1", "role_ids": ["ADMIN"]}) is True


async def test_can_manage_attachments_reads_explicit_permission(monkeypatch) -> None:
    async def get_permissions(user_id):
        return ["attachments:manage"]

    monkeypatch.setattr(routes, "get_user_permissions", get_permissions)

    assert await routes._can_manage_attachments({"user_id": "u-1", "role_ids": []}) is True


async def test_read_limited_file_rejects_oversized_upload() -> None:
    upload = _UploadFile([b"ab", b"cd"])

    with pytest.raises(HTTPException) as exc_info:
        await routes._read_limited_file(upload, max_size=3)

    assert exc_info.value.status_code == 413


async def test_read_limited_file_returns_bytes() -> None:
    upload = _UploadFile([b"ab", b"cd"])

    assert await routes._read_limited_file(upload, max_size=4) == b"abcd"
