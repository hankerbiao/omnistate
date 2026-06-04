"""Test Lab document model for catalog L1."""
from datetime import datetime, timezone

from beanie import Document, before_event, Insert, Save
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class TestLabDoc(Document):
    """L1 Lab preset managed by admins/TPM."""

    lab_id: str = Field(..., description="业务主键，如 LAB-BIOS")
    code: str = Field(..., description="唯一编码，创建后不可变")
    name: str = Field(..., description="显示名称")
    description: str | None = Field(None, description="描述")
    sort_order: int = Field(default=0, description="排序")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "test_labs"
        indexes = [
            IndexModel("lab_id", unique=True),
            IndexModel("code", unique=True),
            IndexModel([("is_active", ASCENDING), ("sort_order", ASCENDING)]),
        ]
