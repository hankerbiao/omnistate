# AGENTS.md

This file provides guidance for agentic coding agents operating in the DML V4 repository.

## Build/Lint/Test Commands

### Project Root

```bash
pip install -r requirements.txt         # Install Python dependencies from repo root
```

### Backend Commands

```bash
# Development server (daemon on port 8801)
cd backend
./server.sh start
# Or foreground on port 8000:
.venv/bin/python -m app.main

# Database initialization
cd backend
python scripts/init/init_mongodb.py      # Sync workflow configs + base app data
python scripts/init/init_rbac.py        # Initialize RBAC (roles/permissions)
python scripts/init/create_user.py \
  --user-id admin001 --username "系统管理员" --password 'Admin@123' \
  --roles ADMIN --email admin@example.com --upsert

# Testing (pytest)
cd backend
pytest                                  # All backend tests
pytest tests/unit/workflow/ -v          # Specific test directory
pytest tests/unit/workflow/test_workflow_service.py -v
pytest tests/unit/workflow/test_workflow_service.py::test_create_item -v  # Single test
pytest tests/integration/ -v            # Integration tests (requires MongoDB)
pytest --cov=app                        # With coverage

# Linting (flake8)
cd backend
flake8                                  # Max line length: 110, max complexity: 12
flake8 app/modules/workflow/service/    # Specific directory
flake8 --select=E,W,F                   # Specific error codes
```

Lint configuration: `backend/.flake8` (`max-line-length = 110`, `max-complexity = 12`, ignores E203/W503/W293/E501). Also configured in `backend/pyproject.toml` under `[tool.flake8]`.

Pytest config: `backend/pyproject.toml` sets `asyncio_mode = "auto"` for all tests. Integration tests have additional settings in `backend/tests/integration/pytest.ini` (short tracebacks, function-level loop scope).

### Frontend Commands

```bash
cd frontend
npm install                             # Install dependencies
npm run dev                             # Vite dev server (port 3000, accessible on network)
npm run build                           # tsc -b && vite build
npm run lint                            # ESLint (flat config)
npm run preview                         # Preview production build
npm run clean                           # Clean dist directory
```

### Documentation Site Commands

```bash
cd backend/docs
npm install
npm run docs:dev                        # VitePress dev server
npm run docs:build                      # Build static site
npm run docs:preview                    # Preview built site
```

## Runtime Configuration

- Backend config is loaded from `backend/config.yaml` via `app.shared.config.get_settings()`. See `backend/config.yaml.example` for the canonical template.
- Key sections: `app` (debug, cors), `mongodb` (uri, db_name), `rabbitmq`, `kafka`, `minio` (attachments storage), `jwt` (secret, algorithm, expire), `execution`, `redis`, `notification`, `logging`.
- Beanie index sync is skipped by default (`SKIP_INDEX_SYNC=1`). Run `python scripts/init/init_mongodb.py` or set `SKIP_INDEX_SYNC=0` when indexes must be synchronized.
- Frontend API base URL: `VITE_API_BASE_URL` in `frontend/.env`, defaulting in `src/services/api.ts` to `http://localhost:8000/api/v1`.

## Backend Architecture

### Application Startup and Lifespan

**`backend/app/main.py`** creates the FastAPI app with `title="Workflow API (MongoDB)", version="2.0.0"`.

Lifespan startup sequence:
1. Connect to MongoDB (`AsyncMongoClient`)
2. Ping MongoDB for connectivity
3. Inject global Mongo client (`set_mongo_client`)
4. Initialize Beanie ODM (skips indexes by default)
5. Validate workflow consistency (checks configs reference valid type_codes/state_codes)
6. Check Kafka health (non-blocking warning)
7. Initialize infrastructure (RabbitMQ, Kafka, APScheduler)
8. Initialize default system configs
9. Initialize Redis connection pool

Shutdown: stop Redis heartbeat, shutdown infrastructure (RabbitMQ/Kafka/scheduler), close MongoDB client.

**Middleware stack** (order of application):
1. `CORSMiddleware` (origins from config)
2. `RequestLoggingMiddleware` (always on — generates X-Request-ID/X-Trace-ID, logs request timing, silent for `/health`)
3. `DebugHttpLoggingMiddleware` (only when `APP_DEBUG=true`, logs full request/response bodies)
4. Exception handlers (registered via `setup_exception_handlers`)

**Routes mounted**: module routers under `/api/v1`, health routes under `/health` (with `/health`, `/health/ready`, `/health/live`).

### Module Layout and Layering

Backend modules live under `backend/app/modules/<module>/`. Most follow this shape:

| Directory | Responsibility |
|-----------|---------------|
| `api/` | FastAPI routers + dependency wiring |
| `schemas/` | Pydantic request/response models |
| `service/` or `application/` | Orchestration and business use cases |
| `domain/` | Business policies, rules, exceptions |
| `repository/` | Beanie documents and persistence helpers |

**Layering rules**: API → Service/Application → Repository/Domain. No upward dependencies.

**All 16 modules**:

| Module | Purpose |
|--------|---------|
| `workflow` | Configuration-driven state machine. Manages work types, states, `BusWorkItemDoc`, transitions, reassignment, `BusFlowLogDoc` audit history. Rules from `backend/app/configs/*.json`. |
| `test_specs` | Requirements, test cases, automation test cases, catalog/lab fields, comments, change logs, status projection. Main "what/how to test" domain. |
| `execution` | Runtime execution orchestration. Platform dispatches one current case, receives results from external agents, advances on terminal state. |
| `execution_plan` | Execution plans and plan items. Used by My Tasks, manual result backfill, single/batch automation dispatch. |
| `auth` | Login, JWT helpers, current-user dependencies, users, roles, permissions, navigation authorization. |
| `attachments` | File/object-storage metadata and attachment API. |
| `search` | Cross-module global search. |
| `project` | Project CRUD and stats. |
| `system_config` | Global configuration management + AI tool interfaces (text polish, connection test). |
| `ai_analysis` | AI-driven test case quality analysis (scoring, redundancy, coverage). |
| `test_case_collection` | Predefined test case collections. |
| `terminal` | Execution agent terminal management. |
| `failure_analysis` | Test execution failure analysis. |
| `notification` | Notifications (simplest module, constants + service only). |
| `redis` | Redis service registry/management. |
| `lineage` | Cross-module traceability graph views. |

### Shared Infrastructure Patterns

**Document Model Registration**: Decentralized pattern via `backend/app/shared/infrastructure/`:
- `bootstrap.py` — imports module packages to trigger Beanie Document registration
- `document_registry.py` — global list with `register_document_model()` / `get_document_models()`
- Modules register models in their `repository/models/__init__.py` by calling `register_document_model(SomeDoc)`

**API Router Registration**: Same decentralized pattern via `backend/app/shared/api/`:
- `router_registry.py` — global list with `register_router(router, prefix, tags)`
- Modules call `register_router()` in their `api/__init__.py`
- `main.py` imports all module API packages to trigger registration, then mounts collected routers

**Context System** (`backend/app/shared/context.py`):
- `TraceContext`: `request_id`, `trace_id`, `client_ip` — set by `RequestLoggingMiddleware`
- `OperationContext`: `actor_id`, `username`, `role_ids`, `permissions` — set by auth dependency injection
- API: `set_trace_context()`, `get_trace_context()`, `set_operation_context()`, `get_operation_context()`, `reset_context()`
- `trace_scope()` context manager for background tasks

**Exception Hierarchy** (`backend/app/shared/domain/exceptions.py`):
- `AppError` → HTTP 4xx/5xx based on subclass
  - `NotFoundError` → 404
  - `ConflictError` → 409
  - `ValidationError` → 400
  - `PermissionDeniedError` → 403
- Module-specific exceptions inherit from `AppError` (e.g., `WorkflowError`, `TestSpecsError`, `ExecutionPlanError`)
- Global exception handlers in `backend/app/shared/api/errors/handlers.py` — registered in order: module-specific → `AppError` → StarletteHTTPException → generic Exception

**API Response Envelope** (`backend/app/shared/api/schemas/base.py`):
```python
class APIResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None
```

**Error schema**: `{"error": str, "detail": Optional[str]}`

### Workflow System

- Configs in `backend/app/configs/*.json`: `global_config.json` (12 states), `requirement.json` (9 transitions), `test_case.json` (5 transitions)
- Rules: `type_code` + `from_state` + `action` → `to_state`
- Owner strategies: `KEEP`, `TO_CREATOR`, `TO_SPECIFIC_USER`
- Configs auto-sync (upsert) to MongoDB on startup
- Consistency validation at startup: ensures configured `type_code`, `from_state`, `to_state` exist

### Test Infrastructure

**Integration test conftest** (`backend/tests/integration/conftest.py`):
- `test_data_registry` — tracks created test data for cleanup
- `cleanup_test_data` (autouse) — cleans up after every test
- `app_with_lifespan` — FastAPI app with real MongoDB connection
- `admin_token` — login as `test_admin` (password `Admin@123`)
- `test_users` — 7 fixed integration test users (`integ_tpm`, `integ_reviewer`, `integ_dev`, `integ_qa`, `integ_tester`, `integ_auto_dev`, `integ_no_role`)
- Per-role authenticated clients: `client_admin`, `client_tpm`, `client_reviewer`, `client_dev`, `client_qa`, `client_tester`, `client_no_role`, `client_auto_dev`
- Test utilities in `backend/tests/integration/utils/`: `AuthenticatedClient`, `assert_response`, `assert_success`, `get_data`, `get_error`

**Unit tests**: No MongoDB dependency. Use fakes/mocks. Located in `backend/tests/unit/<module>/`.

### Architecture Tests

Located in `backend/tests/unit/architecture/`:
- `test_file_sizes.py` — enforces file size limits
- `test_module_boundaries.py` — enforces layering rules (no upward imports)
- `test_redundancy_governance.py` — catches code duplication
- `test_startup_composition.py` — validates startup sequence
- `test_status_projection_boundaries.py` — validates state projection boundaries

## Frontend Architecture

### Technology Stack
- React 19 + TypeScript + Vite (build tool)
- TailwindCSS 4 (utility classes + inline styles + CSS files)
- `@tanstack/react-query` (server state management)
- `next-themes` (dark/light mode)
- `recharts` (data visualization), `xterm` (terminal emulator)
- ESLint 9 (flat config)

### Routing Model

**Internal state-based routing** (no React Router). Pages are switched via a `PageType` union type in a `switch`/`case` block inside `AppContent`.

18 page types: `'requirements' | 'manualTestCases' | 'testCases' | 'agents' | 'roles' | 'roleGroup' | 'users' | 'profile' | 'myTasks' | 'permissions' | 'dashboard' | 'catalogLabs' | 'testPlanStudioDemo' | 'lineageView' | 'search' | 'collections' | 'projects' | 'systemConfig' | 'caseGovernance'`

### Provider Layer

```
QueryClientProvider (React Query, staleTime=30s, retry=1)
  -> ThemeProvider (next-themes, attribute="data-theme", default="light")
    -> AuthProvider (JWT in localStorage, user/permissions state)
      -> NavigationProvider (currentPage, visible nav items, permission filtering)
        -> AppContent
```

- **AuthProvider** (`src/providers/AuthProvider.tsx`): Manages JWT token, provides `isAuthenticated`, `currentUsername`, `currentUserId`, `currentUserRole`, `userPermissions`. On mount restores session from stored token. Supports user switching via 6 pre-configured test users.
- **NavigationProvider** (`src/providers/NavigationProvider.tsx`): Manages `currentPage`, computes `visibleNavItems` based on user permissions. Provides `handleWorkflowNavigate()` and `handleOpenLineage()`.
- **queryKeys** (`src/providers/queryKeys.ts`): React Query key factory for all domains.

### API Client

**`src/services/api.ts`**: Singleton `ApiClient` class using native `fetch()`.
- Base URL: `import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'`
- JWT stored in `localStorage` as `jwt_token`, sent as Bearer token
- Expects `{ code: number, message: string, data: T }` envelope
- 60+ methods grouped by backend feature (auth, requirements, test cases, workflow, execution, execution plans, catalog, RBAC, system config, AI, projects, search, lineage, collections, enums)

### Component Architecture

- **Single-file page components**: Most pages are single `.tsx` files in `src/components/` (e.g., `DashboardPage.tsx` at 48K, `TestExecutionPlanDemo.tsx` at 131K)
- **Subdirectory groups**: Complex features have subdirectories: `TestCaseBoard/`, `workflow/`, `lineage/`, `catalog/`, `projects/`, `test-plan/`, `failure-analysis/`
- **Shared UI**: `src/components/ui/` — `AIPolishButton`, `ModernCard`, `ModernStats`, `PageHero`, `PageToolbar`, `SplitDetailPanel`
- **Navigation**: `src/config/navigation.ts` — 18 nav items in 4 sections, filtered by permissions via `getVisibleNavItems()`
- **Types**: `src/types/app.ts` (PageType, NavItem), `src/types/index.ts` (~1406 lines, all domain types)

### Pre-configured Test Users

Defined in `src/config/users.ts` (password `Test@123`):
- `admin` (ADMIN), `tpm` (TPM), `reviewer` (REVIEWER), `dev` (MANUAL_DEV), `qa` (QA), `tester` (TESTER)

## Data and Workflow Notes

- MongoDB via Beanie ODM. Documents inherit from `Document`. Business docs use `is_deleted` soft-delete pattern.
- Auth helpers: `app.shared.auth` exports `get_current_user`, `require_permission`, `require_any_permission`, password/JWT helpers.
- API prefix: `/api/v1`. Unified response envelope: `{"code": 0, "message": "ok", "data": ...}`.
- Error responses use same envelope: `{"code": <status>, "message": "ErrorType", "data": {"error": "...", "detail": "..."}}`.

## Existing Documentation Worth Reading

- Root `README.md` — business overview, module descriptions, API route table, startup guide
- `backend/docs/` — VitePress documentation site (architecture, design docs, module docs, handover docs, conventions)
- `backend/app/configs/README.md` — workflow configuration documentation with diagrams
- `backend/app/modules/auth/README.md` — RBAC and auth behavior
- `backend/app/modules/test_specs/README.md` — requirements and test case domain
- `backend/app/modules/execution/README.md` — serial execution orchestration model
- `backend/app/modules/workflow/README.md` — workflow/state-machine details
- `backend/app/shared/rabbitmq/README.md` — RabbitMQ producer-only module
- `backend/app/shared/kafka/README.md` — Kafka four-layer architecture
- `backend/scripts/README.md` — script tools documentation
- `backend/docs/reference/conventions.md` — dev & architecture conventions
- `backend/docs/reference/api-conventions.md` — API conventions
- `backend/docs/reference/data-model-conventions.md` — data model conventions
- `backend/docs/reference/testing-conventions.md` — testing conventions
- `backend/docs/handover/new-engineer-onboarding.md` — onboarding guide
- `backend/docs/handover/change-checklist.md` — change checklist for developers
