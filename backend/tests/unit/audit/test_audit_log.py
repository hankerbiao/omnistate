"""AuditLogMiddleware 单元测试。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.shared.middleware.audit_log import AuditLogMiddleware
from app.shared.security.redaction import REDACTED, redact_dict, redact_query_params


# ═══════════════════════════════════════════════════════════════════════
#  _redact
# ═══════════════════════════════════════════════════════════════════════

def test_shared_redaction_covers_audit_sensitive_fields():
    """共享脱敏能力覆盖审计持久化所需的密码变体与配置值。"""
    result = redact_dict({
        "old_password": "a1",
        "new_password": "b2",
        "current_password": "c3",
        "config_key": "ai.api_key",
        "config_value": "sk-real-secret",
        "normal": "keep",
    })
    assert result["old_password"] == REDACTED
    assert result["new_password"] == REDACTED
    assert result["current_password"] == REDACTED
    assert result["config_value"] == REDACTED
    assert result["config_key"] == "ai.api_key"
    assert result["normal"] == "keep"


def test_shared_query_redaction_covers_audit_params():
    result = redact_query_params({"token": "abc", "api_key": "sk-x", "page": "2"})
    assert result == {"token": REDACTED, "api_key": REDACTED, "page": "2"}


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


async def test_write_audit_log_skips_body_for_system_configs_and_redacts_query():
    """系统配置路径不记录 body（避免 config_value 明文入库），查询敏感参数脱敏。"""
    mw = AuditLogMiddleware(app=MagicMock())

    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/system-configs/ai.api_key"
    mock_request.method = "PUT"
    mock_request.query_params = {"token": "leak-me"}
    mock_request.path_params = {}

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_doc_instance = MagicMock()
    mock_doc_instance.insert = AsyncMock()

    with patch("app.shared.middleware.audit_log.get_operation_context") as get_ctx:
        ctx = MagicMock(actor_id="user-001", username="张三", role_ids=["ADMIN"])
        get_ctx.return_value = ctx

        with patch("app.shared.middleware.audit_log.get_trace_context") as get_trace:
            trace = MagicMock(request_id="req-cfg", client_ip="10.0.0.1")
            get_trace.return_value = trace

            with patch("app.modules.audit.repository.models.audit_log.AuditLogDoc") as MockDoc:
                MockDoc.return_value = mock_doc_instance
                body = b'{"config_key": "ai.api_key", "config_value": "sk-real-secret"}'
                await mw._write_audit_log(mock_request, mock_response, body, 30)

                MockDoc.assert_called_once()
                call_kwargs = MockDoc.call_args.kwargs
                # 系统配置路径不应记录请求体
                assert call_kwargs["request_body"] is None
                # 查询串敏感参数应被脱敏
                assert call_kwargs["query_params"]["token"] == "***REDACTED***"

def test_audit_log_actor_type_default():
    """AuditLogDoc 的 actor_type 默认值为 human。"""
    from app.modules.audit.repository.models.audit_log import AuditLogDoc
    assert AuditLogDoc.model_fields["actor_type"].default == "human"

