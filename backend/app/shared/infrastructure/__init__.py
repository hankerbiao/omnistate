"""共享基础设施模块。"""

from .registry import (
    InfrastructureRegistry,
    InfrastructureStatus,
    get_infrastructure_registry,
    initialize_infrastructure,
    shutdown_infrastructure,
    get_kafka_manager,
)

__all__ = [
    "InfrastructureRegistry",
    "InfrastructureStatus",
    "get_infrastructure_registry",
    "initialize_infrastructure",
    "shutdown_infrastructure",
    "get_kafka_manager",
]
