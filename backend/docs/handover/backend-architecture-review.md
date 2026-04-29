# Backend Architecture Review

Date: 2026-04-28

This review focuses on reducing backend code complexity and improving readability and extensibility in
`app`. Security hardening is intentionally not a primary topic because the system runs in an internal
trusted environment.

## Executive Summary

The backend is a modular FastAPI monolith with a generally healthy direction: modules are grouped by
business capability, workflow rules are centralized, and the execution module documents its current
serial-dispatch model. The main maintainability cost is not the technology choice. It comes from
inconsistent layer boundaries, repeated infrastructure patterns, and a few places where historical
refactors left two architecture styles living side by side.

The highest-value path is an incremental cleanup, not a rewrite. Keep the monolith, keep Beanie, keep
the current HTTP and MongoDB contracts, and reduce complexity by standardizing dependency assembly,
documenting module ownership, consolidating repeated document behavior, and making the command/query
application layer the visible entry point for business operations.

## Current Shape

The observed runtime shape is:

- `app/main.py` owns FastAPI app creation, MongoDB connection, Beanie model registration, workflow
  config validation, middleware, exception handlers, and infrastructure startup.
- `app/shared/api/main.py` mounts all module routers under `/api/v1`.
- Business modules are capability based: `workflow`, `test_specs`, `execution`, `auth`, `attachments`,
  and `terminal`.
- `workflow` has moved toward an application layer with command, query, mutation, ports, and hooks.
- `test_specs` uses both older service classes and newer command/query application services.
- `execution` uses command/query services plus several mixins to split task dispatch, case handling,
  command utilities, and query serialization.
- Shared infrastructure manages RabbitMQ, optional Kafka producer startup, and the execution scheduler
  through a process-level registry.

## Findings

### 1. Startup Composition Is Too Centralized

`app/main.py` currently imports every Beanie document model and registers them in one list. This makes
module ownership harder to see and turns every new model into an edit to the global app entry point.
The same file also owns workflow config validation and infrastructure lifecycle.

Impact:

- New modules must modify the central entry point.
- Startup behavior is harder to test in isolation.
- The file mixes app wiring, data model discovery, consistency checks, and infrastructure lifecycle.

Recommendation:

- Move document model lists into module-owned exports such as `app/modules/workflow/repository/models`.
- Create a small startup composition helper, for example `app/shared/infrastructure/bootstrap.py`, that
  collects `document_models` and runs consistency checks.
- Keep `app/main.py` as an orchestrator only: create app, apply middleware, call bootstrap, include router.

Priority: P0, low behavioral risk.

### 2. Module Layering Is Useful But Not Uniform

The codebase uses several layer names: `api`, `application`, `service`, `domain`, `repository`, and
`schemas`. The meaning is clear in `workflow`, less clear in `test_specs`, and mixed in `execution`.
For example, `test_specs` routes depend on application command/query services, but those services call
older service classes that still contain business rules, transaction handling, workflow gateway calls,
and document mutation.

Impact:

- New engineers must learn module-specific meanings of `service` and `application`.
- Business rules are split between domain policies, command services, and service classes.
- It is easy to add new behavior in the wrong layer because both patterns are available.

Recommendation:

- Adopt this convention for new work:
  - `api`: HTTP only, request/response mapping and auth dependencies.
  - `application`: use-case orchestration, commands, query services, cross-module ports.
  - `domain`: pure policy/rule decisions and domain exceptions.
  - `repository/models`: persistence models only.
  - `service`: legacy module-internal data operations until migrated.
- In `test_specs`, stop adding new public use cases to `service`; add them to `application` and let
  service classes shrink toward persistence helpers.
- Update module README files so their documented layer meaning matches the code. The local
  `app/modules/workflow/README.md` still describes `service/` as the core service layer, while the
  current implementation uses `application/`.

Priority: P0 for documentation and convention; P1 for code movement.

### 3. Cross-Module Boundaries Are Mostly Good, But Need One Rule

`test_specs` talks to `workflow` through `WorkflowItemGateway` and `WorkflowServicesAdapter` in some
paths, which is a good direction. There are still direct reads from workflow persistence models in
support code, such as status projection helpers. `execution` directly imports `test_specs` repository
models to resolve automation/manual case bindings.

Impact:

- Direct model imports couple module storage details.
- Future changes to `workflow` or `test_specs` persistence can break unrelated modules.
- The intended port/gateway pattern is not consistently applied.

Recommendation:

- Define a simple rule: cross-module writes and use cases go through application ports; direct model reads
  are only allowed for explicitly documented projection/query shortcuts.
- Add small query ports where the dependency is stable and important:
  - `test_specs` should expose a case metadata lookup port for `execution`.
  - `workflow` should expose status lookup/projection through an application query method instead of
    support helpers reading workflow documents directly.
- Do not introduce a full repository abstraction layer across all Beanie models yet; it would add more
  code than it removes.

Priority: P1.

### 4. Repeated Document Behavior Should Be Standardized

Many models repeat `is_deleted`, `created_at`, `updated_at`, and `update_updated_at`. Many services also
repeat `{"is_deleted": False}` filters, soft delete assignments, and document-to-dict conversion. There
is already a small `BaseService._doc_to_dict`, but it is not enough to express the common document
contract.

Impact:

- Soft-delete behavior is easy to forget.
- Timestamp behavior differs slightly by model.
- CRUD code is longer than the business logic it protects.

Recommendation:

- Add shared model mixins for common Beanie fields:
  - `TimestampedDocumentMixin` for UTC `created_at`, `updated_at`, and touch behavior.
  - `SoftDeleteDocumentMixin` for `is_deleted` and optional `deleted_at` where needed.
- Add small shared query helpers, not a large base repository:
  - `not_deleted()` returning `{"is_deleted": False}`.
  - `soft_delete(doc)` that marks deletion and updates timestamps.
  - `model_to_public_dict(doc)` for `id` string normalization where Pydantic output is not enough.
- Migrate module by module, starting with new code and high-churn services.

Priority: P1.

### 5. Error Mapping Is Too Route-Local

Routes frequently catch `ValueError`, `KeyError`, module-specific exceptions, and generic exceptions,
then convert them to `HTTPException`. There is a global exception handler, but modules still perform a
lot of route-local mapping.

Impact:

- API error behavior can drift across modules.
- Route handlers become noisy.
- It is harder to see the happy path.

Recommendation:

- Keep route-local handling only where status code is genuinely endpoint-specific.
- Add a small set of shared application exceptions or extend existing domain exceptions:
  - `NotFoundError`
  - `ConflictError`
  - `ValidationError`
  - `PermissionDeniedError`
- Register centralized mappings in `app/shared/api/errors/handlers.py`.
- Migrate opportunistically: do not mass-rewrite every route first.

Priority: P1.

### 6. Execution Service Mixins Reduce File Size But Increase Reading Cost

`ExecutionDispatchService` and `ExecutionTaskCommandService` compose behavior through multiple mixins.
This keeps individual files smaller, but the primary execution flow crosses several classes and files:
command construction, case resolution, deduplication, task persistence, case persistence, dispatch, and
serialization are not visible from one place.

Impact:

- Debugging task dispatch requires jumping across many files.
- Private helper ownership is unclear because helpers are inherited rather than explicitly composed.
- Future changes may add another mixin instead of clarifying a use-case boundary.

Recommendation:

- Keep the current behavior and external API unchanged.
- Replace inheritance mixins gradually with explicit collaborators:
  - `ExecutionCaseResolver`
  - `ExecutionTaskWriter`
  - `ExecutionTaskDispatcher`
  - `ExecutionTaskSerializer`
- Make `ExecutionTaskCommandService` own the high-level use cases: create, rerun, delete, stop, cancel.
- Make `ExecutionDispatchService` either a true dispatch collaborator or merge it into command service if
  it only exists to bridge mixin methods.

Priority: P2, because dispatch behavior is business-critical and should be changed after tests are tight.

### 7. Workflow Is the Best-Defined Core, But It Needs Public Boundaries

`workflow` has a clear split between query, mutation, commands, domain policies, and hooks. The main
issue is that it exposes many concrete services directly through FastAPI dependencies and other modules.

Impact:

- Other modules can bypass command service invariants by using mutation/query services directly.
- Hook behavior, such as test spec projection, is not obvious unless reading dependency wiring.

Recommendation:

- Treat `WorkflowCommandService` as the write-side public API.
- Treat `WorkflowQueryService` as the read-side public API.
- Keep `WorkflowMutationService` module-internal unless there is a specific reason to inject it.
- Document hook registration as part of module integration: `test_specs` adds a projection hook when
  building its workflow command service.

Priority: P0 for documentation; P1 for dependency cleanup.

### 8. Infrastructure Registry Is Pragmatic But Has Too Many Responsibilities

`InfrastructureRegistry` starts RabbitMQ producer management, lazily starts Kafka producer management,
runs the execution scheduler loop, performs health checks, and records component status. It is useful,
but it is now both a lifecycle manager and a component registry.

Impact:

- Health semantics are tied to startup choices, such as Kafka being marked skipped while still lazily
  available.
- Scheduler lifecycle is coupled to messaging producer lifecycle.
- Tests for one component require understanding the whole registry.

Recommendation:

- Split status tracking from component startup:
  - `InfrastructureRegistry`: lookup and lifecycle orchestration.
  - `ComponentStatusStore`: status updates and health snapshot formatting.
  - `ExecutionSchedulerRunner`: scheduler loop.
- Keep the public helpers `get_kafka_manager`, `get_rabbitmq_manager`, and `shutdown_infrastructure`
  stable during migration.

Priority: P2.

## Recommended Roadmap

### Phase 1: Align Documentation And Guardrails

Goal: make the intended architecture obvious without changing runtime behavior.

- Update module README files to match the current layer names and ownership.
- Add a short backend architecture guide describing allowed dependencies:
  - API can depend on application and schemas.
  - Application can depend on domain, models, and cross-module ports.
  - Domain should not depend on API, service, or infrastructure.
  - Cross-module writes use ports/application services.
- Add a lightweight architecture test to catch obvious upward dependencies and direct forbidden imports.
- Document workflow as the authoritative status source for requirements and test cases.

Expected benefit: lower onboarding cost and fewer inconsistent future changes.

### Phase 2: Standardize Composition And Shared Patterns

Goal: remove repeated wiring and repeated persistence boilerplate.

- Move Beanie document model collection out of `app/main.py` into module-owned exports.
- Add a bootstrap helper that initializes Beanie and runs startup consistency checks.
- Introduce shared timestamp/soft-delete helpers and migrate only touched modules first.
- Centralize common exception-to-HTTP mappings.

Expected benefit: smaller app entry point, less repeated CRUD noise, more consistent API behavior.

### Phase 3: Clarify `test_specs` And Workflow Integration

Goal: make requirement/test-case use cases readable from application services.

- Make command/query application services the only public entry points used by routes.
- Move permission checks, workflow command calls, and high-level business decisions into application
  services.
- Shrink `RequirementService` and `TestCaseService` toward persistence-oriented helpers.
- Replace direct workflow document reads in projection support with a workflow query port where practical.

Expected benefit: easier feature changes for requirements and test cases, less confusion between
business orchestration and persistence helpers.

### Phase 4: Refactor Execution Internals After Test Coverage

Goal: reduce dispatch flow reading cost without changing task behavior.

- Add focused tests around create, rerun, deduplication, scheduled dispatch, serial case progress, and
  event ingestion.
- Replace mixin inheritance with named collaborators one responsibility at a time.
- Keep API schemas, MongoDB fields, and RabbitMQ/HTTP payload shape stable.

Expected benefit: safer execution changes and clearer ownership of dispatch, case resolution, and
serialization.

## Non-Goals

- Do not split this backend into microservices.
- Do not introduce a heavy dependency injection framework.
- Do not replace Beanie or MongoDB as part of complexity reduction.
- Do not perform a broad security redesign in this review cycle.
- Do not mass-rewrite all services before adding architecture tests and behavior tests.

## Suggested Acceptance Criteria

- `app/main.py` no longer imports every module model directly.
- New module models can be registered through module-local exports.
- Module README files and `docs/guide/architecture-overview.md` agree on layer definitions.
- Route handlers are shorter because common error mappings and dependency assembly are centralized.
- New cross-module behavior uses a named port/application service instead of importing another module's
  document model by default.
- Execution dispatch behavior has tests before mixin removal starts.

## Verification Used For This Review

- Inspected module layout under `app`.
- Inspected FastAPI app startup, API router mounting, workflow dependencies, test spec dependencies,
  execution command/dispatch services, infrastructure registry, and representative service files.
- Ran `python -m compileall -q app`; the current source compiles successfully.
