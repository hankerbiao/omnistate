from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.attachments.repository.models import AttachmentDoc
from app.modules.attachments.service.attachment_service import AttachmentService
from app.shared.domain.exceptions import ConflictError


class _FakeMinioClient:
    def __init__(self):
        self.config = SimpleNamespace(presigned_url_expires_seconds=123)
        self.put_calls = []
        self.removed = []

    def get_bucket(self) -> str:
        return "attachments"

    def put_object(self, **kwargs) -> None:
        self.put_calls.append(kwargs)

    def remove_object(self, object_name: str) -> None:
        self.removed.append(object_name)

    def presigned_get_object(self, object_name: str, expires_seconds: int | None = None) -> str:
        return f"http://minio.local/{object_name}?expires={expires_seconds}"


class _FakeAttachment:
    file_id = "file-1"
    original_filename = "input.json"
    bucket = "attachments"
    object_name = "attachments/file-1.json"
    size = 128
    content_type = "application/json"
    sha256 = "abc123"
    uploaded_by = "u-1"
    uploaded_at = datetime(2026, 7, 20, 8, 0, 0, tzinfo=timezone.utc)
    is_deleted = False
    deleted_at = None

    def __init__(self):
        self.updated = False

    async def update(self) -> None:
        self.updated = True


def _service(monkeypatch, minio=None, reference_checker=None) -> AttachmentService:
    minio = minio or _FakeMinioClient()
    monkeypatch.setattr("app.modules.attachments.service.attachment_service.get_minio_client", lambda: minio)
    return AttachmentService(reference_checker=reference_checker)


async def test_to_info_includes_sha256(monkeypatch) -> None:
    service = _service(monkeypatch)

    info = service.to_info(_FakeAttachment())

    assert info.sha256 == "abc123"
    assert info.storage_path == "attachments/attachments/file-1.json"


async def test_get_download_url_uses_default_expiry_and_to_thread(monkeypatch) -> None:
    calls = []

    async def fake_to_thread(func, *args, **kwargs):
        calls.append((func.__name__, args, kwargs))
        return func(*args, **kwargs)

    monkeypatch.setattr("app.modules.attachments.service.attachment_service.asyncio.to_thread", fake_to_thread)
    monkeypatch.setattr(AttachmentService, "get_attachment", lambda self, file_id: asyncio.sleep(0, _FakeAttachment()))
    service = _service(monkeypatch)

    url = await service.get_download_url("file-1")

    assert url.endswith("expires=123")
    assert calls == [("presigned_get_object", ("attachments/file-1.json",), {"expires_seconds": 123})]


async def test_upload_file_cleans_minio_object_when_metadata_create_fails(monkeypatch) -> None:
    minio = _FakeMinioClient()

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def fail_create(self):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr("app.modules.attachments.service.attachment_service.asyncio.to_thread", fake_to_thread)
    monkeypatch.setattr(AttachmentDoc, "create", fail_create)
    service = _service(monkeypatch, minio=minio)

    with pytest.raises(RuntimeError, match="Failed to upload file"):
        await service.upload_file("input.json", b"{}", "application/json", "u-1")

    assert minio.put_calls
    assert minio.removed == [minio.put_calls[0]["object_name"]]


async def test_delete_attachment_rejects_referenced_file(monkeypatch) -> None:
    attachment = _FakeAttachment()
    service = _service(monkeypatch, reference_checker=lambda file_id: asyncio.sleep(0, True))
    monkeypatch.setattr(AttachmentService, "get_attachment", lambda self, file_id: asyncio.sleep(0, attachment))

    with pytest.raises(ConflictError):
        await service.delete_attachment("file-1")

    assert attachment.is_deleted is False
    assert attachment.updated is False


async def test_delete_attachment_soft_deletes_unreferenced_file(monkeypatch) -> None:
    attachment = _FakeAttachment()
    service = _service(monkeypatch, reference_checker=lambda file_id: asyncio.sleep(0, False))
    monkeypatch.setattr(AttachmentService, "get_attachment", lambda self, file_id: asyncio.sleep(0, attachment))

    assert await service.delete_attachment("file-1") is True
    assert attachment.is_deleted is True
    assert attachment.deleted_at is not None
    assert attachment.updated is True
