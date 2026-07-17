"""共享脱敏工具单元测试。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.middleware.request_logging import RequestLoggingMiddleware
from app.shared.security.redaction import (
    REDACTED,
    is_sensitive_field,
    redact_dict,
    redact_headers,
    redact_json_string,
    redact_query_params,
    redact_query_string,
    safe_body_preview,
    should_skip_body_logging,
)


# ═══════════════════════════════════════════════════════════════════════
#  redact_dict
# ═══════════════════════════════════════════════════════════════════════

def test_redact_dict_top_level():
    assert redact_dict({"password": "hunter2"}) == {"password": REDACTED}


def test_redact_dict_nested():
    data = {"user": {"name": "a", "token": "t"}, "scope": "read"}
    out = redact_dict(data)
    assert out["user"]["token"] == REDACTED
    assert out["user"]["name"] == "a"
    assert out["scope"] == "read"


def test_redact_dict_list_values():
    data = {"keys": [{"api_key": "k1"}, {"api_key": "k2"}]}
    out = redact_dict(data)
    assert out["keys"][0]["api_key"] == REDACTED
    assert out["keys"][1]["api_key"] == REDACTED


def test_redact_dict_preserves_non_sensitive():
    data = {"title": "用例", "tags": ["x", "y"]}
    assert redact_dict(data) == data


def test_redact_dict_case_insensitive_keys():
    assert redact_dict({"API_KEY": "secret"}) == {"API_KEY": REDACTED}


def test_redact_dict_handles_non_dict_scalar():
    assert redact_dict("plain") == "plain"
    assert redact_dict(123) == 123


# ═══════════════════════════════════════════════════════════════════════
#  redact_json_string
# ═══════════════════════════════════════════════════════════════════════

def test_redact_json_string_redacts_password():
    out = redact_json_string('{"user_id": "u1", "password": "my-secret-pw"}')
    assert '"password": "***REDACTED***"' in out
    assert "my-secret-pw" not in out
    assert '"user_id": "u1"' in out


def test_redact_json_string_unparseable_is_redacted():
    assert redact_json_string("not json") == "<unparseable-body-redacted>"


def test_redact_json_string_truncates():
    big = '{"note": "' + "A" * 5000 + '"}'
    out = redact_json_string(big, max_len=50)
    assert out.endswith("...(truncated)")


# ═══════════════════════════════════════════════════════════════════════
#  redact_query_string / redact_headers
# ═══════════════════════════════════════════════════════════════════════

def test_redact_query_string():
    q = redact_query_string("token=abc&scope=read")
    assert "token=***REDACTED***" in q
    assert "scope=read" in q


def test_redact_query_string_decodes_keys_and_preserves_duplicates():
    q = redact_query_string("access%5Ftoken=abc&tag=a&tag=b")
    assert "access_token=***REDACTED***" in q
    assert q.count("tag=") == 2


def test_redact_query_params():
    assert redact_query_params({"api_key": "secret", "page": "2"}) == {
        "api_key": REDACTED,
        "page": "2",
    }


def test_redact_query_string_empty():
    assert redact_query_string("") == ""


def test_redact_headers():
    headers = {"Authorization": "Bearer x", "X-Request-ID": "r1"}
    out = redact_headers(headers)
    assert out["Authorization"] == REDACTED
    assert out["X-Request-ID"] == "r1"


# ═══════════════════════════════════════════════════════════════════════
#  should_skip_body_logging
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "path",
    ["/api/v1/auth/login", "/openapi/v1/oauth/token"],
)
def test_should_skip_body_logging_sensitive(path):
    assert should_skip_body_logging(path) is True


def test_should_skip_body_logging_normal():
    assert should_skip_body_logging("/api/v1/test-cases") is False


# ═══════════════════════════════════════════════════════════════════════
#  safe_body_preview / RequestLoggingMiddleware compatibility entry
# ═══════════════════════════════════════════════════════════════════════

class _FakeRequest:
    def __init__(self, method, content_type, body, path="/x", query=""):
        self.method = method
        self.headers = {"content-type": content_type}
        self.url = SimpleNamespace(path=path, query=query)
        self._body = body.encode("utf-8") if isinstance(body, str) else body

    async def body(self):
        return self._body


async def test_safe_body_preview_redacts_json_body():
    req = _FakeRequest("POST", "application/json", '{"user_id": "u1", "password": "secret123"}')
    preview = await safe_body_preview(req)
    assert "***REDACTED***" in preview
    assert "secret123" not in preview


async def test_safe_body_preview_omits_non_json_body():
    req = _FakeRequest("POST", "application/x-www-form-urlencoded", "password=secret123")
    preview = await safe_body_preview(req)
    assert preview == "<application/x-www-form-urlencoded body omitted>"
    assert "secret123" not in preview


async def test_request_logging_skips_sensitive_path_body():
    req = _FakeRequest(
        "POST", "application/json", '{"user_id": "u1", "password": "p"}', path="/api/v1/auth/login"
    )
    preview = await RequestLoggingMiddleware._read_body_preview(req)
    assert preview == "<body redacted>"


async def test_request_logging_get_has_no_body():
    req = _FakeRequest("GET", "application/json", '{"x": 1}')
    assert await RequestLoggingMiddleware._read_body_preview(req) == "-"


def test_is_sensitive_field_helper():
    assert is_sensitive_field("client_secret")
    assert is_sensitive_field("WEBHOOK_SECRET")
    assert not is_sensitive_field("title")
