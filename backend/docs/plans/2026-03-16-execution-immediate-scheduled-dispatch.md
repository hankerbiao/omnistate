# Execution Immediate And Scheduled Dispatch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add support for both immediate dispatch and scheduled dispatch for execution tasks while preserving the current Kafka/HTTP dispatch abstraction and deduplication semantics.

**Architecture:** Keep a single execution-task creation API and a single `ExecutionTaskDoc` model. Distinguish immediate and scheduled execution with scheduling metadata on the task record, and introduce a lightweight scheduler loop that scans due tasks and reuses the existing dispatch path. Deduplication remains centralized in `ExecutionService`, but the dedup key must include scheduling fields so tasks planned for different times are not treated as duplicates.

**Tech Stack:** FastAPI, Beanie ODM, Python async services, pytest

---

### Task 1: Extend execution task schema for scheduling

**Files:**
- Modify: `app/modules/execution/repository/models/execution.py`
- Modify: `app/modules/execution/schemas/execution.py`
- Test: `tests/unit/execution/test_execution_schedule_models.py`

**Step 1: Write the failing test**

Add a model/schema test asserting that execution tasks now expose:
- `schedule_type`
- `schedule_status`
- `planned_at`
- `triggered_at`

Example:

```python
def test_dispatch_request_accepts_schedule_fields():
    req = DispatchTaskRequest(
        framework="pytest",
        cases=[DispatchCaseItem(case_id="TC-001")],
        schedule_type="SCHEDULED",
        planned_at="2026-03-20T10:00:00Z",
    )
    assert req.schedule_type == "SCHEDULED"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/execution/test_execution_schedule_models.py -v`
Expected: FAIL because scheduling fields do not exist yet.

**Step 3: Write minimal implementation**

In `ExecutionTaskDoc`, add:
- `schedule_type: str = "IMMEDIATE"`
- `schedule_status: str = "READY"` for immediate tasks, `"PENDING"` for scheduled tasks
- `planned_at: Optional[datetime]`
- `triggered_at: Optional[datetime]`

In `DispatchTaskRequest`, add:
- `schedule_type: Literal["IMMEDIATE", "SCHEDULED"] = "IMMEDIATE"`
- `planned_at: Optional[datetime]`

In `DispatchTaskResponse`, add:
- `schedule_type`
- `schedule_status`
- `planned_at`
- `triggered_at`

Validation rules:
- `IMMEDIATE`: `planned_at` optional
- `SCHEDULED`: `planned_at` required and stored in UTC

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/execution/test_execution_schedule_models.py -v`
Expected: PASS

### Task 2: Split task creation from task dispatch in service layer

**Files:**
- Modify: `app/modules/execution/application/execution_service.py`
- Modify: `app/modules/execution/application/commands.py`
- Test: `tests/unit/execution/test_execution_scheduling_service.py`

**Step 1: Write the failing test**

Add tests for these behaviors:
- immediate task creates record and dispatches immediately
- scheduled task creates record and does not dispatch immediately
- scheduled task gets `schedule_status="PENDING"`
- immediate task gets `schedule_status="TRIGGERED"` after successful dispatch

Example:

```python
@pytest.mark.asyncio
async def test_scheduled_task_is_saved_but_not_dispatched():
    result = await service.dispatch_execution_task(command, actor_id="user-1")
    assert result["schedule_type"] == "SCHEDULED"
    assert result["schedule_status"] == "PENDING"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/execution/test_execution_scheduling_service.py -v`
Expected: FAIL because dispatch flow currently always pushes immediately.

**Step 3: Write minimal implementation**

Refactor `ExecutionService`:

1. Add a helper to normalize schedule fields:

```python
def _normalize_schedule(schedule_type, planned_at, now):
    ...
```

Rules:
- `IMMEDIATE`: set `schedule_status="READY"` before dispatch, then `TRIGGERED` after successful handoff
- `SCHEDULED`: persist `schedule_status="PENDING"` and skip dispatcher call
- if `planned_at <= now`, treat scheduled task as due and dispatch immediately

2. When creating `ExecutionTaskDoc`, populate:
- `schedule_type`
- `schedule_status`
- `planned_at`
- `triggered_at`

3. Extract the existing “send to dispatcher and update result” block into a helper such as:

```python
async def _dispatch_existing_task(self, task_doc, command) -> None:
    ...
```

4. Update dedup key generation to include:
- `schedule_type`
- normalized `planned_at` (or `None`)

This prevents tasks scheduled for different times from colliding.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/execution/test_execution_scheduling_service.py -v`
Expected: PASS

### Task 3: Add scheduler service for due tasks

**Files:**
- Create: `app/modules/execution/service/task_scheduler.py`
- Modify: `app/shared/infrastructure/registry.py`
- Modify: `app/modules/execution/service/__init__.py`
- Test: `tests/unit/execution/test_execution_task_scheduler.py`

**Step 1: Write the failing test**

Add tests asserting:
- scheduler scans `schedule_status="PENDING"` and `planned_at <= now`
- due tasks transition to dispatch path
- non-due tasks are ignored

Example:

```python
@pytest.mark.asyncio
async def test_scheduler_dispatches_due_scheduled_tasks():
    await scheduler.tick()
    assert dispatched_task_ids == ["ET-2026-000001"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/execution/test_execution_task_scheduler.py -v`
Expected: FAIL because scheduler service does not exist yet.

**Step 3: Write minimal implementation**

Create `ExecutionTaskScheduler` that:
- queries `ExecutionTaskDoc` where:
  - `schedule_type == "SCHEDULED"`
  - `schedule_status == "PENDING"`
  - `planned_at <= now`
  - `is_deleted == False`
- marks tasks as `schedule_status="READY"` before dispatch attempt
- rebuilds `DispatchExecutionTaskCommand` from stored `request_payload`
- calls `ExecutionService._dispatch_existing_task(...)`
- on success sets:
  - `schedule_status="TRIGGERED"`
  - `triggered_at=now`
- on failure either:
  - revert to `PENDING`, or
  - set `schedule_status="FAILED"`

Recommendation: use `FAILED` if handoff failed after the due moment; do not silently reset to `PENDING`.

Register a background loop in infrastructure lifecycle:
- only start once
- sleep on configurable interval, e.g. `EXECUTION_SCHEDULER_INTERVAL_SEC`

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/execution/test_execution_task_scheduler.py -v`
Expected: PASS

### Task 4: Expose API behavior for scheduling and cancellation

**Files:**
- Modify: `app/modules/execution/api/routes.py`
- Modify: `app/modules/execution/schemas/execution.py`
- Test: `tests/integration/test_api_execution_scheduling.py`

**Step 1: Write the failing test**

Add API tests for:
- scheduled dispatch request returns `201` with `schedule_status="PENDING"`
- immediate dispatch request returns `201` with `schedule_status="TRIGGERED"` or immediate-ready equivalent
- cancel endpoint updates pending scheduled task to `CANCELLED`

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_api_execution_scheduling.py -v`
Expected: FAIL because schedule fields and cancel route are not implemented.

**Step 3: Write minimal implementation**

1. Keep `POST /api/v1/execution/tasks/dispatch` as the unified entrypoint.
2. Add:

```python
POST /api/v1/execution/tasks/{task_id}/cancel
```

Cancellation rule:
- only allow when `schedule_type == "SCHEDULED"` and `schedule_status == "PENDING"`
- reject if already `TRIGGERED`, `FAILED`, or `CANCELLED`

3. Update `get_task_status` output to include:
- `schedule_type`
- `schedule_status`
- `planned_at`
- `triggered_at`

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_api_execution_scheduling.py -v`
Expected: PASS

### Task 5: Document configuration and operating rules

**Files:**
- Modify: `app/modules/execution/README.md`
- Modify: `app/shared/db/config.py`

**Step 1: Write the failing test**

No automated test required. Use documentation review.

**Step 2: Run test to verify it fails**

N/A

**Step 3: Write minimal implementation**

Document:
- difference between immediate and scheduled tasks
- UTC requirement for `planned_at`
- background scheduler interval config
- interaction with deduplication
- cancellation semantics

Add config:
- `EXECUTION_SCHEDULER_INTERVAL_SEC: int = 5`

**Step 4: Run test to verify it passes**

Run: `python -m compileall app/modules/execution app/shared/db/config.py`
Expected: PASS

### Task 6: Full targeted verification

**Files:**
- Test: `tests/unit/execution/test_execution_schedule_models.py`
- Test: `tests/unit/execution/test_execution_scheduling_service.py`
- Test: `tests/unit/execution/test_execution_task_scheduler.py`
- Test: `tests/integration/test_api_execution_scheduling.py`

**Step 1: Run focused test set**

Run:

```bash
pytest \
  tests/unit/execution/test_execution_schedule_models.py \
  tests/unit/execution/test_execution_scheduling_service.py \
  tests/unit/execution/test_execution_task_scheduler.py \
  tests/integration/test_api_execution_scheduling.py -v
```

Expected: PASS

**Step 2: Run compile check**

Run:

```bash
python -m compileall app/modules/execution app/shared/infrastructure/registry.py app/shared/db/config.py
```

Expected: PASS

**Step 3: Commit**

```bash
git add app/modules/execution app/shared/infrastructure/registry.py app/shared/db/config.py tests/unit/execution tests/integration docs/plans/2026-03-16-execution-immediate-scheduled-dispatch.md
git commit -m "feat: add immediate and scheduled execution dispatch"
```
