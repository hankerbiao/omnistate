from app.modules.system_config.repository.models.config import SystemConfigDoc, SystemConfigHistoryDoc

DOCUMENT_MODELS = [SystemConfigDoc, SystemConfigHistoryDoc]

__all__ = ["SystemConfigDoc", "SystemConfigHistoryDoc", "DOCUMENT_MODELS"]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)
