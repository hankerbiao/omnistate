"""共享基础设施模块。

保持包导入轻量，避免导入 bootstrap 时急切拉起 registry 及 execution 依赖。
"""

from typing import Any


def get_infrastructure_registry() -> Any:
    from .registry import get_infrastructure_registry as _get_infrastructure_registry

    return _get_infrastructure_registry()


def get_rabbitmq_manager() -> Any:
    from .registry import get_rabbitmq_manager as _get_rabbitmq_manager

    return _get_rabbitmq_manager()


def get_kafka_manager() -> Any:
    from .registry import get_kafka_manager as _get_kafka_manager

    return _get_kafka_manager()


async def initialize_infrastructure(bootstrap_servers: list[str] | None = None) -> None:
    from .registry import initialize_infrastructure as _initialize_infrastructure

    await _initialize_infrastructure(bootstrap_servers)


async def initialize_kafka_producer_only(bootstrap_servers: list[str] | None = None) -> None:
    from .registry import initialize_kafka_producer_only as _initialize_kafka_producer_only

    await _initialize_kafka_producer_only(bootstrap_servers)


async def shutdown_infrastructure() -> None:
    from .registry import shutdown_infrastructure as _shutdown_infrastructure

    await _shutdown_infrastructure()


def __getattr__(name: str) -> Any:
    if name in {"InfrastructureRegistry", "InfrastructureStatus"}:
        from . import registry

        return getattr(registry, name)
    raise AttributeError(name)


__all__ = [
    "InfrastructureRegistry",
    "InfrastructureStatus",
    "get_infrastructure_registry",
    "get_rabbitmq_manager",
    "initialize_infrastructure",
    "initialize_kafka_producer_only",
    "shutdown_infrastructure",
    "get_kafka_manager",
]
