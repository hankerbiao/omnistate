"""Terminal session store abstractions."""

from __future__ import annotations

from typing import Protocol

from app.modules.terminal.domain import TerminalSession


class TerminalSessionStore(Protocol):
    """抽象 terminal 会话存储，用于隔离进程内状态实现。"""

    def get(self, session_id: str) -> TerminalSession | None:
        ...

    def save(self, session: TerminalSession) -> None:
        ...

    def delete(self, session_id: str) -> TerminalSession | None:
        ...

    def count_user_sessions(self, user_id: str) -> int:
        ...


class InMemoryTerminalSessionStore:
    """默认的单进程内存会话存储。"""

    def __init__(self) -> None:
        self._sessions: dict[str, TerminalSession] = {}
        self._user_sessions: dict[str, set[str]] = {}

    def get(self, session_id: str) -> TerminalSession | None:
        return self._sessions.get(session_id)

    def save(self, session: TerminalSession) -> None:
        self._sessions[session.session_id] = session
        self._user_sessions.setdefault(session.user_id, set()).add(session.session_id)

    def delete(self, session_id: str) -> TerminalSession | None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return None

        user_sessions = self._user_sessions.get(session.user_id)
        if user_sessions:
            user_sessions.discard(session_id)
            if not user_sessions:
                self._user_sessions.pop(session.user_id, None)
        return session

    def count_user_sessions(self, user_id: str) -> int:
        return len(self._user_sessions.get(user_id, set()))
