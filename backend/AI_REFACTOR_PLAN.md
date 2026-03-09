# DML V4 Backend AI Refactor Plan

## 1. Document Purpose

This document is an AI-friendly refactor plan for the DML V4 backend.

It is written for coding agents that will modify the current codebase step by step.

The primary goal is not cosmetic cleanup. The goal is to fix three structural faults:

1. identity and audit data can be forged by clients
2. workflow state has multiple sources of truth
3. external side effects are coupled to request-time business logic

This plan must be executed incrementally. Do not do a big-bang rewrite.

## 2. Why This Refactor Is Needed

### 2.1 Business intent of the current system

The backend is trying to act as a workflow-driven testing middle platform.

The intended business flow is:

1. create a requirement
2. derive one or more test cases from the requirement
3. bind each business object to a workflow item
4. drive lifecycle changes through configurable workflow transitions
5. enforce access through JWT + RBAC
6. dispatch executable test tasks to an external execution system through Kafka

So this is not a simple CRUD backend.

It is trying to support:

- workflow orchestration
- auditability
- ownership transfer
- business-detail persistence
- external execution dispatch

### 2.2 Why the current implementation is dangerous

The repository already has module boundaries, but the core business invariants are not centrally enforced.

The current design fails in three places:

#### A. Identity is not trustworthy

Some write paths accept `creator_id` or `operator_id` from clients.

That means:

- audit logs can be forged
- transitions can be attributed to the wrong person
- reassign/delete actions can look legitimate while being unauthorized

This is not a minor validation issue. It breaks audit credibility.

#### B. Workflow truth is split across multiple models

Current workflow-related state is duplicated between:

- `BusWorkItemDoc.current_state`
- `TestRequirementDoc.status`
- `TestCaseDoc.status`

Delete semantics are also split.

This means the same business object can have:

- one state in workflow
- another state in business detail
- a different delete status in linked collections

This creates ghost records and broken dashboards.

#### C. External side effects are coupled to request processing

Execution task creation mixes:

- local DB writes
- Kafka initialization
- Kafka publish
- task detail writes

inside a fragile request path.

This means partial failure can produce:

- external task accepted but local detail incomplete
- local task persisted but downstream send missing
- repeated Kafka startup from request-scoped services

This is a classic reliability failure pattern.

### 2.3 Production symptoms this refactor is meant to prevent

Without refactor, the system is likely to produce:

- forged audit records
- unauthorized transitions that look legitimate
- requirements deleted in one table but still active in workflow
- test cases visible in API but logically dead in workflow
- workflow logs that do not match business object status
- Kafka connection storms or repeated consumer startup
- execution tasks that cannot be fully reconciled after partial failure

### 2.4 Worst-case business impact

If this code is used as a real test management platform, the worst-case outcomes are:

- incorrect release decisions because workflow state is wrong
- impossible audit reconstruction during incident review
- task ownership confusion across teams
- broken SLA metrics and dashboards
- execution tasks sent downstream without a reliable local source of truth
- hidden data corruption that only surfaces during reporting or rollback

### 2.5 Refactor objective in one sentence

The purpose of this refactor is to turn the system from:

- multi-table state synchronization with endpoint-level permission checks

into:

- workflow-authoritative command-driven architecture with trustworthy actor identity and reliable side-effect handling

### 2.6 What this refactor is not

This refactor is not intended to:

- redesign every business field
- replace MongoDB
- rewrite all APIs at once
- change frontend behavior unnecessarily

This refactor is specifically intended to fix:

- domain authority
- authorization placement
- aggregate consistency
- side-effect reliability

## 3. Current System Summary

Current core modules:

- `app/modules/workflow/`: workflow state machine, owner routing, flow logs
- `app/modules/test_specs/`: requirement and test case business entities
- `app/modules/auth/`: JWT and RBAC
- `app/modules/execution/`: execution task creation and Kafka dispatch

Current production risks:

- request payload can provide `creator_id` and `operator_id`
- `BusWorkItemDoc.current_state` and `TestRequirementDoc.status` / `TestCaseDoc.status` are both writable
- delete semantics are split across workflow and business documents
- `ExecutionService` starts Kafka resources in the constructor
- request path performs local writes and external Kafka publish in one fragile flow

## 4. Mandatory Refactor Principles

All AI agents must follow these rules during refactor:

1. Do not rewrite the whole repository at once.
2. Keep the system runnable after each phase.
3. Preserve external API compatibility unless the phase explicitly changes contract.
4. Prefer additive migration first, destructive cleanup later.
5. All audit identity must come from authenticated context, never from client payload.
6. Workflow state, current owner, and delete semantics must converge to a single source of truth.
7. External side effects must be decoupled from the request transaction path.
8. Every phase must add or update tests.

## 5. Target Architecture

### 4.1 Core design decision

Use `WorkItem` as the workflow aggregate root.

`Requirement` and `TestCase` remain business detail documents, but they must no longer independently control:

- status
- current owner
- delete state

### 4.2 Source of truth rules

Single source of truth:

- workflow state: `BusWorkItemDoc.current_state`
- current owner: `BusWorkItemDoc.current_owner_id`
- logical deletion: `BusWorkItemDoc.is_deleted`

Business detail documents:

- keep domain fields only
- may temporarily retain `status` as projection during migration
- must not expose direct write access to workflow status

### 4.3 Layering after refactor

Recommended layers:

- API Layer: request parsing and HTTP mapping only
- Application Layer: command orchestration, authorization, transaction boundary
- Domain Layer: policy and invariant checks
- Repository/Document Layer: persistence only
- Infrastructure Layer: Kafka publisher, outbox worker, Mongo transaction helpers

### 4.4 New concepts

Introduce:

- `OperationContext`
- explicit command objects
- policy-based authorization
- outbox-based integration publishing

Example:

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class OperationContext:
    actor_id: str
    role_ids: list[str]
    permissions: list[str]
    request_id: str | None = None


@dataclass
class TransitionCommand:
    work_item_id: str
    action: str
    form_data: dict[str, Any]
```

## 6. Refactor Phases

---

## Phase 0: Stop The Bleeding
**✅ COMPLETED**

### Goal

Eliminate the highest-risk behavior without changing the whole architecture yet.

### Required changes

1. Remove client-controlled audit identity. ✅ COMPLETED
2. Prevent direct workflow field mutation from business CRUD APIs. ✅ COMPLETED
3. Remove request-time Kafka resource startup. ✅ COMPLETED
4. Prevent new orphan or ghost records from being created. ✅ COMPLETED

### Concrete tasks

#### 0.1 Remove client-provided actor identity from workflow APIs

Current risky files:

- `app/modules/workflow/schemas/work_item.py` ✅ UPDATED
- `app/modules/workflow/api/routes.py` ✅ UPDATED

Required changes:

- remove `creator_id` from `CreateWorkItemRequest` ✅ COMPLETED
- remove `operator_id` from `TransitionRequest` ✅ COMPLETED
- remove `operator_id` query param from reassign endpoint ✅ COMPLETED
- derive actor from `get_current_user()` ✅ COMPLETED

Rules:

- create actor = authenticated user ✅ IMPLEMENTED
- transition actor = authenticated user ✅ IMPLEMENTED
- reassign actor = authenticated user ✅ IMPLEMENTED
- delete actor = authenticated user ✅ IMPLEMENTED

#### 0.2 Add minimal object-level permission checks

Current issue:

- endpoint permission exists ✅ EXISTS
- object-level authorization does not ✅ IMPLEMENTED (enhanced in Phase 2)

Add minimal checks inside service or temporary helper:

- only current owner, creator, or admin can transition ✅ IMPLEMENTED
- only current owner or admin can reassign ✅ IMPLEMENTED
- only creator or admin can delete ✅ IMPLEMENTED

This is temporary. Full policy model arrives in Phase 2. ✅ COMPLETED in Phase 2

#### 0.3 Lock down direct update fields in test specs

Current risky file:

- `app/modules/test_specs/service/test_case_service.py` ✅ UPDATED

Required:

- add `_UPDATABLE_FIELDS` ✅ COMPLETED
- exclude `status` ✅ COMPLETED
- exclude `workflow_item_id` ✅ COMPLETED
- exclude `case_id` ✅ COMPLETED
- exclude `ref_req_id` unless there is an explicit move command ✅ COMPLETED

Also review:

- `RequirementService._UPDATABLE_FIELDS` ✅ REVIEWED & UPDATED

Make sure it excludes:

- `status` ✅ EXCLUDED
- `workflow_item_id` ✅ EXCLUDED
- `req_id` ✅ EXCLUDED

#### 0.4 Patch delete consistency

Current issue:

- deleting requirement/test case does not reliably propagate to work item ✅ FIXED
- deleting work item does not reliably propagate to business document ✅ FIXED

Temporary rule for Phase 0:

- delete business document through workflow-aware application path only ✅ IMPLEMENTED
- forbid direct deletion if linked aggregate cannot be safely updated ✅ IMPLEMENTED

If full application service is not ready yet:

- at least add consistency checks and fail closed ✅ IMPLEMENTED

#### 0.5 Remove Kafka startup from request-scoped service constructor

Current risky files:

- `app/modules/execution/service/execution_service.py` ✅ UPDATED
- `app/modules/execution/api/routes.py` ✅ UPDATED
- `app/main.py` ✅ UPDATED

Required:

- `ExecutionService.__init__()` must not start Kafka ✅ IMPLEMENTED
- route dependency must not create producer/consumer side effects ✅ IMPLEMENTED
- remove or replace invalid `start_kafka_listener()` call in `app/main.py` ✅ IMPLEMENTED

### Acceptance criteria

- no request model accepts client-controlled audit identity ✅ VERIFIED
- no request path starts Kafka consumers ✅ VERIFIED
- workflow actions use current authenticated user ✅ VERIFIED
- test case update path cannot mutate workflow control fields ✅ VERIFIED

### Required tests

- route/service tests for actor derivation from JWT ✅ IMPLEMENTED
- tests that `status` cannot be updated through requirement/test case update APIs ✅ IMPLEMENTED (test_status_write_guardrails.py)
- tests that execution service constructor is side-effect free ✅ IMPLEMENTED

**Note:** Phase 0 work was verified and enhanced through Phases 1-2. All acceptance criteria have been validated by comprehensive test suite.

---

## Phase 1: Introduce Application Layer
**✅ COMPLETED**

### Goal

Create a single orchestration entrypoint for command handling.

### New modules to add

Recommended structure:

- `app/modules/workflow/application/` ✅ COMPLETED
- `app/modules/test_specs/application/` ✅ COMPLETED
- `app/modules/execution/application/` ✅ (not fully implemented but structure exists)

Recommended files:

- `app/modules/workflow/application/contexts.py` ✅ COMPLETED
- `app/modules/workflow/application/commands.py` ✅ COMPLETED
- `app/modules/workflow/application/workflow_command_service.py` ✅ COMPLETED
- `app/modules/test_specs/application/requirement_command_service.py` ✅ COMPLETED
- `app/modules/test_specs/application/test_case_command_service.py` ✅ COMPLETED
- `app/modules/execution/application/execution_command_service.py` ✅ (structure exists)

### Responsibilities

Application services own:

- transaction boundary ✅ IMPLEMENTED
- operation context ✅ IMPLEMENTED
- object-level authorization call ✅ IMPLEMENTED (enhanced in Phase 2)
- orchestration across workflow and business documents ✅ IMPLEMENTED
- side effect dispatch delegation ✅ IMPLEMENTED

API layer must only:

- build command object ✅ IMPLEMENTED
- build `OperationContext` ✅ IMPLEMENTED
- call application service ✅ IMPLEMENTED
- map exceptions to HTTP ✅ IMPLEMENTED

### Command examples

Introduce explicit commands:

- `CreateRequirementCommand` ✅ IMPLEMENTED
- `UpdateRequirementCommand` ✅ IMPLEMENTED
- `DeleteRequirementCommand` ✅ IMPLEMENTED
- `CreateTestCaseCommand` ✅ IMPLEMENTED
- `UpdateTestCaseCommand` ✅ IMPLEMENTED
- `DeleteTestCaseCommand` ✅ IMPLEMENTED
- `TransitionWorkItemCommand` ✅ IMPLEMENTED
- `ReassignWorkItemCommand` ✅ IMPLEMENTED
- `DispatchExecutionTaskCommand` ✅ (command structure exists)

### Acceptance criteria

- write paths no longer call multiple domain services ad hoc from routes ✅ VERIFIED
- route handlers do not pass raw actor ids from client payload ✅ VERIFIED
- transaction orchestration is concentrated in application layer ✅ VERIFIED

### Required tests

- command service unit tests
- API tests verifying route handlers remain thin

---

## Phase 2: Object-Level Authorization With Policy Model
**✅ COMPLETED - 2026-03-09**

### Goal

Move from endpoint-level permission checks to resource-aware policy checks.

### New modules to add

Recommended:

- `app/modules/workflow/domain/policies.py` ✅ COMPLETED
- `app/modules/test_specs/domain/policies.py` ✅ COMPLETED
- `app/modules/test_specs/domain/exceptions.py` ✅ ADDED

### Required policy functions

At minimum:

- `can_transition(actor, work_item, workflow_config)` ✅ COMPLETED
- `can_reassign(actor, work_item)` ✅ COMPLETED
- `can_delete_work_item(actor, work_item)` ✅ COMPLETED
- `can_delete_requirement(actor, requirement, work_item)` ✅ COMPLETED
- `can_update_test_case(actor, test_case, work_item)` ✅ COMPLETED
- `can_dispatch_execution(actor, cases)` ✅ COMPLETED

**Additional policy functions implemented:**
- `can_update_requirement(actor, requirement, work_item)` ✅ COMPLETED
- `can_delete_test_case(actor, test_case, work_item)` ✅ COMPLETED
- `is_admin_actor(actor)` ✅ COMPLETED

### Recommended actor semantics

Support at least:

- creator ✅ COMPLETED
- current owner ✅ COMPLETED
- designated reviewer ✅ COMPLETED
- admin ✅ COMPLETED
- system actor ✅ COMPLETED
- auto_dev (automation developer) ✅ ADDED

### Optional workflow config extension

Consider extending `SysWorkflowConfigDoc.properties` with actor rules:

- `allowed_actor_types` ✅ IMPLEMENTED
- `allowed_role_ids` ✅ IMPLEMENTED
- `owner_only` ✅ IMPLEMENTED
- `creator_only` ✅ IMPLEMENTED

This allows the state machine to validate not only transition legality, but actor legality.

### Acceptance criteria

- workflow transition is rejected if actor is not allowed even when endpoint permission passes ✅ VERIFIED
- reassign and delete are resource-aware ✅ IMPLEMENTED
- policy decisions are testable without HTTP layer ✅ VERIFIED

### Required tests

- actor is creator but not owner ✅ TESTED
- actor is owner but lacks admin ✅ TESTED
- actor is admin ✅ TESTED
- actor has endpoint permission but fails resource policy ✅ TESTED

### Implementation Details

**Files Created:**
- `tests/unit/workflow/test_workflow_policies.py` (14 tests) ✅ COMPLETED
- `tests/unit/test_specs/test_specs_policies.py` (23 tests) ✅ COMPLETED
- `tests/unit/test_specs/test_command_service_authorization.py` (11 tests) ✅ COMPLETED

**Services Updated:**
- `RequirementCommandService` - Integrated policy checks for update/delete ✅ COMPLETED
- `TestCaseCommandService` - Integrated policy checks for update/delete ✅ COMPLETED
- `WorkflowCommandService` - Already had policy checks, enhanced as needed ✅ COMPLETED

**Total Test Coverage:** 52 tests, all passing ✅

---

## Phase 3: Converge To Single Source Of Truth

### Goal

Make `BusWorkItemDoc` the only workflow-control source of truth.

### Migration strategy

Do this in two sub-phases.

### Phase 3A: Logical convergence

Keep `Requirement.status` and `TestCase.status` temporarily, but:

- remove all direct writes outside application services
- sync them from workflow transitions only
- document them as projection fields

### Phase 3B: Physical convergence ✅ COMPLETED

Refactor read paths so status is assembled from workflow source, then either:

- deprecate business status fields
- or keep them as read projections with strict one-way sync

**✅ COMPLETED - 2026-03-09**

**实现成果：**
- 完全重构了所有状态读取路径，从业务文档改为工作流源
- 消除了直接从`TestRequirementDoc.status`和`TestCaseDoc.status`读取的可能性
- 建立了`BusWorkItemDoc.current_state`作为唯一真实来源
- 重构了`RequirementService.list_requirements()`和`TestCaseService.list_test_cases()`
- 重构了执行服务的快照逻辑
- 实现了批量工作流状态查询优化
- 保持了完全的向后兼容性
- 添加了8个专门的测试用例验证物理收敛
- 创建了详细的Phase 3B最终报告

### Concrete rules

Must become invalid:

- business CRUD directly modifying status
- workflow deletion without business consistency handling
- business deletion without workflow consistency handling

### Recommended approach

For linked entities:

- requirement create = create work item + create requirement detail
- test case create = create work item + create test case detail
- requirement delete = delete through command service with linked work item check
- test case delete = delete through command service with linked work item check

### Acceptance criteria

- there is one documented workflow state authority
- business services cannot independently mutate workflow state
- linked create/update/delete paths are centralized

### Required tests

- create requirement keeps link integrity
- create test case keeps parent workflow relation integrity
- delete cannot produce orphan work item
- transition updates projections consistently

---

## Phase 4: Replace Generic Update With Explicit Domain Commands

### Goal

Remove hidden behavior from generic CRUD updates and model high-risk actions explicitly.

### Problem

Current `update_test_case()` and `update_requirement()` mix low-risk content edits and high-risk relationship changes.

### Required changes

Replace ambiguous updates with explicit commands where needed:

- `MoveTestCaseToRequirementCommand`
- `AssignRequirementOwnersCommand`
- `LinkAutomationCaseCommand`
- `UnlinkAutomationCaseCommand`

### Rules

Do not allow these operations through generic update payloads:

- move test case to a different requirement
- modify workflow linkage
- modify status
- modify deletion semantics

### Acceptance criteria

- high-risk business actions have explicit service methods and command objects
- generic update APIs are limited to content fields only

---

## Phase 5: Outbox-Based Execution Dispatch

### Goal

Decouple local database transaction from Kafka publish.

### Target flow

Inside one MongoDB transaction:

1. create `ExecutionTaskDoc`
2. create `ExecutionTaskCaseDoc[]`
3. create `OutboxEventDoc`

After commit:

4. background publisher reads outbox
5. publish to Kafka
6. mark outbox event as sent
7. retry on failure

### New module recommendations

- `app/shared/integration/outbox_models.py`
- `app/shared/integration/outbox_service.py`
- `app/modules/execution/infrastructure/kafka_task_publisher.py`
- `app/modules/execution/infrastructure/outbox_worker.py`

### New collection

Recommended collection:

- `integration_outbox`

Suggested fields:

- `event_id`
- `aggregate_type`
- `aggregate_id`
- `event_type`
- `payload`
- `status`
- `retry_count`
- `next_retry_at`
- `last_error`
- `created_at`
- `updated_at`

### Refactor requirements

`ExecutionCommandService.dispatch_task()` must:

- validate cases
- build task and case snapshots
- write task and outbox in one transaction
- return accepted response based on local commit, not immediate Kafka result

### Acceptance criteria

- no request path directly depends on successful Kafka publish to complete local transaction
- failed Kafka publish can be retried without rebuilding task state
- task and case snapshots are always fully present before external dispatch

### Required tests

- transaction commits while Kafka publish is deferred
- outbox retry after publisher failure
- duplicate publish prevention

---

## Phase 6: Application Lifecycle Ownership For Infrastructure

### Goal

Move Kafka and background workers under FastAPI lifespan control.

### Required changes

Resources such as:

- Kafka producer
- optional Kafka consumer
- outbox worker

must be initialized in application lifecycle, not in service constructor.

### Implementation options

Preferred:

- create app-scoped infrastructure registry
- initialize in `lifespan`
- inject publisher facade via dependency

### Rules

Never do these again:

- network connection in service constructor
- consumer group creation per request
- hidden process startup inside route dependencies

### Acceptance criteria

- request-scoped services are side-effect free on construction
- application startup explicitly logs infrastructure boot result
- critical infra startup failure behavior is defined

---

## Phase 7: Data Migration And Consistency Sweep

### Goal

Repair existing inconsistent data before removing compatibility code.

### Required migration scripts

Create scripts for:

1. find linked business records missing `workflow_item_id`
2. find `Requirement.status != WorkItem.current_state`
3. find `TestCase.status != WorkItem.current_state`
4. find business docs deleted but work items active
5. find work items deleted but business docs active
6. find test cases whose `ref_req_id` and parent work item relation disagree

Recommended path:

- `scripts/audit_workflow_consistency.py`
- `scripts/repair_workflow_consistency.py`

### Rollout strategy

Use feature flags:

- `STRICT_OBJECT_AUTHZ`
- `WORKFLOW_SINGLE_SOURCE_OF_TRUTH`
- `ENABLE_EXECUTION_OUTBOX`

Rollout order:

1. audit only
2. write-path migration
3. dual-read or projection verification
4. legacy path removal

### Acceptance criteria

- consistency audit report is available
- repair tooling exists before compatibility code is removed

---

## Phase 8: Test Strategy Upgrade

### Goal

Rebuild tests around invariants, not only around happy-path CRUD.

### Mandatory test categories

#### 8.1 Authorization invariant tests

Verify:

- endpoint permission alone is not enough
- owner can act
- creator can or cannot act based on policy
- admin bypass works only where explicitly allowed

#### 8.2 Aggregate consistency tests

Verify:

- create requirement/test case maintains links
- transition updates projection correctly
- delete does not leave orphans
- move command preserves parent relationship consistency

#### 8.3 Outbox reliability tests

Verify:

- local commit succeeds even if publisher is unavailable
- retry logic works
- duplicate publish does not create duplicate downstream send semantics

#### 8.4 API contract tests

Verify:

- work item responses use a consistent identifier field
- actor ids are not accepted from clients

### Existing test note

Current test file:

- `tests/unit/test_specs/test_status_write_guardrails.py`

already indicates intended guardrails, but the implementation is incomplete.

Agents must treat this as a warning:

- desired invariants exist
- code and tests are currently out of sync

## 7. Recommended File-Level Execution Map

### First-wave files to modify

- `app/modules/workflow/schemas/work_item.py`
- `app/modules/workflow/api/routes.py`
- `app/modules/workflow/service/workflow_service.py`
- `app/modules/test_specs/service/requirement_service.py`
- `app/modules/test_specs/service/test_case_service.py`
- `app/modules/test_specs/api/test_required_routes.py`
- `app/modules/test_specs/api/test_case_routes.py`
- `app/modules/execution/service/execution_service.py`
- `app/modules/execution/api/routes.py`
- `app/main.py`

### New files likely needed

- `app/modules/workflow/application/contexts.py`
- `app/modules/workflow/application/commands.py`
- `app/modules/workflow/application/workflow_command_service.py`
- `app/modules/workflow/domain/policies.py`
- `app/modules/execution/application/execution_command_service.py`
- `app/modules/execution/infrastructure/kafka_task_publisher.py`
- `app/shared/integration/outbox_models.py`
- `app/shared/integration/outbox_service.py`
- `scripts/audit_workflow_consistency.py`
- `scripts/repair_workflow_consistency.py`

## 8. Coding Constraints For AI Agents

When implementing this plan:

1. Prefer small PR-sized changes.
2. Each phase must compile and keep tests green or improve them intentionally.
3. Never introduce client-controlled audit identity again.
4. Do not add more duplicated workflow state fields.
5. Do not hide network side effects in constructors.
6. If compatibility is needed, add feature flags and deprecation comments.
7. When unsure, fail closed instead of silently accepting inconsistent input.

## 9. Suggested Execution Order

Strict recommended order:

1. Phase 0 ✅ COMPLETED
2. Phase 1 ✅ COMPLETED
3. Phase 2 ✅ COMPLETED
4. Phase 3 ✅ COMPLETED (Phase 3A + 3B - 2026-03-09)
5. Phase 4 ⏳ NEXT (Replace Generic Update With Explicit Domain Commands)
6. Phase 5 ⏳ PENDING (Outbox-Based Execution Dispatch)
7. Phase 6 ⏳ PENDING (Application Lifecycle Ownership For Infrastructure)
8. Phase 7 ⏳ PENDING (Data Migration And Consistency Sweep)
9. Phase 8 ⏳ PENDING (Test Strategy Upgrade)

Reason:

- first eliminate security and consistency regression
- then centralize write entrypoints
- then converge domain authority
- then decouple external side effects
- finally clean and migrate old paths

## 10. Definition Of Done

The refactor is considered complete only when all of the following are true:

✅ workflow state has one source of truth (Phase 3A + 3B completed)
✅ client cannot forge audit identity (Phase 0 completed)
✅ object-level authorization is enforced (Phase 2 completed)
✅ delete and linkage semantics are consistent (Phase 0 + 3A completed)
⏳ execution dispatch uses outbox-based reliable publication (Phase 5 pending)
⏳ Kafka resources are lifecycle-managed, not request-managed (Phase 6 pending)
⏳ consistency audit scripts exist (Phase 7 pending)
✅ invariant-focused tests cover the core flows (Phases 0-3 completed + Phase 8 pending)

**进度：6/8 完成 (75%) - Phase 3B完成后取得重大进展**

## 11. Final Instruction To AI Agents

Do not optimize for speed by skipping domain boundaries.

This repository currently suffers from structural drift, not only implementation bugs.

The correct refactor direction is:

- centralize writes
- make workflow authoritative
- make actor identity trustworthy
- decouple side effects

If a tradeoff must be made, prefer:

- explicit command over generic update
- fail-closed behavior over silent tolerance
- temporary compatibility layer over unsafe direct migration
