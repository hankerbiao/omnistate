class WorkflowError(Exception):
    """工作流基础异常"""
    pass


class WorkItemNotFoundError(WorkflowError):
    """事项不存在异常"""

    def __init__(self, work_item_id: int):
        super().__init__(f"事项 ID={work_item_id} 不存在")


class InvalidTransitionError(WorkflowError):
    """非法状态流转异常"""

    def __init__(self, state: str, action: str):
        super().__init__(f"当前状态 '{state}' 不支持动作 '{action}'")


class MissingRequiredFieldError(WorkflowError):
    """缺失必填字段异常"""

    def __init__(self, field: str):
        super().__init__(f"缺少节点必要字段: {field}")


class PermissionDeniedError(WorkflowError):
    """权限不足异常"""

    def __init__(self, user_id: int, action: str):
        super().__init__(f"用户 ID={user_id} 无权执行动作 '{action}'")
