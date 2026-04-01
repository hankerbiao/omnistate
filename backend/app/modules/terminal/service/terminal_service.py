"""Terminal SSH session service."""
from __future__ import annotations

import asyncio
import contextlib
import socket
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket

from app.modules.terminal.domain import TerminalSession
from app.modules.terminal.schemas import TerminalClientMessage, TerminalServerMessage
from app.shared.core.logger import log as logger
from app.shared.db.config import settings

try:
    import paramiko
except ImportError:  # pragma: no cover - runtime dependency path
    paramiko = None


def validate_session_capacity(active_count: int, max_sessions: int) -> None:
    """Reject new sessions when the per-user quota is reached."""
    if active_count >= max_sessions:
        raise ValueError("too many active terminal sessions")


class TerminalService:
    """Manage SSH-backed terminal sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, TerminalSession] = {}
        self._user_sessions: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        user_id: str,
        connect_message: TerminalClientMessage,
        cols: int = 120,
        rows: int = 32,
    ) -> TerminalSession:
        """Create and register one SSH-backed shell session."""
        async with self._lock:
            active_count = len(self._user_sessions.get(user_id, set()))
            validate_session_capacity(active_count, settings.TERMINAL_MAX_SESSIONS_PER_USER)

            ssh_client, ssh_channel = await asyncio.to_thread(
                self._open_ssh_session,
                connect_message.host or "",
                int(connect_message.port or 22),
                connect_message.username or "",
                connect_message.password or "",
                cols,
                rows,
            )

            session = TerminalSession(
                session_id=uuid.uuid4().hex,
                user_id=user_id,
                shell="ssh",
                cwd=f"{connect_message.username}@{connect_message.host}",
                cols=cols,
                rows=rows,
                host=connect_message.host or "",
                port=int(connect_message.port or 22),
                username=connect_message.username or "",
                ssh_client=ssh_client,
                ssh_channel=ssh_channel,
            )
            self._sessions[session.session_id] = session
            self._user_sessions.setdefault(user_id, set()).add(session.session_id)
            logger.info(
                "terminal ssh session created: "
                f"user_id={user_id}, session_id={session.session_id}, "
                f"target={session.username}@{session.host}:{session.port}"
            )
            return session

    async def close_session(self, session_id: str) -> None:
        """Close a session and release resources."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if not session:
                return

            user_sessions = self._user_sessions.get(session.user_id)
            if user_sessions:
                user_sessions.discard(session_id)
                if not user_sessions:
                    self._user_sessions.pop(session.user_id, None)

        await asyncio.to_thread(self._shutdown_ssh_session, session)
        logger.info(
            "terminal ssh session closed: "
            f"user_id={session.user_id}, session_id={session.session_id}, "
            f"target={session.username}@{session.host}:{session.port}"
        )

    async def handle_websocket(self, websocket: WebSocket, user_id: str, cols: int = 120, rows: int = 32) -> None:
        """Run the terminal websocket bridge for one connection."""
        connect_message = await self._receive_connect_message(websocket)
        session = await self.create_session(
            user_id=user_id,
            connect_message=connect_message,
            cols=cols,
            rows=rows,
        )
        await websocket.send_json(
            TerminalServerMessage(
                type="session",
                session_id=session.session_id,
                shell=session.shell,
                cwd=session.cwd,
                host=session.host,
                port=session.port,
                username=session.username,
            ).model_dump(exclude_none=True)
        )

        pump_task = asyncio.create_task(self._pump_ssh_output(websocket, session))
        receive_task = asyncio.create_task(self._receive_client_messages(websocket, session))
        idle_task = asyncio.create_task(self._watch_idle_timeout(websocket, session))

        done, pending = await asyncio.wait(
            {pump_task, receive_task, idle_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        for task in done:
            with contextlib.suppress(Exception):
                await task

        exit_code = self._read_exit_code(session)
        if exit_code is not None and websocket.client_state.name == "CONNECTED":
            await websocket.send_json(
                TerminalServerMessage(type="exit", code=int(exit_code)).model_dump(exclude_none=True)
            )

        await self.close_session(session.session_id)

    async def _receive_connect_message(self, websocket: WebSocket) -> TerminalClientMessage:
        payload = await websocket.receive_json()
        message = TerminalClientMessage.model_validate(payload)
        if message.type != "connect":
            raise ValueError("first terminal message must be connect")
        return message

    async def _pump_ssh_output(self, websocket: WebSocket, session: TerminalSession) -> None:
        """Read SSH output and forward it to the websocket."""
        while True:
            if session.ssh_channel.closed:
                return

            chunk = await asyncio.to_thread(self._read_channel_chunk, session.ssh_channel)
            if not chunk:
                if session.ssh_channel.exit_status_ready():
                    return
                await asyncio.sleep(0.02)
                continue

            session.last_active_at = datetime.now(timezone.utc)
            await websocket.send_json(
                TerminalServerMessage(
                    type="output",
                    data=chunk.decode("utf-8", errors="ignore"),
                ).model_dump(exclude_none=True)
            )

    async def _receive_client_messages(self, websocket: WebSocket, session: TerminalSession) -> None:
        """Handle websocket input and control events."""
        while True:
            payload = await websocket.receive_json()
            message = TerminalClientMessage.model_validate(payload)
            session.last_active_at = datetime.now(timezone.utc)

            if message.type == "input":
                data = message.data or ""
                if data:
                    await asyncio.to_thread(session.ssh_channel.send, data)
                continue

            if message.type == "resize":
                cols = message.cols or session.cols
                rows = message.rows or session.rows
                await asyncio.to_thread(session.ssh_channel.resize_pty, width=cols, height=rows)
                session.cols = cols
                session.rows = rows
                continue

            if message.type == "ping":
                await websocket.send_json(TerminalServerMessage(type="pong").model_dump())
                continue

            await websocket.send_json(
                TerminalServerMessage(type="error", message="session already connected").model_dump()
            )

    async def _watch_idle_timeout(self, websocket: WebSocket, session: TerminalSession) -> None:
        """Close idle sessions after the configured timeout."""
        timeout_seconds = max(1, int(settings.TERMINAL_IDLE_TIMEOUT_SEC))
        while True:
            await asyncio.sleep(5)
            if session.ssh_channel.closed or session.ssh_channel.exit_status_ready():
                return

            idle_seconds = (datetime.now(timezone.utc) - session.last_active_at).total_seconds()
            if idle_seconds < timeout_seconds:
                continue

            logger.warning(
                "terminal session idle timeout reached: "
                f"user_id={session.user_id}, session_id={session.session_id}, "
                f"idle_seconds={idle_seconds:.0f}"
            )
            await websocket.send_json(
                TerminalServerMessage(
                    type="error",
                    message=f"terminal session idle for more than {timeout_seconds} seconds",
                ).model_dump(exclude_none=True)
            )
            await asyncio.to_thread(self._shutdown_ssh_session, session)
            return

    @staticmethod
    def _open_ssh_session(
        host: str,
        port: int,
        username: str,
        password: str,
        cols: int,
        rows: int,
    ) -> tuple["paramiko.SSHClient", "paramiko.Channel"]:
        if paramiko is None:
            raise RuntimeError("paramiko is required to use SSH terminal sessions")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10,
                banner_timeout=10,
                auth_timeout=10,
            )
            channel = client.invoke_shell(term="xterm-256color", width=cols, height=rows)
            channel.settimeout(0.2)
            return client, channel
        except Exception:
            with contextlib.suppress(Exception):
                client.close()
            raise

    @staticmethod
    def _shutdown_ssh_session(session: TerminalSession) -> None:
        with contextlib.suppress(Exception):
            if not session.ssh_channel.closed:
                session.ssh_channel.close()
        with contextlib.suppress(Exception):
            session.ssh_client.close()

    @staticmethod
    def _read_channel_chunk(channel: "paramiko.Channel") -> bytes:
        try:
            return channel.recv(4096)
        except socket.timeout:
            return b""

    @staticmethod
    def _read_exit_code(session: TerminalSession) -> int | None:
        with contextlib.suppress(Exception):
            if session.ssh_channel.exit_status_ready():
                return int(session.ssh_channel.recv_exit_status())
        return None
