"""Global metadata dictionary entries used by manual test cases."""
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.shared.core.document_mixins import TimestampedDocumentMixin, SoftDeleteDocumentMixin


class TestCaseMetadataDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
    """A stable, administrator-managed option for a test-case metadata field."""

    type_code: str = Field(..., description="Metadata field type code")
    code: str = Field(..., description="Stable option code; immutable after creation")
    name: str = Field(..., description="Display name")
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    is_default: bool = False
    is_legacy: bool = False
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Settings:
        name = "test_case_metadata"
        indexes = [
            *SoftDeleteDocumentMixin.Settings.indexes,
            IndexModel([
                ("type_code", ASCENDING),
                ("code", ASCENDING),
            ], unique=True),
            IndexModel([
                ("type_code", ASCENDING),
                ("is_active", ASCENDING),
                ("sort_order", ASCENDING),
            ]),
        ]
