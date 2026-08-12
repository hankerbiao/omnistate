"""Project membership, controlled documents, and project file library models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel

from app.shared.core.document_mixins import SoftDeleteDocumentMixin, TimestampedDocumentMixin


class ProjectMemberDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
    project_id: str
    user_id: str
    role_code: str
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "project_members"
        indexes = [
            *SoftDeleteDocumentMixin.Settings.indexes,
            IndexModel([('project_id', ASCENDING), ('user_id', ASCENDING)], unique=True, partialFilterExpression={'is_deleted': False}),
            IndexModel([('project_id', ASCENDING), ('role_code', ASCENDING)]),
        ]


class DocumentReviewer(BaseModel):
    user_id: str
    decision: Optional[str] = None
    comment: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class ProjectDocumentDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
    document_id: str
    project_id: str
    name: str
    current_version: int = 1
    phase_code: str
    status: str = "DRAFT"
    updated_by: str

    class Settings:
        name = "project_documents"
        indexes = [
            *SoftDeleteDocumentMixin.Settings.indexes,
            IndexModel([('project_id', ASCENDING), ('name', ASCENDING)], unique=True, partialFilterExpression={'is_deleted': False}),
            IndexModel([('project_id', ASCENDING), ('phase_code', ASCENDING)]),
        ]


class ProjectDocumentVersionDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
    document_id: str
    project_id: str
    version: int
    phase_code: str
    attachment_id: str
    submitted_by: str
    reviewers: List[DocumentReviewer] = Field(default_factory=list)
    status: str = "DRAFT"
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Settings:
        name = "project_document_versions"
        indexes = [
            *SoftDeleteDocumentMixin.Settings.indexes,
            IndexModel([('document_id', ASCENDING), ('version', ASCENDING)], unique=True),
            IndexModel([('project_id', ASCENDING), ('status', ASCENDING)]),
        ]


class ProjectFolderDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
    folder_id: str
    project_id: str
    name: str
    normalized_name: str
    parent_folder_id: Optional[str] = None
    depth: int = 0
    created_by: str

    class Settings:
        name = "project_folders"
        indexes = [
            *SoftDeleteDocumentMixin.Settings.indexes,
            IndexModel([('project_id', ASCENDING), ('parent_folder_id', ASCENDING), ('normalized_name', ASCENDING)], unique=True, partialFilterExpression={'is_deleted': False}),
        ]


class ProjectFileDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
    project_file_id: str
    project_id: str
    folder_id: Optional[str] = None
    name: str
    normalized_name: str
    attachment_id: str
    created_by: str
    updated_by: str

    class Settings:
        name = "project_files"
        indexes = [
            *SoftDeleteDocumentMixin.Settings.indexes,
            IndexModel([('project_id', ASCENDING), ('folder_id', ASCENDING), ('normalized_name', ASCENDING)], unique=True, partialFilterExpression={'is_deleted': False}),
            IndexModel([('project_id', ASCENDING), ('folder_id', ASCENDING)]),
        ]
