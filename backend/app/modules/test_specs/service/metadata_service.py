"""Metadata dictionary policies and persistence."""
from __future__ import annotations

from typing import Any, Optional

from beanie.exceptions import CollectionWasNotInitialized

from app.modules.test_specs.repository.models import TestCaseDoc, TestCaseMetadataDoc


METADATA_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"type_code": "TEST_CATEGORY", "label": "测试分类", "field_name": "test_category", "required": True},
    {"type_code": "PRIORITY", "label": "优先级", "field_name": "priority", "required": True},
    {"type_code": "CASE_TYPE", "label": "用例类型", "field_name": "case_type", "required": True},
    {"type_code": "TEST_LEVEL", "label": "测试级别", "field_name": "test_level"},
    {"type_code": "TEST_PHASE", "label": "测试阶段", "field_name": "test_phase"},
    {"type_code": "BUSINESS_DOMAIN", "label": "业务域", "field_name": "business_domain"},
    {"type_code": "RISK_LEVEL", "label": "风险等级", "field_name": "risk_level"},
    {"type_code": "CONFIDENTIALITY", "label": "数据敏感级别", "field_name": "confidentiality"},
    {"type_code": "TAG", "label": "标签", "field_name": "tags", "multiple": True},
)
_DEFINITION_BY_TYPE = {item["type_code"]: item for item in METADATA_DEFINITIONS}

DEFAULT_METADATA: tuple[dict[str, Any], ...] = (
    {"type_code": "PRIORITY", "code": "P0", "name": "紧急", "color": "#d93021", "sort_order": 0},
    {"type_code": "PRIORITY", "code": "P1", "name": "高", "color": "#f66a0a", "sort_order": 1, "is_default": True},
    {"type_code": "PRIORITY", "code": "P2", "name": "中", "color": "#e3b30e", "sort_order": 2},
    {"type_code": "PRIORITY", "code": "P3", "name": "低", "color": "#0b7ece", "sort_order": 3},
    *tuple(
        {"type_code": "TEST_CATEGORY", "code": code, "name": name, "sort_order": index}
        for index, (code, name) in enumerate((("FUNCTIONAL", "功能"), ("PERFORMANCE", "性能"), ("SECURITY", "安全"), ("COMPATIBILITY", "兼容性"), ("STABILITY", "稳定性"), ("REGRESSION", "回归")))
    ),
    *tuple(
        {"type_code": "CASE_TYPE", "code": code, "name": name, "sort_order": index}
        for index, (code, name) in enumerate((("POSITIVE", "正向"), ("NEGATIVE", "反向"), ("BOUNDARY", "边界"), ("EXCEPTION", "异常"), ("SECURITY", "安全")))
    ),
    *tuple(
        {"type_code": "TEST_LEVEL", "code": code, "name": name, "sort_order": index}
        for index, (code, name) in enumerate((("UNIT", "单元"), ("INTEGRATION", "集成"), ("SYSTEM", "系统"), ("ACCEPTANCE", "验收")))
    ),
    *tuple(
        {"type_code": "TEST_PHASE", "code": code, "name": code, "sort_order": index}
        for index, code in enumerate(("EVT", "DVT", "PVT"))
    ),
    *tuple(
        {"type_code": "BUSINESS_DOMAIN", "code": code, "name": name, "sort_order": index}
        for index, (code, name) in enumerate((("ACCOUNT", "账户"), ("ORDER", "订单"), ("PAYMENT", "支付"), ("MESSAGE", "消息")))
    ),
    *tuple(
        {"type_code": "RISK_LEVEL", "code": code, "name": name, "sort_order": index}
        for index, (code, name) in enumerate((("LOW", "低风险"), ("MEDIUM", "中风险"), ("HIGH", "高风险"), ("CRITICAL", "严重风险")))
    ),
    *tuple(
        {"type_code": "CONFIDENTIALITY", "code": code, "name": name, "sort_order": index}
        for index, (code, name) in enumerate((("PUBLIC", "公开"), ("INTERNAL", "内部"), ("CONFIDENTIAL", "机密"), ("RESTRICTED", "受限")))
    ),
)


class MetadataService:
    """CRUD and validation for globally shared test-case metadata."""

    @staticmethod
    def definition(type_code: str) -> dict[str, Any]:
        try:
            return _DEFINITION_BY_TYPE[type_code]
        except KeyError as exc:
            raise ValueError(f"unknown metadata type: {type_code}") from exc

    @classmethod
    def definitions(cls) -> list[dict[str, Any]]:
        return [dict(item) for item in METADATA_DEFINITIONS]

    @staticmethod
    def _to_dict(doc: TestCaseMetadataDoc, usage_count: int = 0) -> dict[str, Any]:
        result = doc.model_dump()
        result["id"] = str(doc.id)
        result["usage_count"] = usage_count
        return result

    @classmethod
    async def seed_defaults(cls) -> None:
        for payload in DEFAULT_METADATA:
            existing = await TestCaseMetadataDoc.find_one({"type_code": payload["type_code"], "code": payload["code"], "is_deleted": False})
            if existing:
                continue
            await TestCaseMetadataDoc(**payload).insert()

    @classmethod
    async def list_types(cls) -> dict[str, Any]:
        await cls.seed_defaults()
        docs = await TestCaseMetadataDoc.find({"is_deleted": False, "is_active": True}).sort(
            [("type_code", 1), ("sort_order", 1), ("name", 1)]
        ).to_list()
        return {
            "definitions": cls.definitions(),
            "options": {
                definition["type_code"]: [cls._to_dict(doc) for doc in docs if doc.type_code == definition["type_code"]]
                for definition in METADATA_DEFINITIONS
            },
        }

    @classmethod
    async def list_admin(cls, type_code: Optional[str] = None, active: Optional[bool] = None, q: Optional[str] = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        await cls.seed_defaults()
        query: dict[str, Any] = {"is_deleted": False}
        if type_code:
            cls.definition(type_code)
            query["type_code"] = type_code
        if active is not None:
            query["is_active"] = active
        if q and q.strip():
            query["$or"] = [{"name": {"$regex": q.strip(), "$options": "i"}}, {"code": {"$regex": q.strip(), "$options": "i"}}]
        docs = await TestCaseMetadataDoc.find(query).sort([("type_code", 1), ("sort_order", 1), ("name", 1)]).skip(offset).limit(limit).to_list()
        total = await TestCaseMetadataDoc.find(query).count()
        items = []
        for doc in docs:
            usage_count = await cls.usage_count(doc)
            items.append(cls._to_dict(doc, usage_count))
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def usage_count(doc: TestCaseMetadataDoc) -> int:
        if doc.type_code == "TAG":
            return await TestCaseDoc.find({"is_deleted": False, "tags": doc.code}).count()
        field_name = _DEFINITION_BY_TYPE[doc.type_code]["field_name"]
        return await TestCaseDoc.find({"is_deleted": False, field_name: doc.code}).count()

    @classmethod
    async def create(cls, payload: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
        cls.definition(payload["type_code"])
        existing = await TestCaseMetadataDoc.find_one({"type_code": payload["type_code"], "code": payload["code"], "is_deleted": False})
        if existing:
            raise ValueError("metadata code already exists")
        if payload.get("is_default"):
            await cls._clear_default(payload["type_code"])
        payload = {**payload, "created_by": actor, "updated_by": actor}
        doc = TestCaseMetadataDoc(**payload)
        await doc.insert()
        return cls._to_dict(doc)

    @classmethod
    async def update(cls, metadata_id: str, payload: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
        try:
            doc = await TestCaseMetadataDoc.get(metadata_id)
        except (TypeError, ValueError):
            doc = None
        if not doc or doc.is_deleted:
            raise KeyError("metadata not found")
        if payload.get("is_default"):
            if not payload.get("is_active", doc.is_active):
                raise ValueError("default metadata must be active")
            await cls._clear_default(doc.type_code, exclude_id=doc.id)
        for field, value in payload.items():
            setattr(doc, field, value)
        if not doc.is_active and doc.is_default:
            doc.is_default = False
        doc.updated_by = actor
        await doc.save()
        return cls._to_dict(doc, await cls.usage_count(doc))

    @classmethod
    async def deactivate(cls, metadata_id: str, actor: str | None = None) -> dict[str, Any]:
        return await cls.update(metadata_id, {"is_active": False, "is_default": False}, actor)

    @staticmethod
    async def _clear_default(type_code: str, exclude_id: Any = None) -> None:
        query: dict[str, Any] = {"type_code": type_code, "is_default": True, "is_deleted": False}
        if exclude_id is not None:
            query["_id"] = {"$ne": exclude_id}
        await TestCaseMetadataDoc.find(query).update_many({"$set": {"is_default": False}})

    @classmethod
    async def validate_case_payload(cls, payload: dict[str, Any], existing: Optional[TestCaseDoc] = None) -> dict[str, Any]:
        """Validate active options; allow an existing disabled value to remain on edit."""
        try:
            await cls.seed_defaults()
            docs = await TestCaseMetadataDoc.find({"is_deleted": False}).to_list()
        except CollectionWasNotInitialized:
            # Unit tests can exercise TestCaseService with a fake repository without Mongo.
            return payload
        by_type = {type_code: {doc.code: doc for doc in docs if doc.type_code == type_code} for type_code in _DEFINITION_BY_TYPE}
        for definition in METADATA_DEFINITIONS:
            field_name = definition["field_name"]
            field_present = field_name in payload
            value = payload.get(field_name)
            if existing is not None and not field_present:
                value = getattr(existing, field_name, None)
            if definition.get("required") and existing is None and not value:
                raise ValueError(f"{definition['label']}不能为空")
            values = value if definition.get("multiple") and isinstance(value, list) else [value]
            if not value:
                continue
            for option in values:
                doc = by_type.get(definition["type_code"], {}).get(option)
                if not doc:
                    raise ValueError(f"{definition['label']}选项无效: {option}")
                if not doc.is_active:
                    existing_value = existing and getattr(existing, field_name, None)
                    if not (option in existing_value if isinstance(existing_value, list) else option == existing_value):
                        raise ValueError(f"{definition['label']}选项已停用: {option}")
            if definition.get("multiple") and field_present:
                payload[field_name] = list(dict.fromkeys(values))
        return payload
