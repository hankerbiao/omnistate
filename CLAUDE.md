# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DML V4 is a test-management platform with a FastAPI/MongoDB backend and a React/TypeScript frontend. The product connects test requirements, manual/automation test cases, execution plans, serial execution dispatch, result backfill, lineage/search, attachments, and JWT/RBAC-based access control.

## Common Commands

### Backend

```bash
# Install Python dependencies from the repository root
pip install -r requirements.txt

# Start the FastAPI service
cd backend
python -m app.main                  # serves on 0.0.0.0:8000

# Initialize core data
cd backend
python app/init_mongodb.py          # sync workflow/config data and base app data
python scripts/init_rbac.py         # initialize default roles/permissions
python scripts/create_user.py --user-id admin001 --username "系统管理员" --password 'Admin@123' --roles ADMIN --email admin@example.com --upsert

# Run tests
cd backend
pytest                              # all backend tests
pytest tests/unit/workflow/ -v      # a test directory
pytest tests/integration/ -v        # integration tests
pytest tests/unit/workflow/test_workflow_query_service.py -v
pytest tests/unit/workflow/test_workflow_query_service.py::test_name -v
pytest --cov=app                    # coverage

# Lint
cd backend
flake8
flake8 app/modules/execution/
flake8 --select=E,W,F
```

Backend lint configuration is in `backend/.flake8` (`max-line-length = 110`, `max-complexity = 12`, plus the listed ignores/excludes).

### Frontend

```bash
cd frontend
npm install
npm run dev                         # Vite dev server; default Vite port is 5173 unless overridden
npm run build                       # tsc -b && vite build
npm run lint                        # ESLint
npm run preview
```

There is no frontend test script in `frontend/package.json` at the time of writing.

### Documentation Site

```bash
cd docs
npm install
npm run docs:dev
npm run docs:build
npm run docs:preview
```

## Runtime Configuration

- Backend configuration is loaded from `backend/config.yaml` through `app.shared.config.get_settings()`; `backend/config.yaml.example` shows local defaults.
- Important backend sections include `app`, `mongodb`, `rabbitmq`, `kafka`, `minio`, `jwt`, `execution`, `tmms`, `terminal`, and `logging`.
- `backend/app/shared/db/config.py` is a compatibility shim over the unified YAML settings.
- Beanie index sync is skipped by default in startup when `SKIP_INDEX_SYNC=1`; run `python app/init_mongodb.py` or set `SKIP_INDEX_SYNC=0` when indexes must be synchronized.
- Frontend API base URL comes from `VITE_API_BASE_URL`, defaulting in `src/services/api.ts` to `http://localhost:8000/api/v1`.

## Backend Architecture

### Application Startup and Routing

- `backend/app/main.py` creates the FastAPI app, configures CORS, request/debug middleware, exception handlers, and includes the aggregate router.
- The lifespan hook connects MongoDB, sets the shared Mongo client, initializes Beanie document models, validates workflow config consistency, initializes shared infrastructure, and shuts all of that down on exit.
- `backend/app/shared/infrastructure/bootstrap.py` owns Beanie document model registration. If a module adds a Beanie `Document`, register it through that module's `DOCUMENT_MODELS` and include it in `get_document_models()`.
- `backend/app/shared/api/main.py` is the central API router registration point. Business routes are mounted under `/api/v1`; health is mounted under `/health`.
- API responses use the envelope from `app.shared.api.schemas.base.APIResponse`: `{"code": 0, "message": "ok", "data": ...}`.

### Module Layout and Layering

Backend modules live under `backend/app/modules/<module>/`. Most modules follow this shape:

- `api/`: FastAPI routers and dependency wiring
- `schemas/`: Pydantic request/response models
- `service/` or `application/`: orchestration and business use cases
- `domain/`: business policies/exceptions where present
- `repository/`: Beanie documents and persistence helpers

Keep route handlers thin: receive/validate inputs, apply auth dependencies, call service/application code, and return `APIResponse`. Business rules belong in service/application/domain layers, not directly in routes.

### Core Backend Modules

- `workflow`: configuration-driven state machine. It manages work types, workflow states/configs, `BusWorkItemDoc`, transitions, reassignment, and `BusFlowLogDoc` audit history. Workflow rules are sourced from `backend/app/configs/*.json` and validated at startup when initialized data exists.
- `test_specs`: requirements, test cases, automation test cases, catalog/lab fields, comments, change logs, and status projection behavior. It is the main “what to test / how to test” domain.
- `execution`: runtime execution orchestration. The platform dispatches one current case, receives progress/results from external agents, advances to the next case only after terminal case state, and keeps task/current-state plus historical execution data.
- `execution_plan`: execution plans and plan items used by My Tasks, manual result backfill, single/batch automation dispatch, and plan CRUD (`/api/v1/execution-plans/...`).
- `test_case_collection`: predefined test case collections used by the frontend collection page.
- `auth`: login, JWT helpers, current-user dependencies, users, roles, permissions, and navigation authorization.
- `attachments`: file/object-storage metadata and attachment API.
- `search` and `lineage`: cross-module global search and graph/traceability views.
- `terminal` and `failure_analysis`: terminal session and failure-analysis support modules; verify route registration before assuming they are exposed.

### Data and Workflow Notes

- MongoDB access is via Beanie models; many business documents use `is_deleted`, so query code should account for soft deletion.
- Workflow config consistency checks ensure configured `type_code`, `from_state`, and `to_state` values exist. Empty workflow collections only emit a startup warning so blank environments can boot.
- Auth helpers are exported from `app.shared.auth` (`get_current_user`, `require_permission`, `require_any_permission`, password/JWT helpers).

## Frontend Architecture

- The frontend is a React 19 + TypeScript + Vite single-page app.
- `src/App.tsx` owns authentication state, current page state, current user/permission loading, user switching, and page rendering through a `PageType` switch.
- `src/components/AppShell.tsx` composes the persistent `Sidebar` + `Topbar` layout and maps page keys to page titles/descriptions.
- Navigation metadata is centralized in `src/config/navigation.ts`; `getVisibleNavItems()` filters items using permissions returned from the backend, and `resolveDefaultPage()` chooses the initial page after login.
- Shared app/page types are in `src/types/app.ts`; API/domain types are in `src/types/index.ts`; test-plan-specific types are in `src/types/testPlan.ts`.
- `src/services/api.ts` is the typed fetch client. It stores the JWT in `localStorage` under `jwt_token`, sends it as a Bearer token, unwraps backend error envelopes where possible, and exposes methods grouped by backend feature.
- Major feature components are under `src/components/`; subfolders group larger feature areas such as `TestCaseBoard/`, `workflow/`, `lineage/`, `catalog/`, and shared `ui/` components.

## Existing Documentation Worth Reading

- Root `README.md`: current backend-oriented business overview and local setup notes.
- `backend/README.md`: backend module responsibilities, startup flow, API prefixes, and execution-module caveats.
- `backend/app/modules/workflow/README.md`: workflow/state-machine details.
- `backend/app/modules/test_specs/README.md`: requirements and test case domain details.
- `backend/app/modules/execution/README.md`: serial execution orchestration model.
- `backend/app/modules/auth/README.md`: RBAC and auth behavior.
- `docs/`: VitePress documentation source for broader architecture/API guides.

No Cursor rules (`.cursor/rules/` or `.cursorrules`) or Copilot instructions (`.github/copilot-instructions.md`) were found during this initialization.
