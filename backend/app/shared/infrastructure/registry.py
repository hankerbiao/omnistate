"""应用级基础设施注册表。"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.shared.core.logger import log as logger
from app.shared.db.config import settings
from app.shared.kafka import KafkaMessageManager, load_kafka_config


KAFKA_COMPONENT = "kafka_manager"


@dataclass
class InfrastructureStatus:
    """基础设施状态信息。"""

    component_name: str
    status: str
    last_health_check: datetime | None = None
    health_details: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class InfrastructureRegistry:
    """统一管理应用级基础设施生命周期。"""

    def __init__(self) -> None:
        self.kafka_manager: KafkaMessageManager | None = None
        self._component_status: dict[str, InfrastructureStatus] = {}
        self._initialization_lock = asyncio.Lock()
        self._is_initialized = False
        logger.info("InfrastructureRegistry created")

    async def initialize(self, bootstrap_servers: list[str] | None = None) -> None:
        async with self._initialization_lock:
            if self._is_initialized:
                logger.warning("InfrastructureRegistry already initialized, skipping")
                return

            logger.info("Initializing application infrastructure...")
            dispatch_mode = (settings.EXECUTION_DISPATCH_MODE or "kafka").strip().lower()
            if dispatch_mode != "kafka":
                self._set_component_status(
                    KAFKA_COMPONENT,
                    "SKIPPED",
                    health_details={"dispatch_mode": dispatch_mode},
                )
                self._is_initialized = True
                logger.info(f"Skipping Kafka initialization because dispatch mode is {dispatch_mode}")
                return

            self._set_component_status(KAFKA_COMPONENT, "INITIALIZING")

            try:
                kafka_config = load_kafka_config()
                if bootstrap_servers is not None:
                    kafka_config.bootstrap_servers = bootstrap_servers

                self.kafka_manager = KafkaMessageManager(
                    client_id="dmlv4-infrastructure",
                    config=kafka_config,
                )
                self.kafka_manager.start()

                self._set_component_status(KAFKA_COMPONENT, "RUNNING")
                self._is_initialized = True
                logger.success("Application infrastructure initialized successfully")
            except Exception as e:
                self._set_component_status(
                    KAFKA_COMPONENT,
                    "ERROR",
                    error_message=f"Failed to initialize Kafka manager: {e}",
                )
                logger.exception(f"Failed to initialize infrastructure: {e}")
                await self.shutdown()
                raise

    async def shutdown(self) -> None:
        if not self.kafka_manager and not self._is_initialized:
            logger.warning("InfrastructureRegistry not initialized, nothing to shutdown")
            return

        logger.info("Shutting down application infrastructure...")
        self._set_component_status(KAFKA_COMPONENT, "STOPPING")

        try:
            if self.kafka_manager:
                self.kafka_manager.stop()
                self.kafka_manager = None
            self._set_component_status(KAFKA_COMPONENT, "STOPPED")
            logger.success("Application infrastructure shutdown completed")
        except Exception as e:
            self._set_component_status(
                KAFKA_COMPONENT,
                "ERROR",
                error_message=f"Error stopping Kafka manager: {e}",
            )
            logger.exception(f"Error stopping Kafka manager: {e}")
        finally:
            self._is_initialized = False

    def _set_component_status(
        self,
        component_name: str,
        status: str,
        error_message: str | None = None,
        health_details: dict[str, Any] | None = None,
    ) -> None:
        self._component_status[component_name] = InfrastructureStatus(
            component_name=component_name,
            status=status,
            last_health_check=datetime.now(timezone.utc),
            health_details=health_details or {},
            error_message=error_message,
        )

    def get_kafka_manager(self) -> KafkaMessageManager | None:
        return self.kafka_manager if self._is_initialized else None

    async def health_check(self) -> dict[str, Any]:
        logger.debug("Performing infrastructure health check...")

        if not self.kafka_manager:
            kafka_health = {
                "status": "NOT_INITIALIZED",
                "message": "Kafka manager not initialized",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            kafka_health = self.kafka_manager.health_check()

        status_info = self._component_status.get(KAFKA_COMPONENT)
        if status_info is not None:
            status_info.last_health_check = datetime.now(timezone.utc)
            status_info.health_details = kafka_health

        overall_status = "HEALTHY"
        if kafka_health["status"] == "ERROR":
            overall_status = "UNHEALTHY"
        elif kafka_health["status"] in {"DEGRADED", "STOPPED", "NOT_INITIALIZED"}:
            overall_status = "DEGRADED"

        return {
            "overall_status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                KAFKA_COMPONENT: kafka_health,
            },
        }

    def get_component_status(self, component_name: str) -> InfrastructureStatus | None:
        return self._component_status.get(component_name)

    def get_all_component_status(self) -> dict[str, InfrastructureStatus]:
        return self._component_status.copy()

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized


_infrastructure_registry: InfrastructureRegistry | None = None


def get_infrastructure_registry() -> InfrastructureRegistry:
    global _infrastructure_registry
    if _infrastructure_registry is None:
        _infrastructure_registry = InfrastructureRegistry()
    return _infrastructure_registry


async def initialize_infrastructure(bootstrap_servers: list[str] | None = None) -> None:
    registry = get_infrastructure_registry()
    await registry.initialize(bootstrap_servers)


async def shutdown_infrastructure() -> None:
    registry = get_infrastructure_registry()
    await registry.shutdown()


def get_kafka_manager() -> KafkaMessageManager | None:
    if _infrastructure_registry is None:
        return None
    return _infrastructure_registry.get_kafka_manager()
