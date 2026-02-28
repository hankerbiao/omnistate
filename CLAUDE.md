# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **dual-stack system** consisting of:
1. **Backend**: Configuration-driven workflow/state machine service (Python + FastAPI + Beanie ODM + MongoDB)
2. **Frontend**: Server Test Case Designer web application (React + TypeScript + Vite)

The backend manages business item lifecycles through JSON-configured state transitions. The frontend provides a UI for managing test requirements and test cases for server hardware validation (DDR5 memory testing, etc.).

## Quick Start Commands

```bash
# Backend setup
cd backend
python init_mongodb.py              # Initialize MongoDB with workflow configs
python scripts/init_rbac.py         # Initialize RBAC (roles/permissions)
python scripts/create_user.py       # Create admin user
python -m app.main                  # Start backend (port 8000)

# Frontend setup (in another terminal)
cd frontend
npm install
npm run dev                         # Start dev server (port 3000)
```

## Architecture

### Tech Stack
- **Backend**: FastAPI + Beanie ODM (MongoDB async) + Pydantic
- **Frontend**: React 19 + TypeScript + Vite 6 + TailwindCSS 4
- **Database**: MongoDB (async with Beanie ODM)
- **Testing**: pytest (backend) + FastAPI TestClient
- **Linting**: Flake8 (Python, max-line-length: 110)

### Project Structure

```
/Users/libiao/Desktop/github/dmlv4/
├── backend/                          # Python FastAPI backend
│   ├── app/
│   │   ├── modules/                  # Business modules (workflow, auth, test_specs, assets)
│   │   │   ├── workflow/             # Core workflow/state machine
│   │   │   ├── auth/                 # RBAC (User, Role, Permission)
│   │   │   ├── test_specs/           # Test requirements & cases
│   │   │   └── assets/               # Component library & DUT management
│   │   ├── shared/                   # Shared infrastructure
│   │   │   ├── api/                  # Routes, errors, schemas
│   │   │   ├── core/                 # Logger, Mongo client
│   │   │   └── db/                   # Database config
│   │   ├── configs/                  # JSON workflow configurations
│   │   ├── main.py                   # FastAPI app entry
│   │   └── init_mongodb.py           # MongoDB seed script
│   ├── scripts/
│   │   ├── init_rbac.py              # RBAC initialization
│   │   └── create_user.py            # User creation helper
│   └── tests/                        # pytest tests
│       ├── unit/                     # Unit tests (service/domain)
│       ├── integration/              # Integration tests (API)
│       └── fakes/                    # Test fakes/mocks
│
├── frontend/                         # React TypeScript frontend
│   ├── src/
│   │   ├── App.tsx                   # Main component with all views
│   │   ├── types.ts                  # TypeScript interfaces
│   │   └── main.tsx                  # React entry point
│   ├── package.json                  # Dependencies & scripts
│   └── vite.config.ts                # Vite configuration
│
├── docs/                             # Architecture & API documentation
│   ├── 项目架构规范.md                # Backend architecture spec
│   ├── 后端接口说明.md               # API documentation
│   └── 测试用例创建需求和测试用例字段设计.md
│
├── requirements.txt                  # Python dependencies
├── .flake8                          # Python linting config
└── CLAUDE.md                         # This file
```

### Backend Architecture (Layered Design)

**Strong layering rules**: API → Service → Repository/Domain (no upward dependencies)

#### Key Models (`app/modules/*/repository/models/`)

**System Config Documents** (MongoDB collections):
- `SysWorkTypeDoc` - Business item types (REQUIREMENT, TEST_CASE)
- `SysWorkflowStateDoc` - Workflow states with `is_end` flag
- `SysWorkflowConfigDoc` - Transition rules: `type_code` + `from_state` + `action` → `to_state`

**Business Documents**:
- `BusWorkItemDoc` - Stateful items with `current_state`, `current_owner_id`, `creator_id`
- `BusFlowLogDoc` - Audit trail linking to work items

**Module-Specific Documents**:
- `TestRequirementDoc`, `TestCaseDoc` (test_specs module)
- `UserDoc`, `RoleDoc`, `PermissionDoc` (auth module - RBAC)
- `ComponentLibraryDoc`, `DutDoc`, `TestPlanComponentDoc` (assets module)

### Core Services

**Workflow Service** (`modules/workflow/service/workflow_service.py`):
- `create_item()` - Creates item in DRAFT state
- `handle_transition()` - Validates and executes state transitions
- `get_item_with_transitions()` - Returns item + available next actions
- `list_items()` - Filters by type_code, state, owner_id, creator_id (OR logic)

**Other Services** (per module):
- `TestCaseService` (test_specs module)
- `UserService`, `RoleService` (auth module)
- `AssetService` (assets module)

### Configuration-Driven Workflow Design

Workflow rules defined in JSON configs (`app/configs/*.json`), then seeded to MongoDB:

```json
{
  "work_types": [["REQUIREMENT", "需求"], ["TEST_CASE", "测试用例"]],
  "workflow_configs": {
    "REQUIREMENT": [
      {
        "from_state": "DRAFT",
        "action": "SUBMIT",
        "to_state": "PENDING_REVIEW",
        "target_owner_strategy": "TO_SPECIFIC_USER",
        "required_fields": ["priority", "target_owner_id"]
      }
    ]
  }
}
```

**Owner Strategy Options**:
- `KEEP` - Maintain current owner
- `TO_CREATOR` - Reassign to item creator
- `TO_SPECIFIC_USER` - Use `target_owner_id` from form_data

**To add new workflow type**:
1. Create JSON config in `app/configs/new_type.json`
2. Run `python init_mongodb.py` to seed MongoDB
3. Frontend can now use the new type

### Data Flow

1. **Startup**: `main.py` lifespan handler initializes MongoDB + Beanie ODM with all document models
2. **Seeding**: `init_mongodb.py` seeds workflow rules from JSON configs into MongoDB
3. **Item Creation**: `AsyncWorkflowService.create_item()` → item in DRAFT state
4. **State Transition**: `handle_transition()` validates rules → updates state/owner → logs to `BusFlowLogDoc`
5. **Deletion**: All queries filter by `is_deleted == false` (soft delete pattern)

### Frontend Architecture (Single-File Component)

The React app uses a single-file architecture with view state management in `src/App.tsx`:

**Views** (managed by `currentView` state):
- `req_list` - Test requirement list
- `req_form` - Create/edit requirement
- `req_detail` - Requirement details
- `case_form` - Create test case
- `user_mgmt` - User management

**AI Integration**: Local AI service at `http://172.17.167.43:8000/v1` with model `/models/coder/minimax/MiniMax-M2` for text polishing and test step generation

### API Endpoints (`/api/v1`)

**Workflow Module** (`/work-items`):
- `GET /types` - List work types
- `GET /states` - List workflow states
- `POST` - Create item
- `GET` - List items (filterable)
- `GET /{id}` - Get details
- `POST /{id}/transition` - Execute state transition
- `POST /{id}/reassign` - Reassign owner
- `GET /{id}/logs` - Get transition history
- `GET /{id}/transitions` - Get available actions

**Test Specs Module** (`/requirements`, `/test-cases`):
- Full CRUD operations for test requirements and test cases

**Auth Module** (`/auth/users`, `/auth/roles`, `/auth/permissions`):
- RBAC management (users, roles, permissions, role assignments)

**Assets Module** (`/assets/components`, `/assets/duts`):
- Component library and DUT (Device Under Test) management

**Common**:
- `GET /health` - Health check

See `docs/后端接口说明.md` for complete API documentation

## Common Development Commands

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
cd backend
python init_mongodb.py              # Seed workflow configs
python scripts/init_rbac.py         # Initialize roles/permissions
python scripts/create_user.py       # Create admin user

# Run development server
python -m app.main                  # Port 8000

# Run tests
cd backend
pytest                              # All tests
pytest tests/unit/workflow/         # Specific module
pytest tests/integration/           # Integration tests
pytest -v --cov=app                 # With coverage

# Lint
flake8                              # Max line length: 110
```

### Frontend
```bash
cd frontend
npm install                         # Install dependencies
npm run dev                         # Dev server (port 3000)
npm run build                       # Production build
npm run preview                     # Preview build
npm run lint                        # Type check (tsc --noEmit)
npm run clean                       # Clean dist
```

## Testing Strategy

### Backend Testing
- **Unit Tests** (`tests/unit/`): Service and domain logic with fake objects
- **Integration Tests** (`tests/integration/`): API endpoint testing with FastAPI TestClient
- **Test Patterns**: Uses fakes for MongoDB, pytest fixtures, async testing
- **Fakes**: `tests/fakes/workflow.py` provides fake models for testing

### Running Specific Tests
```bash
cd backend
pytest tests/unit/workflow/test_workflow_service.py -v
pytest tests/unit/auth/test_jwt_auth.py -v
pytest tests/integration/test_api_workflow.py -v
```

## Environment Configuration

### Backend (`app/shared/db/config.py`)
```python
MONGO_URI: str = "mongodb://10.17.154.252:27018"
MONGO_DB_NAME: str = "workflow_db"
CORS_ORIGINS: list[str] = ["*"]
```

Override with `.env` file (not tracked by git).

### Frontend (`.env.local`)
```
APP_URL=http://localhost:3000
GEMINI_API_KEY=your_key_here
```

## Development Guidelines

### Adding New Module
1. Create `app/modules/<new_module>/` with: `api/`, `schemas/`, `service/`, `domain/`, `repository/models/`
2. Add routes to `app/shared/api/main.py`
3. Register document models in `app/main.py` lifespan handler
4. Add tests in `tests/unit/<new_module>/`

### Adding New Workflow Type
1. Create `app/configs/<type>.json` with `work_types` and `workflow_configs`
2. Run `python init_mongodb.py` to seed to MongoDB
3. No code changes needed - frontend can immediately use new type

### Code Standards
- **Backend**: Follow layered architecture (API→Service→Repository), use domain exceptions, no MongoDB细节 in API layer
- **Frontend**: Single-file component architecture with view state management
- **Python**: Max line length 110, max complexity 12, follow FastAPI best practices
- **Testing**: Unit tests for services/domains, integration tests for APIs

## Documentation

- **Backend Architecture**: `docs/项目架构规范.md`
- **API Documentation**: `docs/后端接口说明.md`
- **Test Specs Design**: `docs/测试用例创建需求和测试用例字段设计.md`
- **Backend README**: `backend/README.md`
- **Frontend README**: `frontend/CLAUDE.md`