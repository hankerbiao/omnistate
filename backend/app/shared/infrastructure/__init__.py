"""共享基础设施模块 - Phase 6

提供应用级基础设施组件的统一管理，包括：
- 基础设施注册表
- Kafka管理器生命周期管理
- Outbox工作器生命周期管理
- 健康检查和监控
"""

from .registry import (
    InfrastructureRegistry,
    InfrastructureStatus,
    get_infrastructure_registry,
    initialize_infrastructure,
    shutdown_infrastructure,
    get_kafka_manager,
    get_outbox_worker
)

__all__ = [
    "InfrastructureRegistry",
    "InfrastructureStatus",
    "get_infrastructure_registry",
    "initialize_infrastructure",
    "shutdown_infrastructure",
    "get_kafka_manager",
    "get_outbox_worker",
]