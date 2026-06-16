"""统一枚举 API。

提供 GET /api/v1/enums 端点，返回系统全部枚举值列表。
前端据此动态渲染可选项，避免前端硬编码枚举值。
展示样式（标签文本、颜色等）由前端自行管理。
"""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.execution.application.constants import (
    FINAL_TASK_STATUSES,
    AgentStatus,
    CaseStatus,
    ConsumeStatus,
    DispatchStatus,
    OverallStatus,
    ScheduleStatus,
)
from app.modules.execution_plan.domain.constants import (
    TASK_TO_ITEM_STATUS,
    PlanItemStatus,
    PlanStatus,
)
from app.modules.test_specs.repository.models.requirement import (
    REQUIREMENT_CATEGORY_CHOICES,
    REQUIREMENT_SOURCE_CHOICES,
)
from app.modules.workflow.repository.models.enums import (
    OwnerStrategy,
    WorkItemState,
)
from app.shared.api.schemas.base import APIResponse

router = APIRouter(prefix="/enums", tags=["Enums"])


@router.get(
    "",
    response_model=APIResponse[dict],
    summary="获取系统全部枚举常量",
)
async def get_all_enums():
    """获取系统全部枚举值列表。"""
    return APIResponse(data={
        # 工作流
        "workflow_states": [s.value for s in WorkItemState],
        "owner_strategies": [s.value for s in OwnerStrategy],

        # 测试用例
        "priority": ["P0", "P1", "P2", "P3"],
        "requirement_category": list(REQUIREMENT_CATEGORY_CHOICES),
        "requirement_source": list(REQUIREMENT_SOURCE_CHOICES),
        "automation_case_status": ["ACTIVE", "INACTIVE", "DRAFT", "DEPRECATED"],
        "manual_case_status": ["DRAFT", "PENDING_REVIEW", "IN_REVIEW", "REVISE", "DONE", "REJECTED"],
        "confidentiality": ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"],
        "visibility_scope": ["PUBLIC", "TEAM", "PRIVATE"],
        "risk_level": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "test_category": [
            "FUNCTIONAL", "PERFORMANCE", "STABILITY",
            "COMPATIBILITY", "SECURITY", "REGRESSION",
            "SMOKE", "STRESS",
        ],

        # 执行任务
        "execution_overall_status": [s.value for s in OverallStatus],
        "execution_case_status": [s.value for s in CaseStatus],
        "execution_dispatch_status": [s.value for s in DispatchStatus],
        "execution_schedule_status": [s.value for s in ScheduleStatus],
        "execution_consume_status": [s.value for s in ConsumeStatus],
        "execution_agent_status": [s.value for s in AgentStatus],
        "execution_final_statuses": [s.value for s in FINAL_TASK_STATUSES],

        # 执行计划
        "plan_item_status": [s.value for s in PlanItemStatus],
        "plan_status": [s.value for s in PlanStatus],
        "task_to_item_status": {k: v.value for k, v in TASK_TO_ITEM_STATUS.items()},

        # 系统配置
        "config_types": ["string", "integer", "float", "boolean", "json"],
        "config_categories": ["ai", "system", "general"],
    })
