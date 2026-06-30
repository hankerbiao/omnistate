"""审计日志文档模型注册。"""
from __future__ import annotations

from app.modules.audit.repository.models.audit_log import AuditLogDoc
from app.modules.audit.repository.models.ai_feedback import AiFeedbackDoc

__all__ = ["AuditLogDoc", "AiFeedbackDoc", "DOCUMENT_MODELS"]

DOCUMENT_MODELS = [AuditLogDoc, AiFeedbackDoc]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)
