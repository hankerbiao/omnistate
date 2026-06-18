"""Catalog path segment registry for Creatable suggestions."""
from datetime import datetime, timezone

from beanie import Document
from pydantic import Field
from pymongo import IndexModel

from app.shared.core.document_mixins import TimestampedDocumentMixin


class TestCatalogSegmentDoc(Document, TimestampedDocumentMixin):
    """Lazy-registered catalog segment (not authoritative for case paths)."""

    lab_id: str = Field(..., description="所属 Lab")
    parent_path: list[str] = Field(default_factory=list, description="父路径，[] 表示 Lab 直下")
    segment_name: str = Field(..., description="规范化后小写段名")
    usage_count: int = Field(default=0, description="引用计数")

    class Settings:
        name = "test_catalog_segments"
        indexes = [
            IndexModel(
                [("lab_id", 1), ("parent_path", 1), ("segment_name", 1)],
                unique=True,
            ),
            IndexModel("lab_id"),
        ]
