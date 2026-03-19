"""Dedicated Kafka worker entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.main import validate_workflow_consistency
from app.modules.execution.application.worker_presence import (
    get_kafka_worker_heartbeat_interval_seconds,
    upsert_kafka_worker_presence,
    mark_kafka_worker_offline,
)
from app.modules.auth.repository.models import NavigationPageDoc, PermissionDoc, RoleDoc, UserDoc
from app.modules.execution.application.kafka_handlers import register_execution_kafka_handlers
from app.modules.execution.repository.models import (
    ExecutionAgentDoc,
    ExecutionEventDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.test_specs.repository.models import (
    AutomationTestCaseDoc,
    TestCaseDoc,
    TestRequirementDoc,
)
from app.modules.workflow.repository.models import (
    BusFlowLogDoc,
    BusWorkItemDoc,
    SysWorkflowConfigDoc,
    SysWorkflowStateDoc,
    SysWorkTypeDoc,
)
from app.shared.core.logger import log
from app.shared.core.mongo_client import set_mongo_client
from app.shared.db.config import settings
from app.shared.infrastructure import initialize_kafka_producer_only, shutdown_infrastructure
from app.shared.kafka import KafkaConsumerRunner, KafkaTopicHandlerRegistry, load_kafka_config


DOCUMENT_MODELS = [
    SysWorkTypeDoc,
    SysWorkflowStateDoc,
    SysWorkflowConfigDoc,
    BusWorkItemDoc,
    BusFlowLogDoc,
    TestRequirementDoc,
    TestCaseDoc,
    AutomationTestCaseDoc,
    ExecutionAgentDoc,
    ExecutionEventDoc,
    ExecutionTaskDoc,
    ExecutionTaskCaseDoc,
    UserDoc,
    RoleDoc,
    PermissionDoc,
    NavigationPageDoc,
]

_mongo_client: AsyncMongoClient | None = None
_worker_heartbeat_task: asyncio.Task | None = None


async def initialize_worker_runtime() -> None:
    """Initialize Mongo and Beanie for the worker process."""
    global _mongo_client
    global _worker_heartbeat_task
    log.info("Initializing Kafka worker runtime")
    client = AsyncMongoClient(settings.MONGO_URI)
    await client.admin.command("ping")
    set_mongo_client(client)
    await init_beanie(
        database=client[settings.MONGO_DB_NAME],
        document_models=DOCUMENT_MODELS,
    )
    await validate_workflow_consistency()
    await initialize_kafka_producer_only()
    await upsert_kafka_worker_presence(status="ONLINE")
    _worker_heartbeat_task = asyncio.create_task(_run_worker_heartbeat_loop())
    _mongo_client = client


async def shutdown_worker_runtime() -> None:
    """Close worker runtime resources."""
    global _mongo_client
    global _worker_heartbeat_task
    if _worker_heartbeat_task is not None:
        _worker_heartbeat_task.cancel()
        try:
            await _worker_heartbeat_task
        except asyncio.CancelledError:
            pass
        _worker_heartbeat_task = None
    await mark_kafka_worker_offline()
    await shutdown_infrastructure()
    if _mongo_client is not None:
        close_result = _mongo_client.close()
        if hasattr(close_result, "__await__"):
            await close_result
        _mongo_client = None
    set_mongo_client(None)
    log.info("Kafka worker runtime stopped")


async def _run_worker_heartbeat_loop() -> None:
    interval = get_kafka_worker_heartbeat_interval_seconds()
    while True:
        try:
            await upsert_kafka_worker_presence(status="ONLINE")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception(f"Kafka worker heartbeat failed: {exc}")
        await asyncio.sleep(interval)


def build_kafka_worker_runner() -> KafkaConsumerRunner:
    """Build the worker consumer runner with registered topic handlers."""
    config = load_kafka_config()
    registry = KafkaTopicHandlerRegistry()
    register_execution_kafka_handlers(registry)
    runner = KafkaConsumerRunner(config=config, router=registry)
    runner.register_configured_subscriptions()
    return runner


@asynccontextmanager
async def worker_runtime():
    await initialize_worker_runtime()
    try:
        yield
    finally:
        await shutdown_worker_runtime()


async def run_worker() -> None:
    """Run the Kafka worker forever."""
    async with worker_runtime():
        runner = build_kafka_worker_runner()
        await runner.run_forever()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
