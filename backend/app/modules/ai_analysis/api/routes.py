"""AI 分析 API 路由"""
from fastapi import APIRouter, HTTPException

from app.modules.ai_analysis.schemas.analysis import (
    AnalyzeRequest,
    CollectionAnalysisResult,
    QualityAnalysis,
    RedundancyAnalysis,
    CoverageAnalysis,
)
from app.modules.ai_analysis.service.ai_service import AIService
from app.shared.api.schemas.base import APIResponse

router = APIRouter(prefix="/ai-analyze", tags=["AIAnalysis"])


@router.post("/collections/{collection_id}", response_model=APIResponse[CollectionAnalysisResult], summary="AI 分析用例集质量/冗余/覆盖")
async def analyze_collection(
    collection_id: str,
    request: AnalyzeRequest,
) -> APIResponse[CollectionAnalysisResult]:
    """AI分析用例集"""
    result = await AIService.analyze_collection_by_id(
        collection_id=collection_id,
        analysis_types=request.analysis_types,
    )

    # 转换为响应格式
    q = result.get("quality", {})
    r = result.get("redundancy", {})
    c = result.get("coverage", {})

    response = CollectionAnalysisResult(
        collection_id=collection_id,
        overall_score=result.get("overall_score", 0),
        quality=QualityAnalysis(score=q.get("score", 0), issues=q.get("issues", [])),
        redundancy=RedundancyAnalysis(score=r.get("score", 100), duplicates=r.get("duplicates", [])),
        coverage=CoverageAnalysis(score=c.get("score", 0), gaps=c.get("gaps", [])),
        recommendations=result.get("recommendations", []),
    )

    return APIResponse(data=response)
