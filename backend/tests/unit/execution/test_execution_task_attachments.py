from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.modules.attachments.repository.models import AttachmentDoc
from app.modules.attachments.service.attachment_service import AttachmentService
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_command_helpers import (
    _extract_and_enrich_file_params,
    build_dispatch_task_data,
    initialize_command,
)
from app.modules.execution.schemas import DispatchTaskRequest, RerunTaskRequest


class _FakeFindResult:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self):
        return self._docs


class _FakeAttachment:
    file_id = "file-1"
    original_filename = "input.json"
    bucket = "attachments"
    object_name = "attachments/file-1.json"
    size = 128
    content_type = "application/json"
    sha256 = "abc123deadbeef"
    uploaded_at = datetime(2026, 4, 30, 8, 0, 0, tzinfo=timezone.utc)


class _FakeMinioClient:
    def presigned_get_object(self, object_name: str, expires_seconds: int = 604800) -> str:
        return f"http://minio.local/{object_name}?expires={expires_seconds}"


def test_dispatch_task_request_accepts_task_attachments() -> None:
    request = DispatchTaskRequest(
        dispatch_channel="RABBITMQ",
        cases=[{"auto_case_id": "AUTO-1"}],
        attachments=[{"file_id": "file-1", "original_filename": "input.json"}],
    )

    assert request.attachments[0].file_id == "file-1"


def test_rerun_request_can_explicitly_clear_attachments() -> None:
    request = RerunTaskRequest(attachments=[])

    assert "attachments" in request.model_fields_set
    assert request.attachments == []


def test_enrich_for_dispatch_reads_attachment_docs(monkeypatch) -> None:
    monkeypatch.setattr(
        AttachmentDoc, "find", lambda *args, **kwargs: _FakeFindResult([_FakeAttachment()])
    )

    result = asyncio.run(
        AttachmentService().enrich_for_dispatch(["file-1"])
    )

    assert result == [
        {
            "file_id": "file-1",
            "original_filename": "input.json",
            "storage_path": "attachments/attachments/file-1.json",
            "bucket": "attachments",
            "object_name": "attachments/file-1.json",
            "size": 128,
            "content_type": "application/json",
            "sha256": "abc123deadbeef",
            "uploaded_at": "2026-04-30T08:00:00+00:00",
        }
    ]


def test_enrich_for_dispatch_rejects_missing_attachment(monkeypatch) -> None:
    monkeypatch.setattr(
        AttachmentDoc, "find", lambda *args, **kwargs: _FakeFindResult([])
    )

    with pytest.raises(KeyError, match="attachment not found or deleted"):
        asyncio.run(AttachmentService().enrich_for_dispatch(["missing"]))


def test_dispatch_task_data_refreshes_file_param_urls(monkeypatch) -> None:
    monkeypatch.setattr("app.shared.minio.get_minio_client", lambda: _FakeMinioClient())

    command = DispatchExecutionTaskCommand(
        task_id="ET-2026-000001",
        created_by="u-1",
        dispatch_channel="RABBITMQ",
        auto_case_ids=["AUTO-1"],
        case_ids=["TC-1"],
        case_payloads=[{
            "case_id": "TC-1",
            "script_path": "tests/test_demo.py",
            "script_name": "test_demo",
            "parameters": {
                "threshold": "0.5",
                "firmware": {
                    "type": "file",
                    "file_id": "file-1",
                    "object_name": "attachments/file-1.json",
                    "original_filename": "fw.bin",
                },
            },
        }],
    )

    initialize_command(command)
    payload = build_dispatch_task_data(command)
    data = payload["data"]

    # Task-level attachments should not exist
    assert "attachments" not in data

    # File param is extracted to top-level files with a fresh presigned URL
    assert data["cases"][0]["parameters"]["firmware"] == ""
    assert data["files"]["firmware"]["url"] == "http://minio.local/attachments/file-1.json?expires=604800"


def test_refresh_file_param_urls_graceful_minio_failure(monkeypatch) -> None:
    def _failing_minio():
        raise RuntimeError("MinIO unavailable")

    monkeypatch.setattr("app.shared.minio.get_minio_client", _failing_minio)

    params = {
        "threshold": "0.5",
        "firmware": {
            "type": "file",
            "file_id": "file-1",
            "object_name": "attachments/file-1.json",
            "download_url": "http://old-url/fw.bin",
        },
    }

    modified_params, files_dict = _extract_and_enrich_file_params(params)

    # Should keep original params when MinIO client initialization fails
    assert modified_params["firmware"]["download_url"] == "http://old-url/fw.bin"
    assert files_dict == {}
