from app.modules.project.repository.models.project import ProjectDoc
from app.modules.project.repository.models.assets import (
    DocumentReviewer, ProjectDocumentDoc, ProjectDocumentVersionDoc, ProjectFileDoc, ProjectFolderDoc, ProjectMemberDoc,
)

DOCUMENT_MODELS = [
    ProjectDoc,
    ProjectMemberDoc, ProjectDocumentDoc, ProjectDocumentVersionDoc, ProjectFolderDoc, ProjectFileDoc,
]

__all__ = [
    "ProjectDoc",
    "ProjectMemberDoc",
    "DocumentReviewer",
    "ProjectDocumentDoc",
    "ProjectDocumentVersionDoc",
    "ProjectFolderDoc",
    "ProjectFileDoc",
    "DOCUMENT_MODELS",
]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)
