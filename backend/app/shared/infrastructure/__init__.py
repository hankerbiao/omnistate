"""共享基础设施模块。"""

from .registry import (
    InfrastructureRegistry,
    InfrastructureStatus,
    get_infrastructure_registry,
    get_rabbitmq_manager,
    initialize_infrastructure,
    initialize_kafka_producer_only,
    shutdown_infrastructure,
    get_kafka_manager,
)

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
