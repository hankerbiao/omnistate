from enum import Enum

# OwnerStrategy 定义在 domain 层（纯领域概念），此处 re-export 保持向后兼容。
# 避免新增 repository.enums 的导入方破坏；同时消除 domain → repository 的反向依赖。
from app.modules.workflow.domain.enums import OwnerStrategy  # noqa: F401


class WorkItemState(str, Enum):
    """业务事项状态"""
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    PENDING_DEVELOP = "PENDING_DEVELOP"
    DEVELOPING = "DEVELOPING"
    PENDING_TEST = "PENDING_TEST"
    PENDING_UAT = "PENDING_UAT"
    PENDING_RELEASE = "PENDING_RELEASE"
    RELEASED = "RELEASED"
    DONE = "DONE"
    REJECTED = "REJECTED"
    PENDING_AUDIT = "PENDING_AUDIT"
    ASSIGNED = "ASSIGNED"
