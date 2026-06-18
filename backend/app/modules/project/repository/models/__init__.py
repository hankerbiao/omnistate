from app.modules.project.repository.models.project import ProjectDoc

DOCUMENT_MODELS = [
    ProjectDoc,
]

__all__ = [
    "ProjectDoc",
    "DOCUMENT_MODELS",
]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)
