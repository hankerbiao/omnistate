"""执行计划领域异常。"""


class ExecutionPlanError(Exception):
    """执行计划基础异常。"""


class PlanNotFoundError(ExecutionPlanError):
    """计划不存在。"""

    def __init__(self, plan_id: str):
        super().__init__(f"执行计划 ID={plan_id} 不存在")


class ItemNotFoundError(ExecutionPlanError):
    """计划条目不存在。"""

    def __init__(self, item_id: str):
        super().__init__(f"计划条目 ID={item_id} 不存在")


class ResultNotFoundError(ExecutionPlanError):
    """手工回填结果不存在。"""

    def __init__(self, item_id: str):
        super().__init__(f"条目 ID={item_id} 尚无手工回填结果")
