"""用例集合模型导出。"""
from app.shared.infrastructure.document_registry import register_document_model

from .change_log import TestCaseCollectionChangeLogDoc
from .collection import TestCaseCollectionDoc

__all__ = ["TestCaseCollectionDoc", "TestCaseCollectionChangeLogDoc"]
DOCUMENT_MODELS = [TestCaseCollectionDoc, TestCaseCollectionChangeLogDoc]

for _model in DOCUMENT_MODELS:
    register_document_model(_model)
