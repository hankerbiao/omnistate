"""项目模块常量定义。"""

from __future__ import annotations

from enum import Enum

from typing import List, Tuple


class ProjectStatus(str, Enum):
    """项目状态。"""
    ACTIVE = "active"
    ARCHIVED = "archived"


# project_id 前缀格式：PRJ-YYYY-XXXXX
PROJECT_ID_PREFIX = "PRJ"

# ── 项目关联的实体模型（路径, 类名） ──────────────────────────────
# 用于统计查询、删除清理、数据迁移。新增关联集合时只需在此添加。
PROJECT_RELATED_MODEL_PATHS: List[Tuple[str, str]] = [
    ("app.modules.test_specs.repository.models", "TestCaseDoc"),
    ("app.modules.test_specs.repository.models", "AutomationTestCaseDoc"),
    ("app.modules.test_specs.repository.models", "TestRequirementDoc"),
    ("app.modules.execution_plan.repository.models", "ExecutionPlanDoc"),
    ("app.modules.execution.repository.models", "ExecutionTaskDoc"),
    ("app.modules.workflow.repository.models", "BusWorkItemDoc"),
    ("app.modules.test_case_collection.repository.models", "TestCaseCollectionDoc"),
]
