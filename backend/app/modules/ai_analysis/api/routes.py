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
from app.modules.test_case_collection.repository.models import TestCaseCollectionDoc
from app.modules.test_specs.repository.models.test_case import TestCaseDoc
from app.modules.test_specs.repository.models.automation_test_case import AutomationTestCaseDoc
from app.shared.api.schemas.base import APIResponse

router = APIRouter(prefix="/ai-analyze", tags=["AIAnalysis"])


@router.post("/collections/{collection_id}", response_model=APIResponse[CollectionAnalysisResult])
async def analyze_collection(
    collection_id: str,
    request: AnalyzeRequest,
) -> APIResponse[CollectionAnalysisResult]:
    """AI分析用例集"""
    # 1. 获取集合
    collection = await TestCaseCollectionDoc.find_one(
        TestCaseCollectionDoc.collection_id == collection_id
    )
    if not collection:
        raise HTTPException(status_code=404, detail=f"集合不存在: {collection_id}")

    # 2. 获取所有用例摘要（不含完整步骤）
    cases_data = []

    # 获取手工用例
    if collection.case_ids:
        for cid in collection.case_ids:
            doc = await TestCaseDoc.find_one(TestCaseDoc.case_id == cid)
            if doc:
                case_info = {
                    "id": doc.case_id,
                    "title": doc.title,
                    "type": "manual",
                    "priority": doc.priority or "",
                    "status": doc.status if hasattr(doc, "status") else "",
                    "tags": doc.tags or [],
                }
                cases_data.append(case_info)

    # 获取自动化用例
    if collection.auto_case_ids:
        for aid in collection.auto_case_ids:
            doc = await AutomationTestCaseDoc.find_one(
                AutomationTestCaseDoc.auto_case_id == aid
            )
            if doc:
                case_info = {
                    "id": doc.auto_case_id,
                    "title": doc.name if hasattr(doc, "name") else aid,
                    "type": "auto",
                    "status": doc.status if hasattr(doc, "status") else "",
                    "tags": doc.tags if hasattr(doc, "tags") else [],
                }
                cases_data.append(case_info)

    if not cases_data:
        raise HTTPException(status_code=400, detail="集合中无用例数据")

    # 3. 调用AI分析
    result = await AIService.analyze_collection(
        collection_id=collection_id,
        cases_data=cases_data,
        analysis_types=request.analysis_types,
    )

    # 4. 转换为响应格式
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
