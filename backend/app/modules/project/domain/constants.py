"""项目模块常量定义。"""

from __future__ import annotations

from enum import Enum

from typing import List, Tuple


class ProjectStatus(str, Enum):
    """项目状态。"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectMemberRole(str, Enum):
    PROJECT_ADMIN = "PROJECT_ADMIN"
    PROJECT_MAINTAINER = "PROJECT_MAINTAINER"
    PROJECT_REVIEWER = "PROJECT_REVIEWER"
    PROJECT_VIEWER = "PROJECT_VIEWER"


class ProjectDocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class ProjectReviewDecision(str, Enum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"


# project_id 前缀格式：PRJ-YYYY-XXXXX
PROJECT_ID_PREFIX = "PRJ"

# ── 项目关联的实体模型（路径, 类名） ──────────────────────────────
# 用于统计查询、删除清理、数据迁移。新增关联集合时只需在此添加。
PROJECT_RELATED_MODEL_PATHS: List[Tuple[str, str]] = [
    ("app.modules.test_specs.repository.models", "TestCaseDoc"),
    ("app.modules.test_specs.repository.models", "AutomationTestCaseDoc"),
    ("app.modules.test_specs.repository.models", "TestRequirementDoc"),
    ("app.modules.workflow.repository.models", "BusWorkItemDoc"),
]
