"""独立 Kafka worker 进程入口。

这个模块用于启动一个独立于 FastAPI API 进程之外的 Kafka worker。
worker 会初始化 MongoDB/Beanie、注册 Kafka topic 处理器、维护执行代理心跳，
然后持续消费 Kafka 消息。
"""

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
    # Worker 进程也需要初始化 Beanie 模型，否则无法使用 ODM 访问 MongoDB。
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
    """初始化 worker 运行时资源。"""
    global _mongo_client
    global _worker_heartbeat_task
    log.info("Initializing Kafka worker runtime")

    # 连接 MongoDB，并把客户端注入到全局上下文，供事务或底层访问使用。
    client = AsyncMongoClient(settings.MONGO_URI)
    await client.admin.command("ping")
    set_mongo_client(client)

    # 初始化 Beanie ODM，注册 worker 会访问到的全部文档模型。
    await init_beanie(
        database=client[settings.MONGO_DB_NAME],
        document_models=DOCUMENT_MODELS,
    )

    # 启动前校验 workflow 配置，避免 worker 消费到消息后才发现配置错误。
    await validate_workflow_consistency()

    # Kafka worker 内部仍可能需要发送 Kafka 消息，因此只初始化 Kafka producer。
    await initialize_kafka_producer_only()

    # 将 worker 标记为在线，并启动后台心跳任务。
    await upsert_kafka_worker_presence(status="ONLINE")
    _worker_heartbeat_task = asyncio.create_task(_run_worker_heartbeat_loop())
    _mongo_client = client


async def shutdown_worker_runtime() -> None:
    """关闭 worker 运行时资源。"""
    global _mongo_client
    global _worker_heartbeat_task

    # 先取消心跳任务，避免关闭过程中继续写入在线状态。
    if _worker_heartbeat_task is not None:
        _worker_heartbeat_task.cancel()
        try:
            await _worker_heartbeat_task
        except asyncio.CancelledError:
            pass
        _worker_heartbeat_task = None

    # 标记 worker 离线，再关闭消息基础设施和 Mongo 连接。
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
    """周期性刷新 worker 在线状态。"""
    interval = get_kafka_worker_heartbeat_interval_seconds()
    while True:
        try:
            # 心跳通过 upsert 保持幂等，多次执行只刷新同一个 worker 记录。
            await upsert_kafka_worker_presence(status="ONLINE")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception(f"Kafka worker heartbeat failed: {exc}")
        await asyncio.sleep(interval)


def build_kafka_worker_runner() -> KafkaConsumerRunner:
    """构建 Kafka consumer runner，并注册 topic 处理器。"""
    config = load_kafka_config()
    registry = KafkaTopicHandlerRegistry()
    # execution 模块负责注册自己的 Kafka 消息处理函数。
    register_execution_kafka_handlers(registry)
    runner = KafkaConsumerRunner(config=config, router=registry)
    # 按配置订阅需要消费的 Kafka topic。
    runner.register_configured_subscriptions()
    return runner


@asynccontextmanager
async def worker_runtime():
    """worker 生命周期上下文，保证启动和关闭成对执行。"""
    await initialize_worker_runtime()
    try:
        yield
    finally:
        await shutdown_worker_runtime()


async def run_worker() -> None:
    """持续运行 Kafka worker。"""
    async with worker_runtime():
        runner = build_kafka_worker_runner()
        await runner.run_forever()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
