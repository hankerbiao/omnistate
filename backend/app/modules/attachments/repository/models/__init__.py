from .attachment import AttachmentDoc

__all__ = ["AttachmentDoc", "DOCUMENT_MODELS"]

DOCUMENT_MODELS = [AttachmentDoc]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)
