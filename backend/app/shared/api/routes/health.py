"""
健康检查路由

用于监控服务健康状态
"""
from fastapi import APIRouter

from app.modules.execution.application.worker_presence import get_kafka_worker_health
from app.shared.api.schemas.base import APIResponse
from app.shared.db.config import settings
from app.shared.infrastructure import get_infrastructure_registry

router = APIRouter()


async def _build_health_payload() -> dict:
    """构建健康检查载荷，并显式暴露 worker 启动要求。"""
    registry = get_infrastructure_registry()
    infrastructure = await registry.health_check()
    warnings: list[str] = []
    execution_event_consumer: dict[str, str] = {
        "status": "NOT_REQUIRED",
        "message": "Execution dispatch mode is not kafka",
    }

    dispatch_mode = (settings.EXECUTION_DISPATCH_MODE or "kafka").strip().lower()
    if dispatch_mode == "kafka":
        execution_event_consumer = await get_kafka_worker_health()
        if execution_event_consumer["status"] != "ONLINE":
            warnings.append(execution_event_consumer["message"])

    components = dict(infrastructure.get("components", {}))
    components["execution_event_consumer"] = execution_event_consumer

    return {
        "status": infrastructure.get("overall_status", "UNKNOWN").lower(),
        "message": "Service is running",
        "dispatch_mode": dispatch_mode,
        "warnings": warnings,
        "components": components,
        "timestamp": infrastructure.get("timestamp"),
    }


@router.get("", summary="健康检查")
async def health_check():
    """检查服务是否正常运行"""
    return APIResponse(data=await _build_health_payload())


@router.get("/ready", summary="就绪检查")
async def readiness_check():
    """检查服务是否准备好接收请求"""
    payload = await _build_health_payload()
    if payload["warnings"]:
        payload["status"] = "ready_with_warnings"
        payload["message"] = "Service is ready, but external worker is required for kafka event consumption"
    else:
        payload["status"] = "ready"
        payload["message"] = "Service is ready to accept requests"
    return APIResponse(data=payload)


@router.get("/live", summary="存活检查")
def liveness_check():
    """检查服务是否存活"""
    return APIResponse(data={"status": "alive", "message": "Service is alive"})
