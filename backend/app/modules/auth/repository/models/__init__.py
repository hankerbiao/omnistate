"""Auth Beanie model exports."""
from .rbac import RoleDoc, RoleModel, UserDoc, UserModel

__all__ = [
    "UserDoc",
    "RoleDoc",
    "UserModel",
    "RoleModel",
    "DOCUMENT_MODELS",
]

DOCUMENT_MODELS = [UserDoc, RoleDoc]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)
