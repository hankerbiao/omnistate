from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_command_service import ExecutionTaskCommandService
from app.modules.execution.schemas import DispatchTaskRequest, RerunTaskRequest


def _async_value(value):
    async def _coro():
        return value

    return _coro()


class _FakeAttachment:
    file_id = "file-1"
    original_filename = "input.json"
    bucket = "attachments"
    object_name = "attachments/file-1.json"
    size = 128
    content_type = "application/json"
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


def test_validate_and_enrich_attachments_reads_attachment_doc(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.execution.application.task_command_service.AttachmentDoc.find_one",
        lambda *args, **kwargs: _async_value(_FakeAttachment()),
    )

    result = asyncio.run(
        ExecutionTaskCommandService._validate_and_enrich_attachments(
            [{"file_id": "file-1", "original_filename": "client-name.json"}]
        )
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
            "uploaded_at": "2026-04-30T08:00:00+00:00",
        }
    ]


def test_validate_and_enrich_attachments_rejects_missing_attachment(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.execution.application.task_command_service.AttachmentDoc.find_one",
        lambda *args, **kwargs: _async_value(None),
    )

    with pytest.raises(KeyError, match="attachment not found or deleted"):
        asyncio.run(ExecutionTaskCommandService._validate_and_enrich_attachments([{"file_id": "missing"}]))


def test_dispatch_task_data_adds_presigned_attachment_urls(monkeypatch) -> None:
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
            "parameters": {},
        }],
        attachments=[{
            "file_id": "file-1",
            "original_filename": "input.json",
            "storage_path": "attachments/attachments/file-1.json",
            "bucket": "attachments",
            "object_name": "attachments/file-1.json",
            "size": 128,
            "content_type": "application/json",
            "uploaded_at": "2026-04-30T08:00:00+00:00",
        }],
    )

    payload = command.dispatch_task_data

    assert payload["attachments"] == [
        {
            "file_id": "file-1",
            "original_filename": "input.json",
            "storage_path": "attachments/attachments/file-1.json",
            "size": 128,
            "content_type": "application/json",
            "uploaded_at": "2026-04-30T08:00:00+00:00",
            "download_url": "http://minio.local/attachments/file-1.json?expires=604800",
        }
    ]
