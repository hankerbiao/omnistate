"""应用级基础设施注册表。"""

import asyncio
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.shared.core.logger import log as logger
from app.shared.kafka import KafkaMessageManager, load_kafka_config


@dataclass
class InfrastructureStatus:
    """基础设施状态信息"""
    component_name: str
    status: str  # INITIALIZING, RUNNING, STOPPED, ERROR
    last_health_check: Optional[datetime] = None
    health_details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class InfrastructureRegistry:
    """应用级基础设施注册表

    统一管理所有基础设施组件的生命周期，包括启动、停止和健康检查。
    确保在应用启动时初始化，关闭时优雅清理。
    """

    def __init__(self):
        """初始化基础设施注册表"""
        # 基础设施组件实例
        self.kafka_manager: Optional[KafkaMessageManager] = None
        self._component_status: Dict[str, InfrastructureStatus] = {}
        self._initialization_lock = asyncio.Lock()
        self._is_initialized = False

        logger.info("InfrastructureRegistry created")

    async def initialize(self, bootstrap_servers: Optional[List[str]] = None) -> None:
        """初始化所有基础设施组件

        Args:
            bootstrap_servers: Kafka集群地址列表，如果为None则使用默认配置
        """
        async with self._initialization_lock:
            if self._is_initialized:
                logger.warning("InfrastructureRegistry already initialized, skipping")
                return

            logger.info("Initializing application infrastructure...")

            try:
                # 初始化Kafka管理器
                await self._initialize_kafka_manager(bootstrap_servers)

                self._is_initialized = True
                logger.success("Application infrastructure initialized successfully")

            except Exception as e:
                logger.exception(f"Failed to initialize infrastructure: {str(e)}")
                await self.shutdown()
                raise

    async def _initialize_kafka_manager(self, bootstrap_servers: Optional[List[str]]) -> None:
        """初始化Kafka管理器"""
        component_name = "kafka_manager"
        self._set_component_status(component_name, "INITIALIZING")

        try:
            kafka_config = load_kafka_config()
            if bootstrap_servers is not None:
                kafka_config.bootstrap_servers = bootstrap_servers

            self.kafka_manager = KafkaMessageManager(
                client_id="dmlv4-infrastructure",
                config=kafka_config,
            )

            # 启动Kafka管理器
            self.kafka_manager.start()
            self._set_component_status(component_name, "RUNNING")
            logger.success("Kafka manager initialized and started")

        except Exception as e:
            self._set_component_status(
                component_name, "ERROR", 
                error_message=f"Failed to initialize Kafka manager: {str(e)}"
            )
            raise

    async def shutdown(self) -> None:
        """关闭所有基础设施组件"""
        if not self._is_initialized:
            logger.warning("InfrastructureRegistry not initialized, nothing to shutdown")
            return

        logger.info("Shutting down application infrastructure...")

        shutdown_tasks = []

        # 关闭Kafka管理器
        if self.kafka_manager:
            shutdown_tasks.append(self._shutdown_kafka_manager())

        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        self._is_initialized = False
        logger.success("Application infrastructure shutdown completed")

    async def _shutdown_kafka_manager(self) -> None:
        """关闭Kafka管理器"""
        component_name = "kafka_manager"
        self._set_component_status(component_name, "STOPPING")

        try:
            if self.kafka_manager:
                self.kafka_manager.stop()
                self.kafka_manager = None
            self._set_component_status(component_name, "STOPPED")
            logger.info("Kafka manager stopped")
        except Exception as e:
            self._set_component_status(
                component_name, "ERROR",
                error_message=f"Error stopping Kafka manager: {str(e)}"
            )
            logger.exception(f"Error stopping Kafka manager: {str(e)}")

    def _set_component_status(
        self, 
        component_name: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """设置组件状态"""
        self._component_status[component_name] = InfrastructureStatus(
            component_name=component_name,
            status=status,
            last_health_check=datetime.now(timezone.utc),
            error_message=error_message
        )

    def get_kafka_manager(self) -> Optional[KafkaMessageManager]:
        """获取Kafka管理器实例

        Returns:
            Kafka管理器实例，如果未初始化则返回None
        """
        if not self._is_initialized or not self.kafka_manager:
            logger.warning("Kafka manager not available (not initialized)")
            return None
        return self.kafka_manager

    async def health_check(self) -> Dict[str, Any]:
        """执行所有基础设施组件的健康检查

        Returns:
            健康检查结果字典
        """
        logger.debug("Performing infrastructure health check...")

        health_results = {
            "overall_status": "HEALTHY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {}
        }

        # 检查Kafka管理器
        kafka_health = await self._check_kafka_health()
        health_results["components"]["kafka_manager"] = kafka_health

        if kafka_health["status"] == "ERROR":
            health_results["overall_status"] = "UNHEALTHY"
        elif kafka_health["status"] == "DEGRADED":
            health_results["overall_status"] = "DEGRADED"

        return health_results

    async def _check_kafka_health(self) -> Dict[str, Any]:
        """检查Kafka管理器健康状态"""
        component_name = "kafka_manager"
        
        if not self.kafka_manager:
            return {
                "status": "NOT_INITIALIZED",
                "message": "Kafka manager not initialized",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        try:
            # 检查Kafka是否可用
            # 注意：这里需要KafkaMessageManager有一个健康检查方法
            # 如果没有，我们可以通过尝试发送测试消息来检查
            is_available = hasattr(self.kafka_manager, 'is_available') and self.kafka_manager.is_available()
            
            if is_available:
                status_info = self._component_status.get(component_name)
                return {
                    "status": "HEALTHY",
                    "message": "Kafka manager is available",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": {
                        "is_running": self.kafka_manager.is_running,
                        "bootstrap_servers": getattr(self.kafka_manager, 'bootstrap_servers', []),
                        "last_status": status_info.last_health_check.isoformat() if status_info and status_info.last_health_check is not None else None
                    }
                }
            else:
                return {
                    "status": "DEGRADED",
                    "message": "Kafka manager is running but may not be fully available",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        except Exception as e:
            logger.exception(f"Kafka health check failed: {str(e)}")
            return {
                "status": "ERROR",
                "message": f"Kafka health check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def get_component_status(self, component_name: str) -> Optional[InfrastructureStatus]:
        """获取特定组件的状态信息

        Args:
            component_name: 组件名称

        Returns:
            组件状态信息，如果不存在则返回None
        """
        return self._component_status.get(component_name)

    def get_all_component_status(self) -> Dict[str, InfrastructureStatus]:
        """获取所有组件的状态信息

        Returns:
            所有组件状态的字典
        """
        return self._component_status.copy()

    @property
    def is_initialized(self) -> bool:
        """检查注册表是否已初始化"""
        return self._is_initialized


# 全局基础设施注册表实例
_infrastructure_registry: Optional[InfrastructureRegistry] = None


def get_infrastructure_registry() -> InfrastructureRegistry:
    """获取全局基础设施注册表实例

    Returns:
        基础设施注册表实例
    """
    global _infrastructure_registry
    if _infrastructure_registry is None:
        _infrastructure_registry = InfrastructureRegistry()
    return _infrastructure_registry


async def initialize_infrastructure(bootstrap_servers: Optional[List[str]] = None) -> None:
    """初始化全局基础设施注册表

    Args:
        bootstrap_servers: Kafka集群地址列表
    """
    registry = get_infrastructure_registry()
    await registry.initialize(bootstrap_servers)


async def shutdown_infrastructure() -> None:
    """关闭全局基础设施注册表"""
    registry = await get_infrastructure_registry()
    await registry.shutdown()


def get_kafka_manager() -> Optional[KafkaMessageManager]:
    """获取全局Kafka管理器实例

    Returns:
        Kafka管理器实例，如果未初始化则返回None
    """
    if _infrastructure_registry is None:
        logger.warning("Infrastructure registry not initialized")
        return None
    return _infrastructure_registry.get_kafka_manager()
