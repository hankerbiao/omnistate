# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A configuration-driven workflow/state machine system built with Python, SQLModel, and PostgreSQL. The system manages business item lifecycles through configurable state transitions without hardcoding workflow logic.

## Common Commands

```bash
# Run workflow tests
python test_complex_workflows.py

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Core Components

**Models (`models/`)**
- `system.py` - System configuration tables: `SysWorkType`, `SysWorkflowState`, `SysWorkflowConfig`, and `OwnerStrategy` enum
- `business.py` - Business entities: `BusWorkItem` (stateful items) and `BusFlowLog` (audit trail)

**Services (`services/`)**
- `workflow_service.py` - Core FSM engine. Entry points:
  - `create_item()` - Create new business item in DRAFT state
  - `handle_transition()` - Execute state transitions with validation
  - `get_next_transition()` - Query transition rules from config

**Database (`db/`)**
- `relational.py` - Contains `init_db()` (DDL) and `init_mock_config()` (seeding from JSON)

### Configuration-Driven Design

All workflow rules are defined in `configs/workflow_initial_data.json`:
- `work_types` - Business item types (REQUIREMENT, TEST_CASE)
- `states` - Valid states (DRAFT, PENDING_AUDIT, etc.)
- `workflow_configs` - Transition rules defining from_state + action → to_state

To add a new workflow:
1. Add type to `work_types`
2. Add states to `states`
3. Define transitions in `workflow_configs` with `target_owner_strategy` (KEEP, TO_CREATOR, TO_SPECIFIC_USER) and `required_fields`

### Owner Strategy Patterns

- `KEEP` - Maintain current owner
- `TO_CREATOR` - Reassign to item creator
- `TO_SPECIFIC_USER` - Use `target_owner_id` from form_data

### Data Flow

1. `init_db()` creates tables from SQLModel metadata
2. `init_mock_config()` seeds workflow rules from JSON
3. `WorkflowService.create_item()` creates item with DRAFT state
4. `WorkflowService.handle_transition()` validates and executes state changes
5. Each transition logs to `BusFlowLog` for audit trail