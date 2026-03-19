"""Dedicated Kafka worker entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.main import validate_workflow_consistency
from app.modules.auth.repository.models import NavigationPageDoc, PermissionDoc, RoleDoc, UserDoc
from app.modules.execution.application.kafka_handlers import register_execution_kafka_handlers
from app.modules.execution.repository.models import (
    ExecutionAgentDoc,
    ExecutionEventDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
    ExecutionTaskRunCaseDoc,
    ExecutionTaskRunDoc,
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
    ExecutionTaskRunDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskRunCaseDoc,
    UserDoc,
    RoleDoc,
    PermissionDoc,
    NavigationPageDoc,
]

_mongo_client: AsyncMongoClient | None = None


async def initialize_worker_runtime() -> None:
    """Initialize Mongo and Beanie for the worker process."""
    global _mongo_client
    log.info("Initializing Kafka worker runtime")
    client = AsyncMongoClient(settings.MONGO_URI)
    await client.admin.command("ping")
    set_mongo_client(client)
    await init_beanie(
        database=client[settings.MONGO_DB_NAME],
        document_models=DOCUMENT_MODELS,
    )
    await validate_workflow_consistency()
    _mongo_client = client


async def shutdown_worker_runtime() -> None:
    """Close worker runtime resources."""
    global _mongo_client
    if _mongo_client is not None:
        close_result = _mongo_client.close()
        if hasattr(close_result, "__await__"):
            await close_result
        _mongo_client = None
    set_mongo_client(None)
    log.info("Kafka worker runtime stopped")


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
    import asyncio

    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
