"""血缘图谱 API 依赖注入。"""

from typing import Annotated

from fastapi import Depends

from app.modules.lineage.service import LineageService


def get_lineage_service() -> LineageService:
    return LineageService()


LineageServiceDep = Annotated[
    LineageService,
    Depends(get_lineage_service),
]
