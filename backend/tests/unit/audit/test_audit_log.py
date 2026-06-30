"""AuditLogMiddleware 单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.middleware.audit_log import AuditLogMiddleware


# ═══════════════════════════════════════════════════════════════════════
#  _redact
# ═══════════════════════════════════════════════════════════════════════

def test_redact_replaces_password():
    mw = AuditLogMiddleware(app=MagicMock())
    result = mw._redact({"username": "admin", "password": "secret123"})
    assert result["username"] == "admin"
    assert result["password"] == "***REDACTED***"


def test_redact_replaces_api_key():
    mw = AuditLogMiddleware(app=MagicMock())
    result = mw._redact({"api_key": "sk-xxx", "data": "ok"})
    assert result["api_key"] == "***REDACTED***"
    assert result["data"] == "ok"


def test_redact_handles_nested_dicts():
    mw = AuditLogMiddleware(app=MagicMock())
    result = mw._redact({
        "user": {"name": "admin", "password": "pw", "token": "tk"},
        "action": "login",
    })
    assert result["user"]["password"] == "***REDACTED***"
    assert result["user"]["token"] == "***REDACTED***"
    assert result["user"]["name"] == "admin"
    assert result["action"] == "login"


def test_redact_preserves_non_sensitive_fields():
    mw = AuditLogMiddleware(app=MagicMock())
    result = mw._redact({"title": "用例标题", "priority": "P1", "tags": ["a", "b"]})
    assert result == {"title": "用例标题", "priority": "P1", "tags": ["a", "b"]}


# ═══════════════════════════════════════════════════════════════════════
#  _parse_body
# ═══════════════════════════════════════════════════════════════════════

def test_parse_body_valid_json():
    mw = AuditLogMiddleware(app=MagicMock())
    result = mw._parse_body(b'{"title": "test", "password": "secret"}')
    assert result is not None
    assert result["title"] == "test"
    assert result["password"] == "***REDACTED***"


def test_parse_body_empty():
    mw = AuditLogMiddleware(app=MagicMock())
    assert mw._parse_body(b"") is None


def test_parse_body_invalid_json():
    mw = AuditLogMiddleware(app=MagicMock())
    assert mw._parse_body(b"not json") is None


def test_parse_body_too_large():
    mw = AuditLogMiddleware(app=MagicMock())
    large = b'{"x": "' + b"A" * 5000 + b'"}'
    assert mw._parse_body(large) is None


def test_parse_body_non_dict_json():
    mw = AuditLogMiddleware(app=MagicMock())
    result = mw._parse_body(b'["a", "b"]')
    assert result is not None
    assert "_raw" in result


# ═══════════════════════════════════════════════════════════════════════
#  _infer_resource
# ═══════════════════════════════════════════════════════════════════════

def test_infer_resource_test_case():
    mw = AuditLogMiddleware(app=MagicMock())
    rtype, rid = mw._infer_resource("/api/v1/test-cases/TC-001", {})
    assert rtype == "test_case"
    assert rid == "TC-001"


def test_infer_resource_requirement():
    mw = AuditLogMiddleware(app=MagicMock())
    rtype, rid = mw._infer_resource("/api/v1/requirements/TR-2026-001", {})
    assert rtype == "requirement"
    assert rid == "TR-2026-001"


def test_infer_resource_no_id():
    mw = AuditLogMiddleware(app=MagicMock())
    rtype, rid = mw._infer_resource("/api/v1/test-cases", {})
    assert rtype == "test_case"
    assert rid is None


def test_infer_resource_with_subaction():
    mw = AuditLogMiddleware(app=MagicMock())
    rtype, rid = mw._infer_resource("/api/v1/test-cases/TC-001/transition", {})
    assert rtype == "test_case"
    assert rid == "TC-001"  # transition 被排除


def test_infer_resource_unknown_path():
    mw = AuditLogMiddleware(app=MagicMock())
    rtype, rid = mw._infer_resource("/api/v1/unknown/path", {})
    assert rtype == "unknown"
    assert rid is None


def test_infer_resource_ai_endpoint():
    mw = AuditLogMiddleware(app=MagicMock())
    rtype, rid = mw._infer_resource("/api/v1/ai/generate-cases", {})
    assert rtype == "ai_generate_cases"


# ═══════════════════════════════════════════════════════════════════════
#  _infer_action
# ═══════════════════════════════════════════════════════════════════════

def test_infer_action_post():
    mw = AuditLogMiddleware(app=MagicMock())
    assert mw._infer_action("POST", "/api/v1/test-cases") == "create"


def test_infer_action_put():
    mw = AuditLogMiddleware(app=MagicMock())
    assert mw._infer_action("PUT", "/api/v1/test-cases/TC-001") == "update"


def test_infer_action_delete():
    mw = AuditLogMiddleware(app=MagicMock())
    assert mw._infer_action("DELETE", "/api/v1/test-cases/TC-001") == "delete"


def test_infer_action_dispatch():
    mw = AuditLogMiddleware(app=MagicMock())
    assert mw._infer_action("POST", "/api/v1/execution-plans/items/EPI-1/dispatch") == "dispatch"


def test_infer_action_ai_polish():
    mw = AuditLogMiddleware(app=MagicMock())
    assert mw._infer_action("POST", "/api/v1/ai/polish") == "ai_polish"


def test_infer_action_ai_generate():
    mw = AuditLogMiddleware(app=MagicMock())
    assert mw._infer_action("POST", "/api/v1/ai/generate-cases") == "ai_generate_cases"


def test_infer_action_transition():
    mw = AuditLogMiddleware(app=MagicMock())
    assert mw._infer_action("POST", "/api/v1/work-items/WI-1/transition") == "transition"


# ═══════════════════════════════════════════════════════════════════════
#  AuditLogDoc model
# ═══════════════════════════════════════════════════════════════════════

def test_audit_log_collection_name():
    from app.modules.audit.repository.models.audit_log import AuditLogDoc
    assert AuditLogDoc.Settings.name == "audit_logs"


def test_audit_log_has_ttl_index():
    from app.modules.audit.repository.models.audit_log import AuditLogDoc
    indexes = AuditLogDoc.Settings.indexes
    ttl = indexes[-1]
    assert ttl.document.get("expireAfterSeconds") == 90 * 24 * 60 * 60


def test_audit_log_has_compound_indexes():
    from app.modules.audit.repository.models.audit_log import AuditLogDoc
    indexes = AuditLogDoc.Settings.indexes
    # 应该有 actor_id + created_at 复合索引
    found_actor_created = False
    found_resource = False
    for idx in indexes:
        keys = list(idx.document.get("key", {}).keys())
        if keys == ["actor_id", "created_at"]:
            found_actor_created = True
        if keys == ["resource_type", "resource_id"]:
            found_resource = True
    assert found_actor_created
    assert found_resource


# ═══════════════════════════════════════════════════════════════════════
#  _write_audit_log skips unauthenticated requests
# ═══════════════════════════════════════════════════════════════════════

async def test_write_audit_log_skips_unauthenticated():
    """actor_id 为默认值 '-' 时跳过写入。"""
    mw = AuditLogMiddleware(app=MagicMock())

    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/test-cases"
    mock_request.method = "POST"
    mock_request.query_params = {}
    mock_request.path_params = {}

    mock_response = MagicMock()
    mock_response.status_code = 201

    with patch("app.shared.middleware.audit_log.get_operation_context") as get_ctx:
        ctx = MagicMock(actor_id="-", username="-", role_ids=[])
        get_ctx.return_value = ctx

        with patch("app.shared.middleware.audit_log.get_trace_context") as get_trace:
            trace = MagicMock(request_id="req-1", client_ip="127.0.0.1")
            get_trace.return_value = trace

            with patch("app.modules.audit.repository.models.audit_log.AuditLogDoc") as MockDoc:
                await mw._write_audit_log(mock_request, mock_response, b'{"title":"x"}', 50)
                MockDoc.assert_not_called()


async def test_write_audit_log_writes_for_authenticated():
    """有 actor_id 时正常写入。"""
    mw = AuditLogMiddleware(app=MagicMock())

    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/test-cases"
    mock_request.method = "POST"
    mock_request.query_params = {}
    mock_request.path_params = {}

    mock_response = MagicMock()
    mock_response.status_code = 201

    mock_doc_instance = MagicMock()
    mock_doc_instance.insert = AsyncMock()

    with patch("app.shared.middleware.audit_log.get_operation_context") as get_ctx:
        ctx = MagicMock(actor_id="user-001", username="张三", role_ids=["ADMIN"])
        get_ctx.return_value = ctx

        with patch("app.shared.middleware.audit_log.get_trace_context") as get_trace:
            trace = MagicMock(request_id="req-abc", client_ip="10.0.0.1")
            get_trace.return_value = trace

            with patch("app.modules.audit.repository.models.audit_log.AuditLogDoc") as MockDoc:
                MockDoc.return_value = mock_doc_instance
                await mw._write_audit_log(mock_request, mock_response, b'{"title":"test"}', 120)

                MockDoc.assert_called_once()
                call_kwargs = MockDoc.call_args.kwargs
                assert call_kwargs["actor_id"] == "user-001"
                assert call_kwargs["username"] == "张三"
                assert call_kwargs["method"] == "POST"
                assert call_kwargs["status_code"] == 201
                assert call_kwargs["duration_ms"] == 120
                assert call_kwargs["resource_type"] == "test_case"
                assert call_kwargs["action"] == "create"
                assert call_kwargs["request_body"]["title"] == "test"

                mock_doc_instance.insert.assert_awaited_once()
