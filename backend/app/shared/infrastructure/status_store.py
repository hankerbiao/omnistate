"""
组件状态存储：轻量的状态追踪器，供 InfrastructureRegistry 使用。

将组件注册/状态查询与生命周期管理解耦。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ComponentStatus:
    """单个基础设施组件的运行时状态快照。"""

    component_name: str
    status: str  # "healthy" | "degraded" | "stopped" | "skipped" | "error"
    last_health_check: datetime | None = None
    health_details: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class ComponentStatusStore:
    """轻量级组件状态存储器。"""

    def __init__(self) -> None:
        self._status: dict[str, ComponentStatus] = {}

    def set_component_status(
        self,
        component_name: str,
        status: str,
        error_message: str | None = None,
        health_details: dict[str, Any] | None = None,
    ) -> None:
        """更新组件状态。"""
        self._status[component_name] = ComponentStatus(
            component_name=component_name,
            status=status,
            last_health_check=datetime.utcnow(),
            health_details=health_details or {},
            error_message=error_message,
        )

    def get_component_status(self, component_name: str) -> ComponentStatus | None:
        """查询组件状态。"""
        return self._status.get(component_name)

    def get_all_component_status(self) -> dict[str, ComponentStatus]:
        """查询所有组件状态。"""
        return dict(self._status)

    def format_health_snapshot(self) -> dict[str, Any]:
        """格式化健康检查快照。"""
        snapshot: dict[str, Any] = {}
        for name, status in self._status.items():
            snapshot[name] = {
                "status": status.status,
                "last_health_check": (
                    status.last_health_check.isoformat() if status.last_health_check else None
                ),
                "error_message": status.error_message,
            }
        return snapshot
