# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A configuration-driven workflow/state machine system built with Python, FastAPI, Beanie ODM, and MongoDB. Manages business item lifecycles through configurable state transitions without hardcoding workflow logic.

## Common Commands

```bash
# Run MongoDB initialization (seeds config from JSON files)
cd backend && python init_mongodb.py

# Start backend service
cd backend && python -m app.main

# Start frontend development server
cd frontend && npm install && npm run dev
```

## Architecture

### Stack
- **Backend**: FastAPI + Beanie ODM (MongoDB async driver)
- **Frontend**: Vite + React + TypeScript
- **Database**: MongoDB (async)

### Directory Structure

```
backend/
├── app/
│   ├── api/              # FastAPI routes, schemas, error handlers
│   ├── configs/          # JSON workflow configurations
│   ├── core/             # Logger, MongoDB client
│   ├── db/               # Database configuration (settings)
│   ├── models/           # Beanie Document models & Pydantic schemas
│   ├── services/         # Business logic (AsyncWorkflowService)
│   ├── init_mongodb.py   # DB initialization script
│   └── main.py           # FastAPI app entry point
frontend/                 # Vite + React + TypeScript app
```

### Key Models (`backend/app/models/`)

**System Config Documents**:
- `SysWorkTypeDoc` - Business item types (REQUIREMENT, TEST_CASE)
- `SysWorkflowStateDoc` - Workflow states with `is_end` flag
- `SysWorkflowConfigDoc` - Transition rules: `type_code` + `from_state` + `action` → `to_state`

**Business Documents**:
- `BusWorkItemDoc` - Stateful items with `current_state`, `current_owner_id`, `creator_id`
- `BusFlowLogDoc` - Audit trail linking to work items

### Core Service (`backend/app/services/workflow_service.py`)

Entry points:
- `create_item()` - Creates item in DRAFT state
- `handle_transition()` - Validates and executes state transitions
- `get_item_with_transitions()` - Returns item + available next actions
- `list_items()` - Filters by type_code, state, owner_id, creator_id (OR logic)

### Configuration-Driven Design

Workflow rules defined in `backend/app/configs/*.json`:
```json
{
  "work_types": [["REQUIREMENT", "需求"]],
  "workflow_configs": {
    "REQUIREMENT": [
      {
        "from_state": "DRAFT",
        "action": "SUBMIT",
        "to_state": "PENDING_AUDIT",
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

### Data Flow

1. `main.py` lifespan handler initializes MongoDB connection and Beanie ODM
2. `init_mongodb.py` seeds workflow rules from JSON configs into MongoDB
3. `AsyncWorkflowService.create_item()` creates item with DRAFT state
4. `AsyncWorkflowService.handle_transition()` validates rules, updates state/owner, logs to `BusFlowLogDoc`
5. Queries filter by `is_deleted == false`

### API Endpoints (prefix: `/api/v1`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/work-items/types` | List work types |
| GET | `/work-items/states` | List workflow states |
| POST | `/work-items` | Create new item |
| GET | `/work-items` | List items (filterable) |
| GET | `/work-items/{id}` | Get item details |
| POST | `/work-items/{id}/transition` | Execute state transition |
| POST | `/work-items/{id}/reassign` | Reassign owner |
| GET | `/work-items/{id}/logs` | Get transition history |
| GET | `/work-items/{id}/transitions` | Get available actions |

### Database Settings

Configured in `backend/app/db/config.py`:
- `MONGO_URI`: Default `mongodb://10.17.154.252:27018`
- `MONGO_DB_NAME`: Default `workflow_db`