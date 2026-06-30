"""通知模块文档模型注册。"""
from __future__ import annotations

from app.modules.notification.repository.models.pending_notification import PendingNotificationDoc

__all__ = [
    "PendingNotificationDoc",
    "DOCUMENT_MODELS",
]

DOCUMENT_MODELS = [
    PendingNotificationDoc,
]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)
