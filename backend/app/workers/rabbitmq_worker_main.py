"""Dedicated RabbitMQ worker entrypoint.

该 Worker 用于消费测试框架通过 RabbitMQ 上报的测试事件和结果消息。
与 Kafka worker 类似，作为独立进程运行。
"""

from __future__ import annotations

import asyncio
import signal
from contextlib import asynccontextmanager

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.main import validate_workflow_consistency
from app.modules.auth.repository.models import NavigationPageDoc, PermissionDoc, RoleDoc, UserDoc
from app.modules.execution.application.rabbitmq_handlers import (
    register_execution_rabbitmq_handlers,
)
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
from app.shared.infrastructure import initialize_infrastructure, shutdown_infrastructure
from app.shared.rabbitmq import RabbitMQConsumerRunner, RabbitMQHandlerRegistry, load_rabbitmq_config


# 所有需要初始化的文档模型
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
_worker: RabbitMQConsumerRunner | None = None
_shutdown_event: asyncio.Event | None = None


async def initialize_worker_runtime() -> None:
    """Initialize Mongo and Beanie for the worker process."""
    global _mongo_client
    log.info("Initializing RabbitMQ worker runtime")

    # 连接 MongoDB
    client = AsyncMongoClient(settings.MONGO_URI)
    await client.admin.command("ping")
    set_mongo_client(client)

    # 初始化 Beanie 文档模型
    await init_beanie(
        database=client[settings.MONGO_DB_NAME],
        document_models=DOCUMENT_MODELS,
    )

    # 校验 workflow 配置一致性
    await validate_workflow_consistency()

    # 初始化基础设施 (如 Kafka producer 等)
    await initialize_infrastructure()

    _mongo_client = client
    log.info("RabbitMQ worker runtime initialized")


async def shutdown_worker_runtime() -> None:
    """Close worker runtime resources."""
    global _mongo_client
    log.info("Shutting down RabbitMQ worker runtime")

    # 关闭 RabbitMQ consumer
    global _worker
    if _worker is not None:
        await _worker.stop()
        _worker = None

    # 关闭基础设施
    await shutdown_infrastructure()

    # 关闭 MongoDB 连接
    if _mongo_client is not None:
        close_result = _mongo_client.close()
        if hasattr(close_result, "__await__"):
            await close_result
        _mongo_client = None
        set_mongo_client(None)

    log.info("RabbitMQ worker runtime stopped")


def build_rabbitmq_worker_runner() -> RabbitMQConsumerRunner:
    """Build the worker consumer runner with registered handlers.

    Returns:
        配置好的 RabbitMQ consumer runner
    """
    config = load_rabbitmq_config()
    registry = RabbitMQHandlerRegistry()

    # 注册执行模块的处理器
    register_execution_rabbitmq_handlers(registry)

    runner = RabbitMQConsumerRunner(config=config, registry=registry)
    return runner


@asynccontextmanager
async def worker_runtime():
    """Worker 运行时上下文管理器。

    负责初始化和清理资源。
    """
    await initialize_worker_runtime()
    try:
        yield
    finally:
        await shutdown_worker_runtime()


async def run_worker() -> None:
    """Run the RabbitMQ worker forever."""
    global _worker, _shutdown_event

    _shutdown_event = asyncio.Event()

    # 设置信号处理
    def signal_handler(sig):
        log.info(f"Received signal {sig}, initiating graceful shutdown...")
        if _shutdown_event:
            _shutdown_event.set()

    # 注册信号处理器
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        except NotImplementedError:
            # Windows 不支持 add_signal_handler
            pass

    async with worker_runtime():
        _worker = build_rabbitmq_worker_runner()
        await _worker.start()

        log.info("RabbitMQ worker started, waiting for messages...")

        # 等待关闭信号
        try:
            await _worker.run_forever()
        except asyncio.CancelledError:
            log.info("RabbitMQ worker cancelled")
        finally:
            if _worker and _worker.is_running:
                await _worker.stop()

    log.info("RabbitMQ worker exited")


def main() -> None:
    """Worker 主入口。"""
    log.info("Starting RabbitMQ worker...")
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        log.info("RabbitMQ worker stopped by keyboard interrupt")
    except Exception as e:
        log.exception(f"RabbitMQ worker failed: {e}")
        raise


if __name__ == "__main__":
    main()