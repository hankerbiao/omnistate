from typing import Optional, List
from enum import Enum
from sqlmodel import Field, SQLModel, Column, JSON

class SysWorkType(SQLModel, table=True):
    """
    事项类型定义表
    - 主要功能：维护系统支持的业务事项类型（如 REQUIREMENT、TEST_CASE）
    - 典型用法：与 BusWorkItem.type_code 关联，用于流程规则按类型区分
    - 关键字段：
      - code：类型唯一编码，作为主键
      - name：类型显示名称
    """
    code: str = Field(primary_key=True)  # 类型编码（主键）
    name: str                             # 类型名称

class SysWorkflowState(SQLModel, table=True):
    """
    流程状态定义表
    - 主要功能：枚举系统中所有合法的流程状态（如 DRAFT/PENDING/DONE）
    - 典型用法：供流程配置与审计日志引用，确保状态值规范
    - 关键字段：
      - code：状态编码，主键
      - name：状态显示名称
      - is_end：是否为终止状态（如 DONE）
    """
    code: str = Field(primary_key=True)   # 状态编码（主键）
    name: str                              # 状态名称
    is_end: bool = Field(default=False)    # 是否为终点状态

class OwnerStrategy(str, Enum):
    """
    目标处理人策略常量
    - KEEP: 保持当前处理人不变
    - TO_CREATOR: 流转给事项创建者
    - TO_SPECIFIC_USER: 流转给指定用户（通常从 form_data 中获取）
    """
    KEEP = "KEEP"
    TO_CREATOR = "TO_CREATOR"
    TO_SPECIFIC_USER = "TO_SPECIFIC_USER"

class SysWorkflowConfig(SQLModel, table=True):
    """
    流程配置（Transition 地图）
    - 主要功能：定义在特定 type_code 下，从 from_state 触发 action 后流转到 to_state 的规则
    - 典型用法：在 WorkflowService.get_next_transition 中按地图匹配下一跳
    - 关键字段：
      - type_code：所属事项类型（与 SysWorkType 关联）
      - from_state/action/to_state：状态迁移三元组
      - target_owner_strategy：流转后的处理人变更策略（KEEP/TO_CREATOR/TO_SPECIFIC_USER）
      - required_fields：该步骤必填表单字段列表（JSON 持久化）
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键，自增
    type_code: str = Field(index=True)                         # 事项类型（索引）
    from_state: str                                            # 迁移起始状态
    action: str                                                # 触发动作
    to_state: str                                              # 迁移目标状态
    target_owner_strategy: str = Field(default=OwnerStrategy.KEEP)  # 处理人策略
    required_fields: List[str] = Field(default=[], sa_column=Column(JSON))  # 必填字段列表
