# WebSocket Terminal Design

**Date:** 2026-04-01

## Goal

Provide a simple production-facing WebSocket communication module that allows the frontend to open an `xterm.js` shell window and execute arbitrary system commands through a backend-managed PTY session.

## Constraints

- Keep implementation simple and easy to maintain.
- Follow existing backend layering: `api -> service -> domain/schemas`.
- Integrate with existing JWT + RBAC model.
- Add a standalone frontend test page without introducing a router refactor.
- Support real terminal interaction instead of line-by-line fake command execution.

## Chosen Approach

Use `FastAPI WebSocket + PTY + subprocess.Popen` to create one shell process per WebSocket connection.

Why this approach:

- `xterm.js` expects a TTY-like stream and resize support.
- The implementation stays smaller than introducing a remote execution gateway.
- It supports interactive commands, shell state, and terminal control sequences.

## Backend Design

### Module Structure

- `backend/app/modules/terminal/api/routes.py`
- `backend/app/modules/terminal/service/terminal_service.py`
- `backend/app/modules/terminal/domain/session.py`
- `backend/app/modules/terminal/schemas/terminal.py`
- `backend/app/modules/terminal/api/__init__.py`
- `backend/app/modules/terminal/service/__init__.py`
- `backend/app/modules/terminal/domain/__init__.py`
- `backend/app/modules/terminal/schemas/__init__.py`
- `backend/app/modules/terminal/__init__.py`

### Responsibilities

`api`

- Expose `GET /api/v1/terminal/ws` as a WebSocket endpoint.
- Authenticate the connection using JWT from query string.
- Require authenticated users only. No extra terminal-specific RBAC gate in the current version.
- Own WebSocket lifecycle and translate failures into socket close codes.

`service`

- Create shell sessions.
- Manage PTY master/slave file descriptors and subprocess lifecycle.
- Bridge WebSocket messages to PTY input and PTY output back to WebSocket.
- Track sessions in memory for cleanup and timeout control.

`domain`

- Define `TerminalSession` runtime state.

`schemas`

- Define message payload shapes for terminal events.

### Session Model

Each connection owns one in-memory session:

- `session_id`
- `user_id`
- `shell`
- `cwd`
- `cols`
- `rows`
- `created_at`
- `last_active_at`
- `process_id`

No persistence is added in the first version.

### Message Protocol

Client to server:

```json
{"type":"input","data":"ls -la\r"}
{"type":"resize","cols":120,"rows":32}
{"type":"ping"}
```

Server to client:

```json
{"type":"session","session_id":"...","shell":"/bin/zsh","cwd":"..."}
{"type":"output","data":"..."}
{"type":"error","message":"..."}
{"type":"exit","code":0}
{"type":"pong"}
```

### Runtime Flow

1. Frontend opens WebSocket with JWT token.
2. Backend validates the JWT token and user status.
3. Backend opens PTY and starts configured shell.
4. Backend sends initial `session` event.
5. Frontend streams input to backend.
6. Backend writes bytes into PTY master fd.
7. Backend reads PTY output and streams it to frontend.
8. On disconnect or shell exit, backend closes session and kills process if needed.

### Configuration

Add minimal settings:

- `TERMINAL_SHELL`
- `TERMINAL_WORKDIR`
- `TERMINAL_IDLE_TIMEOUT_SEC`
- `TERMINAL_MAX_SESSIONS_PER_USER`

Defaults should be safe and simple:

- shell defaults to `/bin/zsh`
- workdir defaults to project root
- max sessions per user defaults to `1`

### Security Baseline

This feature intentionally allows arbitrary system commands, so the first version must still enforce a small hard boundary:

- JWT authentication is mandatory.
- Any authenticated user can connect in the current version.
- Shell executable is server-configured only.
- Working directory is server-configured only.
- Session count per user is limited.
- Idle sessions are closed.
- User input is logged as audit events at info level.

This is not a hardened bastion design. It is a minimal controlled internal capability.

## Frontend Design

### Scope

Create one standalone test page component:

- `frontend/src/components/TerminalPage.tsx`

Integrate it into existing `App.tsx` tab switching instead of adding router complexity.

### UI

- Toolbar with connect, disconnect, reconnect buttons
- Connection state
- Shell and working directory display
- Main `xterm.js` panel
- Small risk notice

### Frontend Behavior

- Read JWT token from existing storage.
- Convert API base URL to a WebSocket URL.
- On terminal input, send `input`.
- On resize, send `resize`.
- On backend output, write into terminal.
- On backend exit, disable input and show exit marker.

## Testing Strategy

Backend:

- Unit test WebSocket auth helpers and terminal service validation logic.
- Keep PTY integration lightly tested to avoid flaky CI expectations.

Frontend:

- Build-level verification only for this change.
- Manual terminal smoke test in browser.

## Non-Goals

- Multi-tenant terminal pooling
- Persistent session recovery
- Command allowlist
- File upload/download through terminal
- Terminal sharing / collaborative sessions

## Implementation Notes

- Prefer small synchronous PTY helpers wrapped by async bridge tasks.
- Keep terminal state in one service module first; do not over-split.
- Avoid database schema changes.
- Avoid introducing a frontend routing library only for this page.
