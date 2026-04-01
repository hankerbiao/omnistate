# SSH Terminal Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SSH-based remote terminal sessions so users can enter host credentials in the frontend, save them in browser storage, and open a remote shell through the existing terminal page.

**Architecture:** Keep the existing websocket entrypoint, but change the terminal protocol so the browser sends an explicit `connect` message with SSH parameters after the websocket opens. The backend terminal service will create an SSH-backed session instead of a local PTY process, then bridge SSH channel I/O to the websocket while preserving resize, idle timeout, and session metadata reporting.

**Tech Stack:** FastAPI, Pydantic, WebSocket, Paramiko, React 19, TypeScript, xterm.js, localStorage

---

### Task 1: Extend terminal protocol for SSH bootstrap

**Files:**
- Modify: `backend/app/modules/terminal/schemas/terminal.py`
- Modify: `frontend/src/components/TerminalPage.tsx`
- Test: `backend/tests/unit/terminal/test_terminal_module.py`

- [ ] Add a `connect` client message type with SSH fields: `host`, `port`, `username`, `password`.
- [ ] Keep existing `input`, `resize`, and `ping` messages unchanged for the active session phase.
- [ ] Extend server session metadata to describe the remote target that was connected.
- [ ] Add schema-level validation tests for missing or invalid SSH fields.

### Task 2: Implement SSH-backed terminal session lifecycle

**Files:**
- Modify: `backend/app/modules/terminal/service/terminal_service.py`
- Modify: `backend/app/modules/terminal/domain/session.py`
- Modify: `backend/app/modules/terminal/api/routes.py`
- Test: `backend/tests/unit/terminal/test_terminal_module.py`

- [ ] Refactor terminal session creation so websocket handling waits for a `connect` message before allocating a session.
- [ ] Add SSH connection creation with Paramiko, remote PTY allocation, shell invocation, output pumping, input forwarding, resize handling, and cleanup.
- [ ] Preserve per-user session limits and idle timeout behavior.
- [ ] Ensure password is never logged.
- [ ] Add focused unit tests for connect-message handling, session-capacity behavior, and cleanup-safe helper logic.

### Task 3: Add frontend remote-host form and local persistence

**Files:**
- Modify: `frontend/src/components/TerminalPage.tsx`

- [ ] Add controlled fields for `host`, `port`, `username`, and `password`.
- [ ] Load and save these fields from `localStorage`.
- [ ] On websocket open, send the `connect` message before enabling normal terminal interaction.
- [ ] Show target metadata and expose buttons for connect, disconnect, and clearing saved credentials.
- [ ] Keep resize and terminal input behavior working after session establishment.

### Task 4: Verification

**Files:**
- Test: `backend/tests/unit/terminal/test_terminal_module.py`
- Test: `frontend/src/components/TerminalPage.tsx`

- [ ] Run `cd backend && pytest tests/unit/terminal/test_terminal_module.py -v`.
- [ ] Run `cd frontend && npm run lint`.
- [ ] Fix any failures caused by protocol or typing changes.
