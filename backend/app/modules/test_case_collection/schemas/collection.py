"""用例集合 Pydantic Schema。"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CreateCollectionRequest(BaseModel):
    """创建用例集合请求。"""
    name: str = Field(..., min_length=1, max_length=200, description="集合名称")
    description: Optional[str] = Field(None, max_length=2000, description="集合说明")
    tags: List[str] = Field(default_factory=list, description="标签")
    case_ids: List[str] = Field(default_factory=list, description="初始添加的手工用例 ID")
    auto_case_ids: List[str] = Field(default_factory=list, description="初始添加的自动化用例 ID")


class UpdateCollectionRequest(BaseModel):
    """更新用例集合请求。"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = None


class CollectionResponse(BaseModel):
    """用例集合响应。"""
    collection_id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    case_ids: List[str] = []
    auto_case_ids: List[str] = []
    case_count: int = 0
    auto_case_count: int = 0
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_doc(cls, doc) -> "CollectionResponse":
        return cls(
            collection_id=doc.collection_id,
            name=doc.name,
            description=doc.description,
            tags=doc.tags,
            case_ids=doc.case_ids,
            auto_case_ids=doc.auto_case_ids,
            case_count=len(doc.case_ids),
            auto_case_count=len(doc.auto_case_ids),
            created_by=doc.created_by,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )


class AddCasesRequest(BaseModel):
    """向集合添加用例请求。"""
    case_ids: List[str] = Field(default_factory=list, description="手工用例 ID 列表")
    auto_case_ids: List[str] = Field(default_factory=list, description="自动化用例 ID 列表")


class RemoveCasesRequest(BaseModel):
    """从集合移除用例请求。"""
    case_ids: List[str] = Field(default_factory=list)
    auto_case_ids: List[str] = Field(default_factory=list)


class CollectionListItem(BaseModel):
    """用例集合列表项。"""
    collection_id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    case_count: int = 0
    auto_case_count: int = 0
    created_by: str
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_doc(cls, doc) -> "CollectionListItem":
        return cls(
            collection_id=doc.collection_id,
            name=doc.name,
            description=doc.description,
            tags=doc.tags,
            case_count=len(doc.case_ids),
            auto_case_count=len(doc.auto_case_ids),
            created_by=doc.created_by,
            updated_at=doc.updated_at,
        )
