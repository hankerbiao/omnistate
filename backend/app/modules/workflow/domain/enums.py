"""工作流领域枚举。

纯领域概念，不依赖 HTTP / 数据库 / ODM。
定义在 domain 层，repository 层通过 re-export 复用，避免反向依赖。
"""
from __future__ import annotations

from enum import Enum


class OwnerStrategy(str, Enum):
    """处理人流转策略。

    决定工作项流转后新的处理人如何确定，是纯领域规则。
    """
    KEEP = "KEEP"  # 保持当前处理人
    TO_CREATOR = "TO_CREATOR"  # 流转回创建者
    TO_SPECIFIC_USER = "TO_SPECIFIC_USER"  # 流转给指定用户
