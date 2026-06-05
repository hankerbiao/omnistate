"""Catalog path helpers: segments, suggestions, tree, breadcrumbs."""
from __future__ import annotations

from typing import Any

from app.modules.test_specs.domain.catalog_path import build_catalog_path_key, normalize_catalog_path
from app.modules.test_specs.domain.exceptions import LabNotFoundError
from app.modules.test_specs.repository.models import TestCaseDoc, TestCatalogSegmentDoc, TestLabDoc


class CatalogService:
    """Catalog domain operations shared by labs and test cases."""

    @staticmethod
    def normalize_path_segments(segments: list[str]) -> list[str]:
        return normalize_catalog_path(segments)

    @staticmethod
    def build_path_key(segments: list[str]) -> str:
        return build_catalog_path_key(segments)

    async def ensure_active_lab(self, lab_id: str) -> TestLabDoc:
        lab = await TestLabDoc.find_one({"lab_id": lab_id})
        if not lab:
            raise LabNotFoundError(lab_id)
        if not lab.is_active:
            raise ValueError(f"Lab {lab_id} 未启用")
        return lab

    async def prepare_catalog_fields(self, lab_id: str, catalog_path: list[str]) -> dict[str, Any]:
        await self.ensure_active_lab(lab_id)
        normalized = self.normalize_path_segments(catalog_path)
        return {
            "lab_id": lab_id,
            "catalog_path": normalized,
            "catalog_path_key": self.build_path_key(normalized),
        }

    async def register_path(self, lab_id: str, catalog_path: list[str], delta: int = 1) -> None:
        if delta == 0:
            return
        normalized = self.normalize_path_segments(catalog_path)
        for depth in range(len(normalized)):
            parent_path = normalized[:depth]
            segment_name = normalized[depth]
            await self._adjust_segment(lab_id, parent_path, segment_name, delta)

    async def _adjust_segment(
        self,
        lab_id: str,
        parent_path: list[str],
        segment_name: str,
        delta: int,
    ) -> None:
        doc = await TestCatalogSegmentDoc.find_one(
            {
                "lab_id": lab_id,
                "parent_path": parent_path,
                "segment_name": segment_name,
            }
        )
        if doc:
            doc.usage_count = max(0, doc.usage_count + delta)
            if doc.usage_count == 0:
                await doc.delete()
            else:
                await doc.save()
            return

        if delta > 0:
            await TestCatalogSegmentDoc(
                lab_id=lab_id,
                parent_path=parent_path,
                segment_name=segment_name,
                usage_count=delta,
            ).insert()

    async def get_suggestions(
        self,
        lab_id: str,
        parent_path: list[str] | None = None,
    ) -> list[str]:
        await self.ensure_active_lab(lab_id)
        parent = parent_path or []
        segments = await TestCatalogSegmentDoc.find(
            {
                "lab_id": lab_id,
                "parent_path": parent,
                "usage_count": {"$gt": 0},
            }
        ).sort("+segment_name").to_list()
        return [doc.segment_name for doc in segments]

    async def build_breadcrumb(
        self,
        lab_id: str,
        catalog_path: list[str],
        case_title: str | None = None,
    ) -> str:
        lab = await TestLabDoc.find_one({"lab_id": lab_id})
        lab_name = lab.name if lab else lab_id
        parts = [lab_name, *catalog_path]
        if case_title:
            parts.append(case_title)
        return " / ".join(parts)

    async def enrich_case_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        lab_id = data.get("lab_id")
        catalog_path = data.get("catalog_path") or []
        if lab_id:
            lab = await TestLabDoc.find_one({"lab_id": lab_id})
            data["lab_name"] = lab.name if lab else lab_id
        else:
            data["lab_name"] = None
        if lab_id and catalog_path:
            data["catalog_breadcrumb"] = await self.build_breadcrumb(
                lab_id,
                catalog_path,
            )
        else:
            data["catalog_breadcrumb"] = None
        return data

    @staticmethod
    def match_catalog_prefix_filter(lab_id: str, prefix_segments: list[str]) -> dict[str, Any]:
        if not prefix_segments:
            return {"lab_id": lab_id}
        prefix_key = build_catalog_path_key(prefix_segments)
        return {
            "lab_id": lab_id,
            "catalog_path_key": {"$regex": f"^{prefix_key}(/|$)"},
        }

    async def build_tree(self, lab_id: str) -> dict[str, Any]:
        await self.ensure_active_lab(lab_id)
        segments = await TestCatalogSegmentDoc.find(
            {"lab_id": lab_id, "usage_count": {"$gt": 0}}
        ).to_list()

        cases = await TestCaseDoc.find(
            {"lab_id": lab_id, "is_deleted": False}
        ).to_list()

        root: dict[str, Any] = {"name": "", "path": [], "case_count": 0, "children": {}}

        def _ensure_node(parent: dict[str, Any], segment: str, path: list[str]) -> dict[str, Any]:
            children = parent.setdefault("children", {})
            if segment not in children:
                children[segment] = {
                    "name": segment,
                    "path": path,
                    "case_count": 0,
                    "children": {},
                }
            return children[segment]

        for seg_doc in segments:
            node = root
            path: list[str] = []
            for segment in seg_doc.parent_path + [seg_doc.segment_name]:
                path = path + [segment]
                node = _ensure_node(node, segment, path)

        for case in cases:
            node = root
            path: list[str] = []
            for segment in case.catalog_path or []:
                path = path + [segment]
                node = _ensure_node(node, segment, path)
            node["case_count"] = node.get("case_count", 0) + 1

        return {
            "lab_id": lab_id,
            "tree": _serialize_tree_node(root),
        }

    async def adjust_path_on_update(
        self,
        old_lab_id: str,
        old_path: list[str],
        new_lab_id: str,
        new_path: list[str],
    ) -> None:
        if old_lab_id == new_lab_id and old_path == new_path:
            return
        if old_path:
            await self.register_path(old_lab_id, old_path, delta=-1)
        await self.register_path(new_lab_id, new_path, delta=1)


def _serialize_tree_node(node: dict[str, Any]) -> dict[str, Any]:
    children_dict = node.get("children") or {}
    children_list = [
        _serialize_tree_node(child)
        for _, child in sorted(children_dict.items(), key=lambda item: item[0])
    ]
    return {
        "name": node.get("name", ""),
        "path": node.get("path", []),
        "case_count": node.get("case_count", 0),
        "children": children_list,
    }
