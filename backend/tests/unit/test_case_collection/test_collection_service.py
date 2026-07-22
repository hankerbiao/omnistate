from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.test_case_collection.schemas import (
    CollectionResponse,
    CopyCollectionRequest,
    CreateCollectionRequest,
)
from app.modules.test_case_collection.service.collection_service import (
    TestCaseCollectionService as CollectionService,
)


class _FakeCollectionDoc:
    doc = None

    @classmethod
    async def find_one(cls, query):
        if cls.doc and query.get("collection_id") == cls.doc.collection_id:
            return cls.doc
        return None


@pytest.mark.asyncio
async def test_copy_collection_preserves_cases_when_requested(monkeypatch):
    service = CollectionService()
    source = SimpleNamespace(
        collection_id="CC-0001",
        name="回归",
        description="baseline",
        tags=["P0"],
        case_ids=["TC-1", "TC-2"],
        auto_case_ids=["AC-1"],
        created_by="u1",
        created_at=None,
        updated_at=None,
    )
    _FakeCollectionDoc.doc = source
    monkeypatch.setattr(
        "app.modules.test_case_collection.service.collection_service.TestCaseCollectionDoc",
        _FakeCollectionDoc,
    )

    async def fake_create(request: CreateCollectionRequest, creator_id: str, current_user=None):
        assert creator_id == "u2"
        assert request.case_ids == source.case_ids
        assert request.auto_case_ids == source.auto_case_ids
        return CollectionResponse(
            collection_id="CC-0002",
            name=request.name,
            description=request.description,
            tags=request.tags,
            case_ids=request.case_ids,
            auto_case_ids=request.auto_case_ids,
            case_count=len(request.case_ids),
            auto_case_count=len(request.auto_case_ids),
            created_by=creator_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    service.create = fake_create
    service._save_log = AsyncMock()

    result = await service.copy(
        "CC-0001",
        CopyCollectionRequest(name="回归 副本", description="copy", tags=["P1"], include_cases=True),
        {"user_id": "u2", "username": "tester"},
    )

    assert result.collection_id == "CC-0002"
    assert service._save_log.await_count == 2


def test_case_changes_groups_manual_and_auto_cases():
    changes = CollectionService._case_changes("ADD", ["TC-1"], ["AC-1"])

    assert changes == [
        {"type": "manual", "case_id": "TC-1", "action": "ADD"},
        {"type": "auto", "case_id": "AC-1", "action": "ADD"},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("export_format, expected_media", [
    ("csv", "text/csv; charset=utf-8"),
    ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
])
async def test_export_cases_returns_file_with_empty_collection(monkeypatch, export_format, expected_media):
    service = CollectionService()
    doc = SimpleNamespace(
        collection_id="CC-0001",
        name="空集合",
        case_ids=[],
        auto_case_ids=[],
    )
    service._load_case_context = AsyncMock(return_value=(doc, {}, {}))
    service._export_rows = AsyncMock(return_value=[])
    service._save_log = AsyncMock()

    content, media_type, filename = await service.export_cases(
        "CC-0001",
        export_format,
        {"user_id": "u1"},
    )

    assert content
    assert media_type == expected_media
    assert filename == f"CC-0001_cases.{export_format}"
    service._load_case_context.assert_awaited_once_with("CC-0001")
    service._export_rows.assert_awaited_once_with(doc, {}, {})
    service._save_log.assert_awaited_once()


@pytest.mark.asyncio
async def test_collection_change_log_failure_does_not_fail_operation(monkeypatch):
    service = CollectionService()

    class FailingChangeLogDoc:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def insert(self):
            raise RuntimeError("mongo unavailable")

    warning = MagicMock()
    monkeypatch.setattr(
        "app.modules.test_case_collection.service.collection_service.TestCaseCollectionChangeLogDoc",
        FailingChangeLogDoc,
    )
    monkeypatch.setattr(
        "app.modules.test_case_collection.service.collection_service.log.warning",
        warning,
    )

    await service._save_log("CC-0001", "EXPORT", {"user_id": "u1"})

    warning.assert_called_once()
