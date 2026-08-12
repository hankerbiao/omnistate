"""Project dashboard statistics, blockers, and activity queries."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.modules.project.schemas.project import (
    BlockerItemResponse,
    ExecutionTaskBreakdown,
    ProjectActivityResponse,
    ProjectStatsResponse,
    StatsBreakdown,
)
from app.modules.project.service._related_models import find_model, get_related_models
from app.shared.core.logger import log as logger


def _make_project_filter(project_id: str, extra_filters: Optional[list] = None) -> dict:
    query: dict = {"project_ids": {"$in": [project_id]}, "is_deleted": False}
    if extra_filters:
        query["$and"] = list(extra_filters)
    return query


async def _count_for_project(model, project_id: str, extra_filters: Optional[list] = None) -> int:
    return await model.find(_make_project_filter(project_id, extra_filters)).count()



class ProjectDashboardService:
    DEFAULT_BLOCKER_LIMIT = 20
    DEFAULT_ACTIVITY_LIMIT = 20

    @staticmethod
    async def get_project_stats(project_id: str) -> ProjectStatsResponse:
        related = get_related_models()
        test_case_count = await _count_for_project(find_model(related, "TestCaseDoc"), project_id)
        auto_case_count = await _count_for_project(
            find_model(related, "AutomationTestCaseDoc"), project_id
        )
        requirement_count = await _count_for_project(
            find_model(related, "TestRequirementDoc"), project_id
        )
        plan_count = 0
        task = ExecutionTaskBreakdown()
        manual_pass, auto_pass = StatsBreakdown(), StatsBreakdown()
        coverage_rate = (
            round(test_case_count / requirement_count * 100, 1)
            if requirement_count > 0 else 0.0
        )
        return ProjectStatsResponse(
            test_case_count=test_case_count,
            auto_case_count=auto_case_count,
            requirement_count=requirement_count,
            plan_count=plan_count,
            task=task,
            task_progress=task.progress,
            manual_pass=manual_pass,
            auto_pass=auto_pass,
            coverage_rate=coverage_rate,
            assignee_distribution=[],
        )

    @staticmethod
    async def get_blockers(project_id: str) -> List[BlockerItemResponse]:
        # 精简分支不再维护独立执行计划，项目页仅保留需求/用例统计。
        return []

    @staticmethod
    async def get_activities(
        project_id: str,
        limit: int = DEFAULT_ACTIVITY_LIMIT,
    ) -> List[ProjectActivityResponse]:
        activities: List[ProjectActivityResponse] = []
        try:
            from app.modules.workflow.repository.models.business import BusFlowLogDoc

            pipeline = [
                {"$lookup": {
                    "from": "bus_work_items",
                    "localField": "work_item_id",
                    "foreignField": "_id",
                    "as": "work_item",
                }},
                {"$unwind": "$work_item"},
                {"$match": {
                    "work_item.project_ids": {"$in": [project_id]},
                    "work_item.is_deleted": False,
                }},
                {"$sort": {"created_at": -1}},
                {"$limit": limit},
            ]
            logs = await BusFlowLogDoc.aggregate(pipeline, projection_model=None).to_list()
            operator_ids = {
                entry.get("operator_id", "") for entry in logs if entry.get("operator_id")
            }
            username_map: Dict[str, str] = {}
            if operator_ids:
                try:
                    from app.modules.auth.repository.models import UserDoc

                    users = await UserDoc.find({
                        "user_id": {"$in": list(operator_ids)}
                    }).to_list()
                    username_map = {user.user_id: user.username for user in users if user.username}
                except Exception:
                    pass

            for entry in logs:
                operator_id = entry.get("operator_id", "")
                activities.append(ProjectActivityResponse(
                    id=str(entry.get("_id", "")),
                    time=entry.get("created_at", datetime.now(timezone.utc)),
                    user_id=operator_id,
                    username=username_map.get(operator_id, ""),
                    action=entry.get("action", ""),
                    target=entry.get("work_item", {}).get("title", ""),
                    target_type=entry.get("work_item", {}).get("type_code", ""),
                ))
        except Exception as exc:
            logger.warning("获取项目动态失败: {}", exc)
        return activities
