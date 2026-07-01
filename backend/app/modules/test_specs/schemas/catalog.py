"""Catalog / Lab API schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class CreateLabRequest(BaseModel):
    code: str = Field(..., min_length=1, description="唯一编码，创建后不可变")
    name: str = Field(..., min_length=1, description="显示名称")
    description: str | None = None
    sort_order: int = 0


class UpdateLabRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None


class DeactivateLabRequest(BaseModel):
    target_lab_id: str = Field(..., min_length=1, description="迁移目标 Lab")


class LabResponse(BaseModel):
    lab_id: str
    code: str
    name: str
    description: str | None = None
    sort_order: int
    is_active: bool
    case_count: int = 0
    migrated_case_count: int | None = None
    created_at: datetime
    updated_at: datetime


class CatalogTreeNode(BaseModel):
    name: str
    path: list[str] = Field(default_factory=list)
    case_count: int = 0
    children: list["CatalogTreeNode"] = Field(default_factory=list)


CatalogTreeNode.model_rebuild()


class CatalogTreeResponse(BaseModel):
    lab_id: str
    tree: CatalogTreeNode


class CatalogSuggestionsResponse(BaseModel):
    lab_id: str
    parent_path: list[str]
    segments: list[str]
