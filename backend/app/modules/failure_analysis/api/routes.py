"""失效分析 API 路由。"""
from fastapi import APIRouter, Depends, Query

from app.modules.failure_analysis.api.dependencies import FailureAnalysisServiceDep
from app.modules.failure_analysis.schemas.failure_analysis import (
    FailureAnalysisDashboard,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/failure-analysis", tags=["Failure Analysis"])


@router.get(
    "/dashboard",
    response_model=APIResponse[FailureAnalysisDashboard],
    summary="获取失效分析仪表盘数据",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def get_failure_analysis_dashboard(
    time_range: str = Query("30d", regex="^(7d|30d|90d)$"),
    limit_flaky: int = Query(20, ge=1, le=100),
    limit_high_freq: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    service: FailureAnalysisServiceDep = None,
):
    """获取失效分析仪表盘数据。

    - time_range: 时间范围，7d/30d/90d，默认30d
    - limit_flaky: 不稳定测试返回数量上限
    - limit_high_freq: 高频失败返回数量上限
    """
    data = await service.get_dashboard(
        time_range=time_range,
        limit_flaky=limit_flaky,
        limit_high_freq=limit_high_freq,
    )
    return APIResponse(data=data)
