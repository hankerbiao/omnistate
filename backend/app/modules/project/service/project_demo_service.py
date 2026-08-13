"""Development-only project demo data generation."""

from app.modules.project.domain.exceptions import ProjectNotFoundError
from app.modules.project.repository.models.project import ProjectDoc
from app.modules.project.schemas.project import GenerateDemoResponse


class ProjectDemoService:
    @staticmethod
    async def generate(project_id: str) -> GenerateDemoResponse:
        project = await ProjectDoc.find_one({"project_id": project_id, "is_deleted": False})
        if not project:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")

        return GenerateDemoResponse(plan_items_created=0, activities_created=0)
