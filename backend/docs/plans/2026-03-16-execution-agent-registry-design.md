# Execution Agent Registry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a minimal execution-agent registry so test agents can register themselves, report heartbeats, and be queried by the platform for connection visibility.

**Architecture:** Extend the existing `execution` module with a small Beanie document for agent registry state, minimal request/response schemas, and service methods for registration, heartbeat, and query flows. Keep online/offline derivation in the service so expired heartbeats are surfaced as offline without requiring a background job.

**Tech Stack:** FastAPI, Pydantic, Beanie ODM, pytest

---

### Task 1: Add agent registry persistence model

**Files:**
- Modify: `app/modules/execution/repository/models/execution.py`
- Modify: `app/modules/execution/repository/models/__init__.py`
- Modify: `app/main.py`

**Step 1: Write the failing test**

Add a route/service test that expects agent data to contain `agent_id`, `hostname`, `status`, and `last_heartbeat_at`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_api_execution_agents.py -v`
Expected: FAIL because agent schemas/service/routes do not exist.

**Step 3: Write minimal implementation**

Add `ExecutionAgentDoc` with scheduling fields and indexes. Register it in Beanie bootstrap and model exports.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_api_execution_agents.py -v`
Expected: registration and list route tests can serialize agent fields.

### Task 2: Add schemas and service methods

**Files:**
- Modify: `app/modules/execution/schemas/execution.py`
- Modify: `app/modules/execution/schemas/__init__.py`
- Modify: `app/modules/execution/application/execution_service.py`

**Step 1: Write the failing test**

Add tests expecting register and heartbeat payloads to be validated and agent list/detail responses to expose derived online state.

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_api_execution_agents.py -v`
Expected: FAIL because the new request/response models and service methods are missing.

**Step 3: Write minimal implementation**

Add Pydantic models for registration, heartbeat, and response payloads. Add `register_agent`, `heartbeat_agent`, `list_agents`, and `get_agent` methods to `ExecutionService`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_api_execution_agents.py -v`
Expected: PASS for route-level contract tests and unit coverage for status derivation.

### Task 3: Expose HTTP endpoints and permissions

**Files:**
- Modify: `app/modules/execution/api/routes.py`
- Modify: `app/init_mongodb.py`
- Modify: `app/modules/execution/README.md`

**Step 1: Write the failing test**

Add tests for:
- `POST /api/v1/execution/agents/register`
- `POST /api/v1/execution/agents/{agent_id}/heartbeat`
- `GET /api/v1/execution/agents`
- `GET /api/v1/execution/agents/{agent_id}`

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_api_execution_agents.py -v`
Expected: FAIL because the routes do not exist.

**Step 3: Write minimal implementation**

Expose the routes, apply read permissions to query endpoints, and document the new agent-registry API.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_api_execution_agents.py -v`
Expected: PASS for all agent API contract tests.

### Task 4: Add focused tests

**Files:**
- Create: `tests/integration/test_api_execution_agents.py`
- Create: `tests/unit/execution/test_execution_agent_service.py`

**Step 1: Write the failing test**

Cover online/offline derivation, register response structure, heartbeat response structure, and query route envelopes.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/execution/test_execution_agent_service.py tests/integration/test_api_execution_agents.py -v`
Expected: FAIL before implementation.

**Step 3: Write minimal implementation**

Use a fake execution service for route tests and pure unit tests for derived status logic.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/execution/test_execution_agent_service.py tests/integration/test_api_execution_agents.py -v`
Expected: PASS.
