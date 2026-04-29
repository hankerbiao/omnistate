# Backend Redundancy Governance Review

Date: 2026-04-29

This review covers `backend` only. It intentionally avoids broad security hardening because the system
runs in an internal trusted environment. The goal is to make unused and redundant backend code visible,
reviewable, and preventable through repeatable checks.

## Governance Goal

Treat cleanup as architecture governance, not one-off deletion. A file or abstraction should be removed
only after there is evidence that it is outside the runtime surface, has no supported compatibility
caller, and is covered by tests or a clear manual verification path.

The backend currently has a modular FastAPI monolith shape:

- `app/main.py` owns app startup, Beanie model registration, workflow consistency checks, and
  infrastructure lifecycle.
- `app/shared/api/main.py` mounts all runtime HTTP routers.
- Business modules live under `app/modules/*` with `api`, `application`, `domain`, `repository`,
  `schemas`, and legacy `service` layers.
- Existing architecture tests already prevent several removed facades from returning.

## Classification Rules

Use these labels for every cleanup candidate:

- `P0 delete`: generated or local-only artifacts, such as `__pycache__`, `.DS_Store`, logs, IDE files,
  coverage output, and built documentation output. These should never be tracked.
- `P1 verify then delete`: compatibility wrappers, mock scripts, old facades, unused workers, orphaned
  routes, and unregistered models. These need import, entrypoint, and documentation checks first.
- `P2 consolidate`: duplicate use-case orchestration, repeated persistence helpers, duplicated error
  mapping, or service/application overlap. These are refactors, not direct deletes.
- `Keep`: startup scripts, migration compatibility logic, documented local test harnesses, and runtime
  adapters with active non-test callers.

## Standing Architecture Rules

- API modules perform HTTP mapping and dependency injection only. They should not reach across modules
  into another module's repository models unless the exception is documented in an architecture test.
- Application modules are the public use-case entry points for writes and meaningful reads.
- Domain modules contain pure rules, policies, and exceptions. They should not import API, service, or
  infrastructure code.
- Repository model modules describe persistence only.
- Cross-module writes go through application services or ports. Direct model reads are temporary query
  shortcuts and must be listed as explicit exceptions.
- Compatibility wrappers are allowed only while at least one runtime caller still imports them.

## Current Cleanup Candidates

Immediate generated-artifact candidates observed in the working tree:

- `backend/app/**/__pycache__/`
- `backend/tests/**/__pycache__/`
- `backend/scripts/__pycache__/`
- `backend/app/shared/logs/*.log`
- `backend/app/excalidraw.log`
- `backend/app/.DS_Store`
- `backend/app/configs/.DS_Store`
- `backend/docs/.vitepress/cache/`
- `backend/docs/.vitepress/dist/`
- `backend/docs/node_modules/`

These are already ignored by the root `.gitignore`; the governance test ensures they do not become
tracked files.

Runtime candidates that need evidence before deletion:

- `scripts/mock_rabbitmq_consumer.py`: keep as a documented local execution harness unless a replacement
  worker simulation exists.
- `app/modules/*/service`: do not mass-delete. Some classes are legacy orchestration, but several are
  still called by application services and routes.
- `app/main.py` model registration list: not dead code, but a consolidation target. Move to module-owned
  exports when startup composition is refactored.

Cleaned runtime redundancy:

- `app/shared/kafka/kafka_message_manager.py` and
  `app/shared/rabbitmq/rabbitmq_message_manager.py` were removed after
  `app/shared/infrastructure/registry.py` was migrated to the concrete producer manager classes.
- `app/main.py` no longer owns Beanie model registration or workflow consistency validation. Module
  model packages expose `DOCUMENT_MODELS`, and `app/shared/infrastructure/bootstrap.py` owns startup
  model composition and workflow config validation.
- `ExecutionTaskCommandService` no longer inherits `ExecutionTaskCaseMixin` only to resolve automation
  case bindings. `ExecutionCaseResolver` now owns case binding lookup as an explicit collaborator.
- `ExecutionDispatchService` no longer inherits `ExecutionTaskQueryMixin` only to serialize task
  responses. `ExecutionTaskSerializer` now owns task and task-case response serialization.
- `ExecutionDispatchService` no longer inherits `ExecutionTaskDispatchMixin` for real dispatch side
  effects. `ExecutionTaskDispatchCoordinator` now owns dispatch command rebuilding and task/case
  dispatch state updates.
- `ExecutionDispatchService` no longer inherits `ExecutionTaskCaseMixin` for case loading, payload
  parsing, or case snapshot rebuild. `ExecutionTaskCaseCoordinator` now owns those responsibilities.

## Review Procedure

Run this sequence when reviewing backend redundancy:

1. Runtime surface check: start from `app/main.py`, `app/shared/api/main.py`, `app/workers`, and
   `scripts`. Confirm which files are reachable from HTTP, worker, or documented CLI entrypoints.
2. Static import check: search for imports of suspected files across `backend/app`, `backend/scripts`,
   and `backend/tests`. A file used only by tests is not necessarily dead, but it needs an explicit test
   support reason.
3. Layer duplication check: compare `application` and `service` within each module. If both expose the
   same business operation, pick `application` as the long-term public entrypoint and shrink `service`
   toward private data operations.
4. Compatibility check: wrappers and old names must have a runtime caller. If the last runtime caller is
   removed, remove the wrapper in the same change.
5. Guardrail check: encode stable decisions in `tests/unit/architecture` so removed facades, generated
   artifacts, and forbidden dependency directions do not return silently.

## Acceptance Criteria

A cleanup change is ready when:

- It updates or confirms the relevant architecture test.
- It has a clear `P0`, `P1`, `P2`, or `Keep` classification.
- It does not remove compatibility behavior without identifying callers.
- `pytest tests/unit/architecture -v` passes.
- Wider unit tests pass when behavior code is changed.
