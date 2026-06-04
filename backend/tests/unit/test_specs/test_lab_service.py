"""Unit tests for catalog path normalization and LabService."""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.domain.catalog_path import (  # noqa: E402
    build_catalog_path_key,
    normalize_catalog_path,
    normalize_catalog_segment,
)
from app.modules.test_specs.domain.exceptions import (  # noqa: E402
    CatalogPathValidationError,
    LabConflictError,
    LabNotFoundError,
)
from app.modules.test_specs.service.lab_service import LabService  # noqa: E402


class _FakeLabDoc:
    inserted: list[dict] = []
    store: dict[str, "_FakeLabDoc"] = {}

    def __init__(self, **payload):
        self.payload = dict(payload)
        self.id = f"id-{payload['lab_id']}"
        for key, value in payload.items():
            setattr(self, key, value)

    async def insert(self) -> None:
        self.__class__.inserted.append(dict(self.payload))
        self.__class__.store[self.lab_id] = self

    async def save(self) -> None:
        self.__class__.store[self.lab_id] = self

    async def delete(self) -> None:
        self.__class__.store.pop(self.lab_id, None)

    def model_dump(self) -> dict:
        data = dict(self.payload)
        data.update(
            {
                "lab_id": self.lab_id,
                "code": self.code,
                "name": self.name,
                "description": getattr(self, "description", None),
                "sort_order": self.sort_order,
                "is_active": self.is_active,
                "created_at": getattr(self, "created_at", datetime.now(timezone.utc)),
                "updated_at": getattr(self, "updated_at", datetime.now(timezone.utc)),
            }
        )
        return data

    @classmethod
    def reset(cls) -> None:
        cls.inserted = []
        cls.store = {}

    @classmethod
    def find_one(cls, query=None, *args, **kwargs):
        async def _coro():
            if isinstance(query, dict):
                if "code" in query:
                    for doc in cls.store.values():
                        if doc.code == query["code"]:
                            return doc
                if "lab_id" in query:
                    return cls.store.get(query["lab_id"])
            return None

        return _coro()

    @classmethod
    def find(cls, query=None):
        class _Query:
            async def sort(self, *args, **kwargs):
                return self

            async def to_list(self):
                docs = list(cls.store.values())
                if query and query.get("is_active") is True:
                    docs = [doc for doc in docs if doc.is_active]
                return sorted(docs, key=lambda d: (d.sort_order, d.code))

        return _Query()


def test_normalize_segment_strips_and_lowercases() -> None:
    assert normalize_catalog_segment("  BIOS  ") == "bios"


def test_normalize_segment_rejects_empty() -> None:
    with pytest.raises(CatalogPathValidationError):
        normalize_catalog_segment("   ")


def test_normalize_segment_rejects_slash() -> None:
    with pytest.raises(CatalogPathValidationError):
        normalize_catalog_segment("a/b")


def test_normalize_path_and_key() -> None:
    path = normalize_catalog_path([" BIOS ", "Release_Check"])
    assert path == ["bios", "release_check"]
    assert build_catalog_path_key(path) == "bios/release_check"


@pytest.fixture(autouse=True)
def reset_fake_lab_store():
    _FakeLabDoc.reset()
    yield
    _FakeLabDoc.reset()


def test_create_lab_preserves_code_case() -> None:
    service = LabService()

    with patch("app.modules.test_specs.service.lab_service.TestLabDoc", _FakeLabDoc):
        result = asyncio.run(
            service.create_lab({"code": "Bios", "name": "BIOS Lab", "sort_order": 1})
        )

    assert result["lab_id"] == "LAB-Bios"
    assert result["code"] == "Bios"
    assert result["name"] == "BIOS Lab"
    assert result["case_count"] == 0


def test_create_lab_strips_code_whitespace() -> None:
    service = LabService()

    with patch("app.modules.test_specs.service.lab_service.TestLabDoc", _FakeLabDoc):
        result = asyncio.run(
            service.create_lab({"code": "  DDR5  ", "name": "DDR5 Lab"})
        )

    assert result["code"] == "DDR5"
    assert result["lab_id"] == "LAB-DDR5"


def test_create_lab_rejects_duplicate_code() -> None:
    service = LabService()
    _FakeLabDoc.store["LAB-BIOS"] = _FakeLabDoc(
        lab_id="LAB-BIOS",
        code="BIOS",
        name="Existing",
        sort_order=0,
        is_active=True,
    )

    with patch("app.modules.test_specs.service.lab_service.TestLabDoc", _FakeLabDoc):
        with pytest.raises(LabConflictError):
            asyncio.run(service.create_lab({"code": "BIOS", "name": "Dup"}))


def test_update_lab_does_not_change_code() -> None:
    service = LabService()
    doc = _FakeLabDoc(
        lab_id="LAB-BIOS",
        code="BIOS",
        name="Old Name",
        sort_order=0,
        is_active=True,
    )
    _FakeLabDoc.store["LAB-BIOS"] = doc

    mock_collection = MagicMock()
    mock_collection.count_documents = AsyncMock(return_value=2)

    with patch("app.modules.test_specs.service.lab_service.TestLabDoc", _FakeLabDoc), patch.object(
        LabService,
        "_count_cases",
        AsyncMock(return_value=2),
    ):
        result = asyncio.run(
            service.update_lab("LAB-BIOS", {"name": "New Name", "code": "SHOULD-NOT-CHANGE"})
        )

    assert result["name"] == "New Name"
    assert result["code"] == "BIOS"
    assert result["case_count"] == 2


def test_delete_lab_rejects_when_cases_exist() -> None:
    service = LabService()
    _FakeLabDoc.store["LAB-BIOS"] = _FakeLabDoc(
        lab_id="LAB-BIOS",
        code="BIOS",
        name="BIOS",
        sort_order=0,
        is_active=True,
    )

    with patch("app.modules.test_specs.service.lab_service.TestLabDoc", _FakeLabDoc), patch.object(
        LabService,
        "_count_cases",
        AsyncMock(return_value=3),
    ):
        with pytest.raises(LabConflictError):
            asyncio.run(service.delete_lab("LAB-BIOS"))


def test_deactivate_lab_migrates_cases() -> None:
    service = LabService()
    _FakeLabDoc.store["LAB-BIOS"] = _FakeLabDoc(
        lab_id="LAB-BIOS",
        code="BIOS",
        name="BIOS",
        sort_order=0,
        is_active=True,
    )
    _FakeLabDoc.store["LAB-BMC"] = _FakeLabDoc(
        lab_id="LAB-BMC",
        code="BMC",
        name="BMC",
        sort_order=1,
        is_active=True,
    )

    with patch("app.modules.test_specs.service.lab_service.TestLabDoc", _FakeLabDoc), patch.object(
        LabService,
        "_migrate_cases",
        AsyncMock(return_value=5),
    ):
        result = asyncio.run(service.deactivate_lab("LAB-BIOS", "LAB-BMC"))

    assert result["is_active"] is False
    assert result["migrated_case_count"] == 5
    assert _FakeLabDoc.store["LAB-BIOS"].is_active is False


def test_deactivate_lab_raises_when_target_missing() -> None:
    service = LabService()
    _FakeLabDoc.store["LAB-BIOS"] = _FakeLabDoc(
        lab_id="LAB-BIOS",
        code="BIOS",
        name="BIOS",
        sort_order=0,
        is_active=True,
    )

    with patch("app.modules.test_specs.service.lab_service.TestLabDoc", _FakeLabDoc):
        with pytest.raises(LabNotFoundError):
            asyncio.run(service.deactivate_lab("LAB-BIOS", "LAB-MISSING"))
