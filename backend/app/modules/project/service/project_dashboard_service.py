"""Project dashboard statistics, blockers, and activity queries."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.modules.project.schemas.project import (
    AssigneeDistribution,
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


async def _compute_task_breakdown(task_cls, project_id: str) -> ExecutionTaskBreakdown:
    total = await _count_for_project(task_cls, project_id)
    done = await _count_for_project(
        task_cls, project_id, [{"overall_status": {"$in": ["FINISHED", "SUCCESS", "DONE"]}}]
    )
    running = await _count_for_project(
        task_cls, project_id, [{"overall_status": {"$in": ["RUNNING", "DISPATCHED"]}}]
    )
    failed = await _count_for_project(
        task_cls, project_id, [{"overall_status": {"$in": ["FAILED", "ERROR"]}}]
    )
    pending = total - done - running - failed
    progress = round(done / total * 100, 1) if total > 0 else 0.0
    return ExecutionTaskBreakdown(
        total=total,
        done=done,
        running=running,
        failed=failed,
        pending=pending,
        progress=progress,
    )


async def _fetch_assignee_distribution(project_id: str) -> List[AssigneeDistribution]:
    try:
        from app.modules.execution_plan.repository.models import ExecutionPlanItemDoc

        pipeline = [
            {"$lookup": {
                "from": "execution_plans",
                "localField": "plan_id",
                "foreignField": "plan_id",
                "as": "plan",
            }},
            {"$unwind": "$plan"},
            {"$match": {
                "plan.project_ids": {"$in": [project_id]},
                "plan.is_deleted": False,
                "is_deleted": False,
            }},
            {"$group": {
                "_id": "$assignee_id",
                "item_count": {"$sum": 1},
                "done_count": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}},
            }},
            {"$sort": {"item_count": -1}},
        ]
        results = await ExecutionPlanItemDoc.aggregate(pipeline, projection_model=None).to_list()
        return [
            AssigneeDistribution(
                assignee_id=result.get("_id"),
                assignee_name="",
                item_count=result.get("item_count", 0),
                done_count=result.get("done_count", 0),
                progress=(
                    round(result["done_count"] / result["item_count"] * 100, 1)
                    if result.get("item_count") else 0.0
                ),
            )
            for result in results
        ]
    except Exception as exc:
        logger.warning("获取项目执行人分布失败: project_id={} error={}", project_id, exc)
        return []


async def _compute_pass_rates(project_id: str) -> tuple[StatsBreakdown, StatsBreakdown]:
    manual = StatsBreakdown()
    auto = StatsBreakdown()
    try:
        from app.modules.execution_plan.repository.models import ExecutionPlanItemDoc

        pipeline = [
            {"$lookup": {
                "from": "execution_plans",
                "localField": "plan_id",
                "foreignField": "plan_id",
                "as": "plan",
            }},
            {"$unwind": "$plan"},
            {"$match": {
                "plan.project_ids": {"$in": [project_id]},
                "plan.is_deleted": False,
                "is_deleted": False,
            }},
            {"$group": {
                "_id": "$ref_type",
                "total": {"$sum": 1},
                "passed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "fail"]}, 1, 0]}},
            }},
        ]
        for result in await ExecutionPlanItemDoc.aggregate(pipeline, projection_model=None).to_list():
            total = result.get("total", 0)
            passed = result.get("passed", 0)
            stats = StatsBreakdown(
                total=total,
                passed=passed,
                failed=result.get("failed", 0),
                pass_rate=round(passed / total * 100, 1) if total > 0 else 0.0,
            )
            if result.get("_id") == "manual":
                manual = stats
            elif result.get("_id") == "auto":
                auto = stats
    except Exception as exc:
        logger.warning("计算项目通过率失败: project_id={} error={}", project_id, exc)
    return manual, auto


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
        plan_count = await _count_for_project(find_model(related, "ExecutionPlanDoc"), project_id)
        task = await _compute_task_breakdown(find_model(related, "ExecutionTaskDoc"), project_id)
        manual_pass, auto_pass = await _compute_pass_rates(project_id)
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
            assignee_distribution=await _fetch_assignee_distribution(project_id),
        )

    @staticmethod
    async def get_blockers(project_id: str) -> List[BlockerItemResponse]:
        blockers: List[BlockerItemResponse] = []
        try:
            from app.modules.execution_plan.repository.models import ExecutionPlanItemDoc

            pipeline = [
                {"$lookup": {
                    "from": "execution_plans",
                    "localField": "plan_id",
                    "foreignField": "plan_id",
                    "as": "plan",
                }},
                {"$unwind": "$plan"},
                {"$match": {
                    "plan.project_ids": {"$in": [project_id]},
                    "plan.is_deleted": False,
                    "is_deleted": False,
                    "$or": [
                        {"status": "fail"},
                        {"$and": [{"status": "pending"}, {"priority": "P0"}]},
                    ],
                }},
                {"$sort": {"updated_at": -1}},
                {"$limit": ProjectDashboardService.DEFAULT_BLOCKER_LIMIT},
            ]
            items = await ExecutionPlanItemDoc.aggregate(pipeline, projection_model=None).to_list()
            blockers.extend(
                BlockerItemResponse(
                    id=item.get("item_id", ""),
                    title=item.get("case_title", ""),
                    source="plan_item",
                    assignee_id=item.get("assignee_id"),
                    status=item.get("status", ""),
                    priority=item.get("priority", ""),
                    updated_at=item.get("updated_at"),
                )
                for item in items
            )

            task_cls = find_model(get_related_models(), "ExecutionTaskDoc")
            failed_tasks = await task_cls.find(
                {
                    "project_ids": {"$in": [project_id]},
                    "is_deleted": False,
                    "overall_status": {"$in": ["FAILED", "ERROR"]},
                },
                sort=[("updated_at", -1)],
                limit=ProjectDashboardService.DEFAULT_BLOCKER_LIMIT,
            ).to_list()
            blockers.extend(
                BlockerItemResponse(
                    id=getattr(task, "task_id", ""),
                    title=getattr(task, "task_id", ""),
                    source="execution_task",
                    assignee_id=getattr(task, "created_by", None),
                    status=getattr(task, "overall_status", ""),
                    priority="",
                    updated_at=getattr(task, "updated_at", None),
                )
                for task in failed_tasks
            )
        except Exception as exc:
            logger.warning("获取项目阻塞项失败: {}", exc)
        return blockers[:ProjectDashboardService.DEFAULT_BLOCKER_LIMIT]

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
