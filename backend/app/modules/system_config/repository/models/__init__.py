from app.modules.system_config.repository.models.config import SystemConfigDoc, SystemConfigHistoryDoc

DOCUMENT_MODELS = [SystemConfigDoc, SystemConfigHistoryDoc]

__all__ = ["SystemConfigDoc", "SystemConfigHistoryDoc", "DOCUMENT_MODELS"]
