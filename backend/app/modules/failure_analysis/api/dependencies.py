"""失效分析 API 依赖注入。"""

from typing import Annotated

from fastapi import Depends

from app.modules.failure_analysis.service import FailureAnalysisService


def get_failure_analysis_service() -> FailureAnalysisService:
    return FailureAnalysisService()


FailureAnalysisServiceDep = Annotated[
    FailureAnalysisService,
    Depends(get_failure_analysis_service),
]
