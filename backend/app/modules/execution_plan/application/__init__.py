"""执行计划 application 层。

提供 CQRS 分离：
- PlanCommandService：写操作编排（CRUD + 跨模块副作用）
- PlanQueryService：只读查询
- Port 接口：解耦 execution、notification 模块的直接依赖
"""

from .plan_command_service import PlanCommandService
from .plan_query_service import PlanQueryService
from .ports import ExecutionDispatchPort, PlanNotificationPort

__all__ = [
    "ExecutionDispatchPort",
    "PlanCommandService",
    "PlanNotificationPort",
    "PlanQueryService",
]
