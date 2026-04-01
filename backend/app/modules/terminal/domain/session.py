"""Terminal domain models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import paramiko


@dataclass(slots=True)
class TerminalSession:
    """In-memory terminal session state."""

    session_id: str
    user_id: str
    shell: str
    cwd: str
    cols: int
    rows: int
    host: str
    port: int
    username: str
    ssh_client: "paramiko.SSHClient"
    ssh_channel: "paramiko.Channel"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
