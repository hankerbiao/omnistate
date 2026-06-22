"""通知模板常量。"""

from typing import Final


class NotificationTypes:
    """通知类型常量，用于延迟聚合的分组 key。"""

    EXECUTION_TASK_ASSIGN: Final[str] = "execution_task_assign"
    EXECUTION_TASK_REASSIGN: Final[str] = "execution_task_reassign"
    EXECUTION_TASK_RERUN: Final[str] = "execution_task_rerun"
    WORKFLOW_ITEM_TRANSITION: Final[str] = "workflow_item_transition"
    WORKFLOW_ITEM_REASSIGN: Final[str] = "workflow_item_reassign"


class NotificationTitles:
    """通知标题常量。"""

    EXECUTION_REASSIGN: Final[str] = "执行任务改派"
    EXECUTION_ASSIGN: Final[str] = "执行任务指派"
    EXECUTION_RERUN: Final[str] = "执行任务重新指派"
    WORKFLOW_TRANSITION: Final[str] = "工作项流转"
    WORKFLOW_REASSIGN: Final[str] = "工作项改派"
    BATCH_SUMMARY: Final[str] = "待处理通知汇总"


class NotificationTemplates:
    """通知内容模板。"""

    EXECUTION_REASSIGN: Final[str] = "计划「{plan_title}」中的用例「{case_title}」已改派给您执行"
    EXECUTION_ASSIGN_SINGLE: Final[str] = "计划「{plan_title}」中的用例「{case_title}」已指派给您执行"
    EXECUTION_ASSIGN_BATCH: Final[str] = "计划「{plan_title}」中有 {count} 项用例已指派给您执行"
    EXECUTION_RERUN: Final[str] = "计划「{plan_title}」中的用例「{case_title}」已重新指派给您执行"
    WORKFLOW_TRANSITION: Final[str] = "「{type_code}」{title} 已流转至您处理"
    WORKFLOW_REASSIGN: Final[str] = "「{type_code}」{title} 已改派至您"

    # 延迟聚合通知模板
    BATCH_BODY: Final[str] = "您有 {count} 条待处理通知：\n\n{details}"
    BATCH_ITEM_LINE: Final[str] = "[{action}] {content}"
    BATCH_MORE_ITEMS: Final[str] = "... 还有 {remaining} 条"
