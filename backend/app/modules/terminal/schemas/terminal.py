"""Terminal websocket schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TerminalClientMessage(BaseModel):
    """Client-to-server terminal message."""

    type: Literal["connect", "input", "resize", "ping"]
    data: str | None = None
    cols: int | None = Field(default=None, ge=1)
    rows: int | None = Field(default=None, ge=1)
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    password: str | None = None

    @model_validator(mode="after")
    def validate_connect_payload(self) -> "TerminalClientMessage":
        if self.type != "connect":
            return self

        if not (self.host or "").strip():
            raise ValueError("host is required for connect")
        if self.port is None:
            raise ValueError("port is required for connect")
        if not (self.username or "").strip():
            raise ValueError("username is required for connect")
        if self.password is None:
            raise ValueError("password is required for connect")

        self.host = self.host.strip()
        self.username = self.username.strip()
        return self


class TerminalServerMessage(BaseModel):
    """Server-to-client terminal message."""

    type: Literal["session", "output", "error", "exit", "pong"]
    data: str | None = None
    message: str | None = None
    session_id: str | None = None
    shell: str | None = None
    cwd: str | None = None
    code: int | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
