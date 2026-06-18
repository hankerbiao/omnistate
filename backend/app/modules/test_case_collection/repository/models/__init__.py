"""用例集合模型导出。"""
from .collection import TestCaseCollectionDoc

__all__ = ["TestCaseCollectionDoc"]
DOCUMENT_MODELS = [TestCaseCollectionDoc]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)
