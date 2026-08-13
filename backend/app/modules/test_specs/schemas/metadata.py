"""API schemas for the global test-case metadata dictionary."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class MetadataTypeDefinition(BaseModel):
    type_code: str
    label: str
    field_name: str
    multiple: bool = False
    required: bool = False


class TestCaseMetadataResponse(BaseModel):
    id: str
    type_code: str
    code: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    is_default: bool = False
    is_legacy: bool = False
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetadataTypesResponse(BaseModel):
    definitions: list[MetadataTypeDefinition]
    options: dict[str, list[TestCaseMetadataResponse]]


class CreateTestCaseMetadataRequest(BaseModel):
    type_code: str = Field(..., min_length=1, max_length=64)
    code: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=32)
    sort_order: int = Field(0, ge=0, le=100000)
    is_active: bool = True
    is_default: bool = False


class UpdateTestCaseMetadataRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=32)
    sort_order: Optional[int] = Field(None, ge=0, le=100000)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
