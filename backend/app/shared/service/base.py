"""通用服务基类"""
from typing import Dict, Any, Iterable


class BaseService:
    """提供通用的文档转换与更新方法"""

    @staticmethod
    def _doc_to_dict(doc) -> Dict[str, Any]:
        data = doc.model_dump()
        data["id"] = str(doc.id)
        return data

    @staticmethod
    def _filter_updates(data: Dict[str, Any], allowed_fields: Iterable[str]) -> Dict[str, Any]:
        allowed = set(allowed_fields)
        return {key: value for key, value in data.items() if key in allowed}

    @staticmethod
    def _apply_updates(doc, data: Dict[str, Any], allowed_fields: Iterable[str]) -> None:
        updates = BaseService._filter_updates(data, allowed_fields)
        for key, value in updates.items():
            setattr(doc, key, value)
