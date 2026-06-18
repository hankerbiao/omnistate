"""Beanie Document 模型自动注册表。

消除 app/shared/infrastructure/bootstrap.py 中手动 import 所有模块的
DOCUMENT_MODELS 列表的硬编码依赖。
"""

from __future__ import annotations

from typing import Any, List


# 全局文档模型注册表
_document_registry: List[type[Any]] = []


def register_document_model(model_cls: type[Any]) -> None:
    """模块调用此函数注册 Beanie Document 模型。"""
    if model_cls not in _document_registry:
        _document_registry.append(model_cls)


def get_document_models() -> List[type[Any]]:
    """返回所有已注册的文档模型列表。"""
    return list(_document_registry)
