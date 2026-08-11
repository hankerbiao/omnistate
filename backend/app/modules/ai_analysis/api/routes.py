"""AI 分析 API 路由"""
from fastapi import APIRouter

from app.modules.ai_analysis.schemas.analysis import (
    PendingTaskAnalysisRequest,
    PendingTaskAnalysisResult,
)
from app.modules.ai_analysis.service.ai_service import AIService
from app.shared.api.schemas.base import APIResponse

router = APIRouter(prefix="/ai-analyze", tags=["AIAnalysis"])



@router.post(
    "/my-tasks/pending",
    response_model=APIResponse[PendingTaskAnalysisResult],
    summary="AI 分析我的待处理任务",
)
async def analyze_pending_tasks(
    request: PendingTaskAnalysisRequest,
) -> APIResponse[PendingTaskAnalysisResult]:
    """AI 分析当前用户待处理任务结构、风险和异常。"""
    result = await AIService.analyze_pending_tasks(request.model_dump())
    return APIResponse(data=PendingTaskAnalysisResult(**result))
