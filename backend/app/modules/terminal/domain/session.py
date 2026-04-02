"""Terminal domain models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncssh


@dataclass(slots=True)
class TerminalSession:
    """In-memory terminal session state."""

    # 这里保存的是服务端内存态会话信息，不直接持久化到数据库。
    session_id: str
    user_id: str
    shell: str
    cwd: str
    cols: int
    rows: int
    host: str
    port: int
    username: str
    # AsyncSSH 连接与交互式 process 用于承载远端 shell 生命周期。
    ssh_connection: "asyncssh.SSHClientConnection | Any"
    ssh_process: "asyncssh.SSHClientProcess[str] | Any"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # 最近活跃时间用于空闲超时回收，读写输入都会刷新。
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
