# Kafka Runtime Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split Kafka support into configuration, runtime, module handlers, and a dedicated worker process without breaking current task dispatch.

**Architecture:** Keep producer usage available to the API process through the shared infrastructure registry, but move consumer concerns into a dedicated worker runtime. Route topic payloads through per-module handler registrations so shared Kafka code stays infrastructure-only.

**Tech Stack:** FastAPI, Beanie ODM, kafka-python, Pydantic, pytest

---

### Task 1: Add Kafka runtime architecture tests

**Files:**
- Create: `tests/unit/shared/kafka/test_kafka_runtime_architecture.py`

**Step 1: Write the failing test**

Add tests for Kafka config subscriptions, topic routing, and worker bootstrap orchestration.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/shared/kafka/test_kafka_runtime_architecture.py -v`
Expected: FAIL because the new runtime files do not exist yet.

**Step 3: Write minimal implementation**

Create the new Kafka runtime modules and worker entrypoint needed by the tests.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/shared/kafka/test_kafka_runtime_architecture.py -v`
Expected: PASS.

### Task 2: Split producer and consumer responsibilities

**Files:**
- Modify: `app/shared/kafka/config.py`
- Modify: `app/shared/kafka/__init__.py`
- Modify: `app/shared/kafka/kafka_message_manager.py`
- Create: `app/shared/kafka/producer.py`
- Create: `app/shared/kafka/consumer.py`
- Create: `app/shared/kafka/router.py`
- Create: `app/shared/kafka/dead_letter.py`

**Step 1: Write the failing test**

Use the runtime architecture tests as the contract for the split.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/shared/kafka/test_kafka_runtime_architecture.py -v`
Expected: FAIL while imports or behavior are missing.

**Step 3: Write minimal implementation**

Move producer-only behavior into `producer.py`, add a generic consumer runner, add topic routing and dead-letter support, and keep compatibility exports for existing imports.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/shared/kafka/test_kafka_runtime_architecture.py -v`
Expected: PASS.

### Task 3: Add execution module Kafka integration point

**Files:**
- Create: `app/modules/execution/application/kafka_handlers.py`
- Create: `app/modules/execution/schemas/kafka_events.py`

**Step 1: Write the failing test**

Cover registration of the execution result topic through the worker bootstrap path.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/shared/kafka/test_kafka_runtime_architecture.py -v`
Expected: FAIL because execution handlers or event schemas are missing.

**Step 3: Write minimal implementation**

Add an execution result event schema and register a module-scoped Kafka handler that can later call execution services.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/shared/kafka/test_kafka_runtime_architecture.py -v`
Expected: PASS.

### Task 4: Add dedicated worker entrypoint and keep API producer lifecycle

**Files:**
- Create: `app/workers/__init__.py`
- Create: `app/workers/kafka_worker_main.py`
- Modify: `app/shared/infrastructure/registry.py`

**Step 1: Write the failing test**

Use the worker bootstrap test to lock the lifecycle sequence.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/shared/kafka/test_kafka_runtime_architecture.py -v`
Expected: FAIL while the worker runtime does not orchestrate init/build/run/shutdown.

**Step 3: Write minimal implementation**

Build a dedicated worker startup path and keep the API-side infrastructure registry limited to producer usage and scheduler lifecycle.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/shared/kafka/test_kafka_runtime_architecture.py -v`
Expected: PASS.
