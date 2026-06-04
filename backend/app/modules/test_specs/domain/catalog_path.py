"""Catalog path segment normalization and validation."""
from __future__ import annotations

import re

from app.modules.test_specs.domain.exceptions import CatalogPathValidationError

_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x1f\x7f]")


def normalize_catalog_segment(raw: str) -> str:
    """Normalize a single L2+ catalog path segment (not Lab code/name).

    Rules:
    - strip whitespace
    - reject empty strings
    - reject path separators and control characters
    - lowercase for storage/deduplication (case-insensitive segment matching)
    """
    if raw is None:
        raise CatalogPathValidationError("路径段不能为空")

    segment = str(raw).strip()
    if not segment:
        raise CatalogPathValidationError("路径段不能为空")

    if "/" in segment or "\\" in segment:
        raise CatalogPathValidationError("路径段不能包含 / 或 \\")

    if _CONTROL_CHAR_PATTERN.search(segment):
        raise CatalogPathValidationError("路径段包含非法控制字符")

    return segment.lower()


def normalize_catalog_path(segments: list[str]) -> list[str]:
    """Normalize a full catalog path (>= 1 segment)."""
    if not segments:
        raise CatalogPathValidationError("目录路径至少需要 1 个段")

    return [normalize_catalog_segment(segment) for segment in segments]


def build_catalog_path_key(catalog_path: list[str]) -> str:
    """Build a query key from normalized path segments."""
    normalized = normalize_catalog_path(catalog_path)
    return "/".join(normalized)
