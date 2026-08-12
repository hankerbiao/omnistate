"""Development-only project demo data generation."""

import random
from datetime import datetime, timedelta, timezone

from app.modules.project.domain.exceptions import ProjectNotFoundError
from app.modules.project.repository.models.project import ProjectDoc
from app.modules.project.schemas.project import GenerateDemoResponse


class ProjectDemoService:
    @staticmethod
    async def generate(project_id: str) -> GenerateDemoResponse:
        project = await ProjectDoc.find_one({"project_id": project_id, "is_deleted": False})
        if not project:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")

        from app.modules.workflow.repository.models.business import BusFlowLogDoc, BusWorkItemDoc
        created_items = 0

        demo_work_items = [
            ("用户登录功能需求", "requirement", "用户登录模块的功能需求"),
            ("权限管理功能需求", "requirement", "权限分级管理的功能需求"),
            ("数据导出功能需求", "requirement", "数据导出模块的功能需求"),
            ("用户登录-正常流程验证", "test_case", "验证用户登录正常流程"),
            ("权限管理-管理员角色验证", "test_case", "验证管理员角色权限"),
        ]
        demo_actions = [
            ("SUBMIT_REVIEW", "DRAFT", "PENDING_REVIEW"),
            ("APPROVE", "PENDING_REVIEW", "PENDING_DEVELOP"),
            ("START_DEVELOP", "PENDING_DEVELOP", "DEVELOPING"),
        ]
        operators = ["admin001", "user002", "user003"]
        now = datetime.now(timezone.utc)
        created_activities = 0
        for title, type_code, content in demo_work_items:
            if await BusWorkItemDoc.find_one({
                "title": title,
                "project_ids": {"$in": [project_id]},
            }):
                continue
            work_item = BusWorkItemDoc(
                type_code=type_code,
                title=title,
                content=content,
                current_state="DONE",
                current_owner_id="admin001",
                creator_id="admin001",
                project_ids=[project_id],
            )
            await work_item.insert()
            for action, from_state, to_state in demo_actions[:random.randint(2, 3)]:
                flow_log = BusFlowLogDoc(
                    work_item_id=work_item.id,
                    from_state=from_state,
                    to_state=to_state,
                    action=action,
                    operator_id=random.choice(operators),
                    payload={},
                )
                flow_log.created_at = now - timedelta(
                    hours=random.randint(1, 48),
                    minutes=random.randint(0, 59),
                )
                await flow_log.insert()
                created_activities += 1

        return GenerateDemoResponse(
            plan_items_created=created_items,
            activities_created=created_activities,
        )
