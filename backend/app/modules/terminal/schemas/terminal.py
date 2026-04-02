"""Terminal websocket schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TerminalClientMessage(BaseModel):
    """Client-to-server terminal message."""

    # connect 用于首次建连；其余消息都复用已建立的 session。
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
        # 只有首次 connect 需要校验 SSH 连接参数，其它消息只携带局部字段。
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

    # session/output/error/exit/pong 分别对应建连成功、终端输出、错误、退出、保活响应。
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
