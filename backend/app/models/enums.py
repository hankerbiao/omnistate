from enum import Enum

class OwnerStrategy(str, Enum):
    """处理人流转策略"""
    KEEP = "KEEP"                      # 保持当前处理人
    TO_CREATOR = "TO_CREATOR"          # 流转回创建者
    TO_SPECIFIC_USER = "TO_SPECIFIC_USER"  # 流转给指定用户

class WorkItemState(str, Enum):
    """业务事项状态"""
    DRAFT = "DRAFT"
    # 可以根据业务需求添加更多
