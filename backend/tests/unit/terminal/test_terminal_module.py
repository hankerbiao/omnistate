from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.terminal.api.routes import extract_token_from_query  # noqa: E402
from app.modules.terminal.schemas import TerminalClientMessage  # noqa: E402
from app.modules.terminal.service.terminal_service import (  # noqa: E402
    TerminalService,
    validate_session_capacity,
)


def test_extract_token_from_query_rejects_empty_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        extract_token_from_query(None)

    assert exc_info.value.status_code == 401


def test_extract_token_from_query_accepts_bearer_prefix() -> None:
    assert extract_token_from_query("Bearer abc.def") == "abc.def"


def test_validate_session_capacity_rejects_over_limit() -> None:
    with pytest.raises(ValueError, match="too many active terminal sessions"):
        validate_session_capacity(active_count=1, max_sessions=1)


def test_terminal_client_message_accepts_connect_payload() -> None:
    message = TerminalClientMessage.model_validate(
        {
            "type": "connect",
            "host": "10.0.0.8",
            "port": 22,
            "username": "root",
            "password": "secret",
        }
    )

    assert message.type == "connect"
    assert message.host == "10.0.0.8"
    assert message.port == 22
    assert message.username == "root"


def test_terminal_client_message_rejects_connect_without_host() -> None:
    with pytest.raises(ValidationError):
        TerminalClientMessage.model_validate(
            {
                "type": "connect",
                "port": 22,
                "username": "root",
                "password": "secret",
            }
        )


def test_terminal_service_requires_asyncssh_runtime() -> None:
    service = TerminalService()

    with pytest.raises(RuntimeError, match="asyncssh is required"):
        service._require_asyncssh(None)


def test_terminal_service_write_input_uses_write_and_drain() -> None:
    calls: list[tuple[str, str]] = []

    class FakeWriter:
        def write(self, data: str) -> None:
            calls.append(("write", data))

        async def drain(self) -> None:
            calls.append(("drain", ""))

    async def run() -> None:
        await TerminalService()._write_input(FakeWriter(), "ls\n")

    import asyncio

    asyncio.run(run())

    assert calls == [("write", "ls\n"), ("drain", "")]
