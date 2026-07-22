from __future__ import annotations

import pytest

from scripts.init.sync_rbac import _validated_permission_ids


def test_permission_validation_rejects_unknown_codes() -> None:
    with pytest.raises(ValueError, match="未定义的权限码"):
        _validated_permission_ids(["users:read", "unknown:permission"])


def test_permission_validation_deduplicates_known_codes() -> None:
    assert _validated_permission_ids(["users:read", "users:read"]) == ["users:read"]
