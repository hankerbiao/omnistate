"""Test Lab document model for catalog L1."""

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.shared.core.document_mixins import TimestampedDocumentMixin


class TestLabDoc(Document, TimestampedDocumentMixin):
    """L1 Lab preset managed by admins/TPM."""

    lab_id: str = Field(..., description="业务主键，如 LAB-BIOS")
    code: str = Field(..., description="唯一编码，创建后不可变")
    name: str = Field(..., description="显示名称")
    description: str | None = Field(None, description="描述")
    sort_order: int = Field(default=0, description="排序")
    is_active: bool = Field(default=True, description="是否启用")

    class Settings:
        name = "test_labs"
        indexes = [
            IndexModel("lab_id", unique=True),
            IndexModel("code", unique=True),
            IndexModel([("is_active", ASCENDING), ("sort_order", ASCENDING)]),
        ]
