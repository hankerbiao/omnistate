"""
健康检查路由

用于监控服务健康状态
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("", summary="健康检查")
def health_check():
    """检查服务是否正常运行"""
    return {"status": "healthy", "message": "Service is running"}


@router.get("/ready", summary="就绪检查")
def readiness_check():
    """检查服务是否准备好接收请求"""
    return {"status": "ready", "message": "Service is ready to accept requests"}


@router.get("/live", summary="存活检查")
def liveness_check():
    """检查服务是否存活"""
    return {"status": "alive", "message": "Service is alive"}