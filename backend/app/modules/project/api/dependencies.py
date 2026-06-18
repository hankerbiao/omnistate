"""项目 API 依赖注入。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.project.service.project_service import ProjectService


def get_project_service() -> ProjectService:
    return ProjectService()


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
