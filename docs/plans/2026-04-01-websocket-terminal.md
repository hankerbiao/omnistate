# WebSocket Terminal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a simple production-facing WebSocket terminal module that lets the frontend open an `xterm.js` shell backed by a real PTY session.

**Architecture:** Add a new backend `terminal` module with a WebSocket endpoint and a small in-memory session manager, then add a standalone frontend `TerminalPage` integrated into the existing tab-based app shell.

**Tech Stack:** FastAPI WebSocket, Python PTY/subprocess, React 19, TypeScript, xterm.js

---

### Task 1: Add terminal configuration and permission scaffolding

**Files:**
- Modify: `backend/app/shared/db/config.py`
- Modify: `backend/scripts/init_rbac.py`
- Modify: `backend/app/init_mongodb.py`

**Step 1: Write the failing test**

Add a backend test for terminal settings defaults or RBAC permission presence.

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/... -v`

**Step 3: Write minimal implementation**

Add `TERMINAL_*` settings and `terminal:connect` permission in RBAC seed data.

**Step 4: Run test to verify it passes**

Run the same test command.

### Task 2: Build backend terminal module

**Files:**
- Create: `backend/app/modules/terminal/api/routes.py`
- Create: `backend/app/modules/terminal/api/__init__.py`
- Create: `backend/app/modules/terminal/service/terminal_service.py`
- Create: `backend/app/modules/terminal/service/__init__.py`
- Create: `backend/app/modules/terminal/domain/session.py`
- Create: `backend/app/modules/terminal/domain/__init__.py`
- Create: `backend/app/modules/terminal/schemas/terminal.py`
- Create: `backend/app/modules/terminal/schemas/__init__.py`
- Create: `backend/app/modules/terminal/__init__.py`
- Modify: `backend/app/shared/api/main.py`

**Step 1: Write the failing test**

Add a focused test for token parsing or permission denial in the terminal WebSocket auth path.

**Step 2: Run test to verify it fails**

Run the new backend test directly.

**Step 3: Write minimal implementation**

Implement:

- token extraction from query string
- current user lookup
- permission check
- PTY-backed terminal session bridge
- clean shutdown on disconnect

**Step 4: Run test to verify it passes**

Run the targeted backend test.

### Task 3: Add frontend terminal test page

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/components/TerminalPage.tsx`

**Step 1: Write the failing test**

For this repo, use build failure as the first failing check by importing `xterm` before installation/integration is complete.

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm run build`

**Step 3: Write minimal implementation**

Add the terminal page and tab integration using `xterm` and `xterm-addon-fit`.

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm run build`

### Task 4: Verify backend correctness

**Files:**
- Modify as needed based on verification failures

**Step 1: Run targeted backend tests**

Run: `cd backend && pytest tests/unit -q`

**Step 2: Run terminal-specific lint/compile verification**

Run: `cd backend && python -m compileall app/modules/terminal app/shared`

**Step 3: Fix any failures**

Keep changes minimal and local to terminal work.

### Task 5: Verify frontend correctness

**Files:**
- Modify as needed based on verification failures

**Step 1: Run frontend build**

Run: `cd frontend && npm run build`

**Step 2: Fix any failures**

Keep changes limited to the terminal page and its app integration.
