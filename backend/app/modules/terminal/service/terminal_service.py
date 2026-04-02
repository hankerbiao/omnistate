"""Terminal SSH session service."""
from __future__ import annotations

import asyncio
import contextlib
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

from app.modules.terminal.domain import TerminalSession
from app.modules.terminal.schemas import TerminalClientMessage, TerminalServerMessage
from app.shared.core.logger import log as logger
from app.shared.db.config import settings

try:
    import asyncssh
except ImportError:  # pragma: no cover - runtime dependency path
    asyncssh = None


def validate_session_capacity(active_count: int, max_sessions: int) -> None:
    """Reject new sessions when the per-user quota is reached."""
    # 每个用户的并发终端数做硬限制，避免长期占用 SSH/PTY 资源。
    if active_count >= max_sessions:
        raise ValueError("too many active terminal sessions")


class TerminalService:
    """Manage SSH-backed terminal sessions."""

    def __init__(self) -> None:
        # 会话只放内存里，进程重启后自然失效。
        self._sessions: dict[str, TerminalSession] = {}
        self._user_sessions: dict[str, set[str]] = {}
        # 创建/关闭会话时加锁，避免并发请求下出现计数不一致。
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

            ssh_connection, ssh_process = await self._open_ssh_session(
                host=connect_message.host or "",
                port=int(connect_message.port or 22),
                username=connect_message.username or "",
                password=connect_message.password or "",
                cols=cols,
                rows=rows,
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
                ssh_connection=ssh_connection,
                ssh_process=ssh_process,
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

        await self._shutdown_ssh_session(session)
        logger.info(
            "terminal ssh session closed: "
            f"user_id={session.user_id}, session_id={session.session_id}, "
            f"target={session.username}@{session.host}:{session.port}"
        )

    async def handle_websocket(self, websocket: WebSocket, user_id: str, cols: int = 120, rows: int = 32) -> None:
        """Run the terminal websocket bridge for one connection."""
        # 协议约定第一条消息必须是 connect，用它携带 SSH 目标信息。
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

        # 任一方向结束都认为会话需要收尾，其余任务统一取消。
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
            if self._process_exited(session.ssh_process):
                return

            chunk = await self._read_output(session.ssh_process)
            if not chunk:
                return

            session.last_active_at = datetime.now(timezone.utc)
            await websocket.send_json(
                TerminalServerMessage(
                    type="output",
                    data=chunk,
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
                    # 原样转发终端输入，控制字符也通过同一通道传递。
                    await self._write_input(session.ssh_process.stdin, data)
                continue

            if message.type == "resize":
                cols = message.cols or session.cols
                rows = message.rows or session.rows
                # 前端窗口变化后同步调整远端 PTY 尺寸，避免换行和光标错位。
                self._resize_pty(session.ssh_process, cols, rows)
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
            if self._process_exited(session.ssh_process):
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
            # 先主动关闭 SSH，后续 websocket 收尾逻辑会统一回收 session 记录。
            await self._shutdown_ssh_session(session)
            return

    async def _open_ssh_session(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        cols: int,
        rows: int,
    ) -> tuple[Any, Any]:
        asyncssh_module = self._require_asyncssh(asyncssh)
        connect_kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "connect_timeout": 10,
            "login_timeout": 10,
            "client_keys": None,
            "agent_path": None,
        }
        known_hosts = getattr(settings, "TERMINAL_SSH_KNOWN_HOSTS", None)
        if known_hosts:
            connect_kwargs["known_hosts"] = known_hosts

        connection = await asyncssh_module.connect(**connect_kwargs)
        try:
            # 建立交互式 shell，而不是执行单次命令。
            process = await connection.create_process(
                term_type="xterm-256color",
                term_size=(cols, rows),
                encoding="utf-8",
            )
            return connection, process
        except Exception:
            connection.close()
            with contextlib.suppress(Exception):
                await connection.wait_closed()
            raise

    @staticmethod
    def _require_asyncssh(module: Any) -> Any:
        if module is None:
            raise RuntimeError("asyncssh is required to use SSH terminal sessions")
        return module

    @staticmethod
    async def _write_input(writer: Any, data: str) -> None:
        writer.write(data)
        drain = getattr(writer, "drain", None)
        if callable(drain):
            await drain()

    @staticmethod
    def _resize_pty(process: Any, cols: int, rows: int) -> None:
        channel = getattr(process, "channel", None)
        if channel is None:
            return

        for method_name in ("change_terminal_size", "set_terminal_size"):
            method = getattr(channel, method_name, None)
            if callable(method):
                method(cols, rows, 0, 0)
                return

    @staticmethod
    async def _read_output(process: Any) -> str:
        stdout = getattr(process, "stdout", None)
        if stdout is None:
            return ""

        chunk = await stdout.read(4096)
        if isinstance(chunk, bytes):
            return chunk.decode("utf-8", errors="ignore")
        return chunk or ""

    @staticmethod
    def _process_exited(process: Any) -> bool:
        return bool(getattr(process, "exit_status", None) is not None or getattr(process, "returncode", None) is not None)

    @staticmethod
    async def _shutdown_ssh_session(session: TerminalSession) -> None:
        process = session.ssh_process
        connection = session.ssh_connection

        with contextlib.suppress(Exception):
            stdin = getattr(process, "stdin", None)
            if stdin is not None:
                stdin.close()

        with contextlib.suppress(Exception):
            process.close()

        with contextlib.suppress(Exception):
            wait_closed = getattr(process, "wait_closed", None)
            if callable(wait_closed):
                await wait_closed()

        with contextlib.suppress(Exception):
            connection.close()

        with contextlib.suppress(Exception):
            wait_closed = getattr(connection, "wait_closed", None)
            if callable(wait_closed):
                await wait_closed()

    @staticmethod
    def _read_exit_code(session: TerminalSession) -> int | None:
        process = session.ssh_process
        for attr in ("exit_status", "returncode"):
            value = getattr(process, attr, None)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None
