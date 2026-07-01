"""项目服务层。"""

from __future__ import annotations

import importlib
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.modules.project.domain.constants import (
    PROJECT_ID_PREFIX,
    PROJECT_RELATED_MODEL_PATHS,
    ProjectStatus,
)
from app.modules.project.domain.exceptions import (
    ProjectKeyConflictError,
    ProjectNotFoundError,
)
from app.modules.project.repository.models.project import ProjectDoc
from app.modules.project.schemas.project import (
    AssigneeDistribution,
    BlockerItemResponse,
    ExecutionTaskBreakdown,
    GenerateDemoResponse,
    OwnerBrief,
    ProjectActivityResponse,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectStatsResponse,
    StatsBreakdown,
)
from app.shared.core.logger import log as logger
from app.shared.service.base import BaseService

# 阻塞项 / 最近动态列表的默认返回条数上限
DEFAULT_BLOCKER_LIMIT = 20
DEFAULT_ACTIVITY_LIMIT = 20


# ── 跨模块查询端口 ──────────────────────────────────────────────────


class UserNameResolverPort(ABC):
    """用户名解析端口，由 auth 模块提供实现。"""

    @abstractmethod
    async def resolve_username(self, user_id: str) -> Optional[str]:
        """根据 user_id 查询用户名，不存在返回 None。"""
        ...


class _DefaultUserNameResolver(UserNameResolverPort):
    """默认实现：延迟加载 auth 模块，消除编译期依赖。"""

    async def resolve_username(self, user_id: str) -> Optional[str]:
        try:
            from app.modules.auth.repository.models import UserDoc
            user = await UserDoc.find_one({"user_id": user_id})
            return user.username if user else None
        except Exception:
            return None


# ── 关联模型延迟加载 ──────────────────────────────────────────────────


def _get_related_models() -> list[type]:
    """延迟加载所有关联实体模型。"""
    models = []
    for module_path, class_name in PROJECT_RELATED_MODEL_PATHS:
        try:
            module = importlib.import_module(module_path)
            model_cls = getattr(module, class_name)
            models.append(model_cls)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to load related model {module_path}.{class_name}: {e}")
    return models


def _find_model(related: list[type], name: str) -> type:
    """在关联模型列表中按类名查找，未找到时抛出明确异常。"""
    for m in related:
        if m.__name__ == name:
            return m
    raise ValueError(
        f"Related model '{name}' is not registered in PROJECT_RELATED_MODEL_PATHS. "
        f"Available models: {[m.__name__ for m in related]}"
    )


# ── 辅助查询 ──────────────────────────────────────────────────────────


async def _resolve_owner(owner_id: Optional[str]) -> Optional[OwnerBrief]:
    if not owner_id:
        return None
    username = await _DefaultUserNameResolver().resolve_username(owner_id)
    if username:
        return OwnerBrief(user_id=owner_id, username=username)
    return None


async def _batch_resolve_owners(owner_ids: set[str]) -> Dict[str, OwnerBrief]:
    """批量查询用户并构建 OwnerBrief 映射"""
    if not owner_ids:
        return {}
    try:
        from app.modules.auth.repository.models import UserDoc

        users = await UserDoc.find(
            {"user_id": {"$in": list(owner_ids)}}
        ).to_list()
        return {
            u.user_id: OwnerBrief(user_id=u.user_id, username=u.username)
            for u in users
            if u.username
        }
    except Exception as e:
        logger.warning("批量查询 owner 信息失败: {}", e)
        return {}


async def _fetch_assignee_distribution(project_id: str) -> List[AssigneeDistribution]:
    try:
        from app.modules.execution_plan.repository.models import ExecutionPlanItemDoc
        # ExecutionPlanItemDoc 没有 project_ids，需要通过 ExecutionPlanDoc 做 $lookup
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
        result = await ExecutionPlanItemDoc.aggregate(pipeline, projection_model=None).to_list()
        return [
            AssigneeDistribution(
                assignee_id=r.get("_id"),
                assignee_name="",
                item_count=r.get("item_count", 0),
                done_count=r.get("done_count", 0),
                progress=round(r["done_count"] / r["item_count"] * 100, 1) if r.get("item_count") else 0.0,
            ) for r in result
        ]
    except Exception:
        logger.warning("获取项目执行人分布失败: project_id={}", project_id)
        return []


# ── 统计查询辅助函数 ──────────────────────────────────────────────────


def _make_project_filter(project_id: str, extra_filters: Optional[list] = None) -> dict:
    q: dict = {"project_ids": {"$in": [project_id]}, "is_deleted": False}
    if extra_filters:
        q["$and"] = list(extra_filters)
    return q


async def _count_for_project(model, project_id: str, extra_filters: Optional[list] = None) -> int:
    return await model.find(_make_project_filter(project_id, extra_filters)).count()


async def _compute_task_breakdown(task_cls, project_id: str) -> ExecutionTaskBreakdown:
    total = await _count_for_project(task_cls, project_id)
    done = await _count_for_project(task_cls, project_id, [{"overall_status": {"$in": ["FINISHED", "SUCCESS", "DONE"]}}])
    running = await _count_for_project(task_cls, project_id, [{"overall_status": {"$in": ["RUNNING", "DISPATCHED"]}}])
    failed = await _count_for_project(task_cls, project_id, [{"overall_status": {"$in": ["FAILED", "ERROR"]}}])
    pending = total - done - running - failed
    progress = round(done / total * 100, 1) if total > 0 else 0.0
    return ExecutionTaskBreakdown(
        total=total, done=done, running=running, failed=failed,
        pending=pending, progress=progress,
    )


async def _compute_pass_rates(project_id: str) -> tuple[StatsBreakdown, StatsBreakdown]:
    """使用 aggregation pipeline 分类型统计通过率，避免全量加载到内存。"""
    manual = StatsBreakdown()
    auto = StatsBreakdown()
    try:
        from app.modules.execution_plan.repository.models import ExecutionPlanItemDoc
        # ExecutionPlanItemDoc 没有 project_ids，需要通过 ExecutionPlanDoc 做 $lookup
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
        results = await ExecutionPlanItemDoc.aggregate(pipeline, projection_model=None).to_list()
        for r in results:
            ref_type = r.get("_id")
            total = r.get("total", 0)
            passed = r.get("passed", 0)
            failed = r.get("failed", 0)
            rate = round(passed / total * 100, 1) if total > 0 else 0.0
            sb = StatsBreakdown(total=total, passed=passed, failed=failed, pass_rate=rate)
            if ref_type == "manual":
                manual = sb
            elif ref_type == "auto":
                auto = sb
    except Exception:
        logger.warning("计算项目通过率失败: project_id={}", project_id)
    return manual, auto


async def _compute_coverage(test_case_count: int, requirement_count: int) -> float:
    return round(test_case_count / requirement_count * 100, 1) if requirement_count > 0 else 0.0


# ── 主服务类 ───────────────────────────────────────────────────────────


class ProjectService(BaseService):
    """项目 CRUD 与统计服务。"""

    # ── 响应构造 ──────────────────────────────────────────────────────

    @staticmethod
    async def _to_project_response(doc, owner_map: Optional[Dict[str, OwnerBrief]] = None) -> ProjectResponse:
        owner = owner_map.get(doc.owner_id) if owner_map else await _resolve_owner(doc.owner_id)
        return ProjectResponse(
            project_id=doc.project_id,
            key=doc.key,
            name=doc.name,
            description=doc.description,
            status=doc.status,
            priority=doc.priority,
            owner_id=doc.owner_id,
            owner=owner,
            start_date=doc.start_date,
            end_date=doc.end_date,
            target_version=doc.target_version,
            tags=doc.tags or [],
            created_by=doc.created_by,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    # ── 列表 ──────────────────────────────────────────────────────────

    @staticmethod
    async def list_projects(
        *,
        name: Optional[str] = None,
        status: Optional[str] = None,
        key: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        filters: list = [ProjectDoc.is_deleted == False]

        if name:
            filters.append(ProjectDoc.name == {"$regex": name, "$options": "i"})
        if status:
            filters.append(ProjectDoc.status == status)
        if key:
            filters.append(ProjectDoc.key == {"$regex": key, "$options": "i"})

        sort_field = getattr(ProjectDoc, sort_by, ProjectDoc.created_at)
        sort_direction = -1 if sort_order == "desc" else 1
        skip = (page - 1) * page_size

        total = await ProjectDoc.find({"$and": filters}).count()
        docs = await (
            ProjectDoc.find({"$and": filters})
            .sort((sort_field, sort_direction))
            .skip(skip)
            .limit(page_size)
            .to_list()
        )

        # 批量解析 owner 信息（避免 N+1）
        owner_ids = {d.owner_id for d in docs if d.owner_id}
        owner_map = await _batch_resolve_owners(owner_ids)
        items = [await ProjectService._to_project_response(d, owner_map=owner_map) for d in docs]
        return {"items": items, "total": total}

    # ── 创建 ──────────────────────────────────────────────────────────

    @staticmethod
    async def create_project(
        data: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> ProjectDoc:
        existing = await ProjectDoc.find_one(
            {"key": data["key"], "is_deleted": False}
        )
        if existing:
            raise ProjectKeyConflictError(data["key"])

        project_id = await ProjectService._generate_project_id()

        doc = ProjectDoc(
            project_id=project_id,
            key=data["key"],
            name=data["name"],
            description=data.get("description"),
            status=ProjectStatus.ACTIVE.value,
            priority=data.get("priority", "P2"),
            owner_id=data.get("owner_id"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            target_version=data.get("target_version"),
            tags=data.get("tags", []),
            created_by=created_by,
        )
        await doc.insert()
        logger.info(f"Project created: {project_id} ({data['key']})")
        return doc

    # ── 读取 ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_project(project_id: str) -> Optional[ProjectDoc]:
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")
        return doc

    @staticmethod
    async def get_project_detail(project_id: str) -> ProjectDetailResponse:
        doc = await ProjectService.get_project(project_id)
        stats = await ProjectService.get_project_stats(project_id)
        response = await ProjectService._to_project_response(doc)
        return ProjectDetailResponse(**response.model_dump(), stats=stats)

    # ── 更新 ──────────────────────────────────────────────────────────

    @staticmethod
    async def update_project(
        project_id: str,
        data: Dict[str, Any],
    ) -> ProjectDoc:
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")

        if "key" in data and data["key"] != doc.key:
            existing = await ProjectDoc.find_one(
                {"key": data["key"], "is_deleted": False, "project_id": {"$ne": project_id}}
            )
            if existing:
                raise ProjectKeyConflictError(data["key"])

        allowed_fields = {
            "name", "key", "description", "status",
            "priority", "owner_id", "start_date", "end_date",
            "target_version", "tags",
        }
        ProjectService._apply_updates(doc, data, allowed_fields)
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()
        logger.info(f"Project updated: {project_id}")
        return doc

    # ── 删除 ──────────────────────────────────────────────────────────

    @staticmethod
    async def delete_project(project_id: str) -> None:
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")

        doc.is_deleted = True
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()

        for model in _get_related_models():
            try:
                await model.find(
                    {"project_ids": project_id, "is_deleted": False}
                ).update_many({"$pull": {"project_ids": project_id}})
            except Exception as e:
                logger.warning(f"Failed to clean project_ids from {model.__name__}: {e}")

        logger.info(f"Project deleted: {project_id}")

    # ── 统计 ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_project_stats(project_id: str) -> ProjectStatsResponse:
        related = _get_related_models()

        tc = _find_model(related, "TestCaseDoc")
        ac = _find_model(related, "AutomationTestCaseDoc")
        rc = _find_model(related, "TestRequirementDoc")
        ec = _find_model(related, "TestCaseCollectionDoc")

        test_case_count = await _count_for_project(tc, project_id)
        auto_case_count = await _count_for_project(ac, project_id)
        requirement_count = await _count_for_project(rc, project_id)
        plan_count = await _count_for_project(_find_model(related, "ExecutionPlanDoc"), project_id)
        collection_count = await _count_for_project(ec, project_id)

        task = await _compute_task_breakdown(_find_model(related, "ExecutionTaskDoc"), project_id)
        manual_pass, auto_pass = await _compute_pass_rates(project_id)
        coverage_rate = await _compute_coverage(test_case_count, requirement_count)
        assignee_dist = await _fetch_assignee_distribution(project_id)

        return ProjectStatsResponse(
            test_case_count=test_case_count,
            auto_case_count=auto_case_count,
            requirement_count=requirement_count,
            plan_count=plan_count,
            collection_count=collection_count,
            task=task,
            task_progress=task.progress,
            manual_pass=manual_pass,
            auto_pass=auto_pass,
            coverage_rate=coverage_rate,
            assignee_distribution=assignee_dist,
        )

    # ── 阻塞项 ─────────────────────────────────────────────────────────

    @staticmethod
    async def get_blockers(project_id: str) -> List[BlockerItemResponse]:
        """获取项目风险/阻塞项。"""
        blockers: List[BlockerItemResponse] = []
        try:
            from app.modules.execution_plan.repository.models import ExecutionPlanItemDoc
            # 1. 从 ExecutionPlanItemDoc 查询失败的条目（通过 ExecutionPlanDoc 关联）
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
                {"$limit": DEFAULT_BLOCKER_LIMIT},
            ]
            items = await ExecutionPlanItemDoc.aggregate(pipeline, projection_model=None).to_list()
            for item in items:
                blockers.append(BlockerItemResponse(
                    id=item.get("item_id", ""),
                    title=item.get("case_title", ""),
                    source="plan_item",
                    assignee_id=item.get("assignee_id"),
                    status=item.get("status", ""),
                    priority=item.get("priority", ""),
                    updated_at=item.get("updated_at"),
                ))

            # 2. 从 ExecutionTaskDoc 查询失败的任务
            task_cls = _find_model(_get_related_models(), "ExecutionTaskDoc")
            failed_tasks = await task_cls.find(
                {"project_ids": {"$in": [project_id]}, "is_deleted": False,
                 "overall_status": {"$in": ["FAILED", "ERROR"]}},
                sort=[("updated_at", -1)],
                limit=DEFAULT_BLOCKER_LIMIT,
            ).to_list()
            for t in failed_tasks:
                blockers.append(BlockerItemResponse(
                    id=getattr(t, "task_id", ""),
                    title=getattr(t, "task_id", ""),
                    source="execution_task",
                    assignee_id=getattr(t, "created_by", None),
                    status=getattr(t, "overall_status", ""),
                    priority="",
                    updated_at=getattr(t, "updated_at", None),
                ))
        except Exception as e:
            logger.warning(f"获取项目阻塞项失败: {e}")

        return blockers[:DEFAULT_BLOCKER_LIMIT]

    # ── 最近动态 ───────────────────────────────────────────────────────

    @staticmethod
    async def get_activities(project_id: str, limit: int = DEFAULT_ACTIVITY_LIMIT) -> List[ProjectActivityResponse]:
        """获取项目最近动态。"""
        activities: List[ProjectActivityResponse] = []
        try:
            from app.modules.workflow.repository.models.business import BusFlowLogDoc
            # BusFlowLogDoc → $lookup BusWorkItemDoc → 按 project_ids 过滤
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
            # 批量查询用户名（避免 N+1）
            operator_ids = {log_entry.get("operator_id", "") for log_entry in logs if log_entry.get("operator_id")}
            username_map: Dict[str, str] = {}
            if operator_ids:
                try:
                    from app.modules.auth.repository.models import UserDoc
                    users = await UserDoc.find(
                        {"user_id": {"$in": list(operator_ids)}}
                    ).to_list()
                    username_map = {u.user_id: u.username for u in users if u.username}
                except Exception:
                    pass
            for log_entry in logs:
                operator_id = log_entry.get("operator_id", "")
                username = username_map.get(operator_id, "")

                activities.append(ProjectActivityResponse(
                    id=str(log_entry.get("_id", "")),
                    time=log_entry.get("created_at", datetime.now(timezone.utc)),
                    user_id=operator_id,
                    username=username,
                    action=log_entry.get("action", ""),
                    target=log_entry.get("work_item", {}).get("title", ""),
                    target_type=log_entry.get("work_item", {}).get("type_code", ""),
                ))
        except Exception as e:
            logger.warning(f"获取项目动态失败: {e}")

        return activities

    # ── 演示数据生成 ───────────────────────────────────────────────────

    @staticmethod
    async def generate_demo_data(project_id: str) -> GenerateDemoResponse:
        """生成演示数据。"""
        # 校验项目存在（不存在会抛 ProjectNotFoundError），返回值此处不需要
        await ProjectService.get_project(project_id)

        # 查找或创建演示执行计划
        from app.modules.execution_plan.repository.models import ExecutionPlanDoc, ExecutionPlanItemDoc
        from app.modules.workflow.repository.models.business import BusFlowLogDoc, BusWorkItemDoc
        plan_id = f"DEMO-PLAN-{project_id[-6:]}"
        plan = await ExecutionPlanDoc.find_one({"plan_id": plan_id})
        if plan is None:
            plan = ExecutionPlanDoc(
                plan_id=plan_id,
                title=f"演示执行计划 ({project_id[-6:]})",
                description="系统生成的演示数据",
                status="active",
                project_ids=[project_id],
                created_by="system",
            )
            await plan.insert()

        # 演示数据
        demo_items = [
            {"case_title": "用户登录-正常流程验证", "ref_type": "manual", "status": "done", "priority": "P0"},
            {"case_title": "用户登录-密码错误处理", "ref_type": "manual", "status": "done", "priority": "P0"},
            {"case_title": "权限管理-管理员角色验证", "ref_type": "manual", "status": "done", "priority": "P1"},
            {"case_title": "权限管理-只读用户权限验证", "ref_type": "manual", "status": "fail", "priority": "P1"},
            {"case_title": "数据导出-CSV格式验证", "ref_type": "manual", "status": "done", "priority": "P2"},
            {"case_title": "数据导出-Excel格式验证", "ref_type": "manual", "status": "fail", "priority": "P2"},
            {"case_title": "接口安全扫描-P0用例", "ref_type": "auto", "status": "pending", "priority": "P0"},
            {"case_title": "性能测试-并发请求", "ref_type": "auto", "status": "running", "priority": "P1"},
            {"case_title": "UI兼容性-深色模式", "ref_type": "manual", "status": "running", "priority": "P2"},
            {"case_title": "消息推送-实时通知验证", "ref_type": "auto", "status": "pending", "priority": "P1"},
        ]

        assignees = ["admin001", "user002", "user003", "user004"]
        now = datetime.now(timezone.utc)
        created_items = 0
        created_activities = 0

        for i, item_data in enumerate(demo_items):
            existing = await ExecutionPlanItemDoc.find_one(
                {"plan_id": plan_id, "case_title": item_data["case_title"]}
            )
            if existing:
                continue

            item = ExecutionPlanItemDoc(
                item_id=f"DEMO-ITEM-{project_id[-6:]}-{i+1:03d}",
                plan_id=plan_id,
                ref_type=item_data["ref_type"],
                case_id=f"DEMO-CASE-{i+1:03d}",
                case_title=item_data["case_title"],
                priority=item_data["priority"],
                assignee_id=random.choice(assignees),
                status=item_data["status"],
                order_no=i + 1,
            )
            await item.insert()
            created_items += 1

        # 更新计划计数
        total_items = await ExecutionPlanItemDoc.find(
            {"plan_id": plan_id, "is_deleted": False}
        ).count()
        done_items = await ExecutionPlanItemDoc.find(
            {"plan_id": plan_id, "is_deleted": False, "status": "done"}
        ).count()
        plan.item_count = total_items
        plan.done_count = done_items
        plan.progress_percent = round(done_items / total_items * 100) if total_items > 0 else 0
        await plan.save()

        # ── 创建演示工作流事项 + 流转日志（用于"最近动态"） ──
        demo_work_items = [
            {"title": "用户登录功能需求", "type_code": "requirement", "content": "用户登录模块的功能需求"},
            {"title": "权限管理功能需求", "type_code": "requirement", "content": "权限分级管理的功能需求"},
            {"title": "数据导出功能需求", "type_code": "requirement", "content": "数据导出模块的功能需求"},
            {"title": "用户登录-正常流程验证", "type_code": "test_case", "content": "验证用户登录正常流程"},
            {"title": "权限管理-管理员角色验证", "type_code": "test_case", "content": "验证管理员角色权限"},
        ]

        demo_actions = [
            ("SUBMIT_REVIEW", "DRAFT", "PENDING_REVIEW"),
            ("APPROVE", "PENDING_REVIEW", "PENDING_DEVELOP"),
            ("START_DEVELOP", "PENDING_DEVELOP", "DEVELOPING"),
            ("SUBMIT_TEST", "DEVELOPING", "PENDING_TEST"),
            ("PASS_TEST", "PENDING_TEST", "DONE"),
        ]

        operators = ["admin001", "user002", "user003"]

        for w_item in demo_work_items:
            # 检查是否已存在
            existing_wi = await BusWorkItemDoc.find_one(
                {"title": w_item["title"], "project_ids": {"$in": [project_id]}}
            )
            if existing_wi:
                continue

            # 创建 BusWorkItemDoc
            work_item = BusWorkItemDoc(
                type_code=w_item["type_code"],
                title=w_item["title"],
                content=w_item["content"],
                current_state="DONE",
                current_owner_id="admin001",
                creator_id="admin001",
                project_ids=[project_id],
            )
            await work_item.insert()

            # 为该工作项创建 2-3 条流转日志
            num_logs = random.randint(2, 3)
            for j in range(num_logs):
                action_name, from_state, to_state = demo_actions[j]
                log_time = now - timedelta(hours=random.randint(1, 48), minutes=random.randint(0, 59))
                flow_log = BusFlowLogDoc(
                    work_item_id=work_item.id,
                    from_state=from_state,
                    to_state=to_state,
                    action=action_name,
                    operator_id=random.choice(operators),
                    payload={},
                )
                # 手动设置 created_at（因为 TimestampedDocumentMixin 自动设值为 now）
                flow_log.created_at = log_time
                await flow_log.insert()
                created_activities += 1

        return GenerateDemoResponse(
            plan_items_created=created_items,
            activities_created=created_activities,
        )

    # ── 工具 ──────────────────────────────────────────────────────────

    @staticmethod
    async def _generate_project_id() -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"{PROJECT_ID_PREFIX}-{year}-"
        last = await ProjectDoc.find(
            {"project_id": {"$regex": f"^{prefix}"}},
            sort=[("project_id", -1)],
        ).limit(1).to_list()
        seq = 1
        if last:
            seq = int(last[0].project_id.split("-")[-1]) + 1
        return f"{prefix}{seq:05d}"
