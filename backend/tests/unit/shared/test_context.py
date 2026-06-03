"""共享上下文单元测试。"""

from __future__ import annotations

from app.shared.context import (
    get_operation_context,
    get_trace_context,
    reset_context,
    set_operation_context,
    set_trace_context,
)
from app.shared.core.logger import _get_trace_extra


def test_get_trace_extra_includes_username():
    set_trace_context(request_id="req_user_001", client_ip="10.0.0.1")
    set_operation_context(user_id="u1", username="alice", role_ids=["ADMIN"])

    extra = _get_trace_extra()

    assert extra["request_id"] == "req_user_001"
    assert extra["user_id"] == "u1"
    assert extra["username"] == "alice"
    reset_context()


def test_reset_context_clears_trace_and_operation():
    set_trace_context(request_id="req_reset_001", client_ip="10.0.0.2")
    set_operation_context(user_id="u2", username="bob", role_ids=["ADMIN"])

    reset_context()

    assert get_trace_context().request_id == "-"
    assert get_trace_context().client_ip == "-"
    assert get_operation_context().actor_id == "-"
    assert get_operation_context().username == "-"
