from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import Field, SQLModel, Column, JSON

class BusWorkItem(SQLModel, table=True):
    """
    业务事项实体（FlowInstance 快照）
    - 主要功能：承载一个业务事项的当前状态、处理人以及基础信息
    - 典型用法：在 WorkflowService.handle_transition 中读取与更新，以推进状态机
    - 关键字段含义：
      - current_state：当前流程状态（如 DRAFT/PENDING/DONE），由流程规则驱动变更
      - current_owner_id：当前处理人，REJECT 等动作可能回指给创建者
      - creator_id：事项创建者，用于权限与回指场景
      - created_at：创建时间，用于审计/排序
    - 约束与关系：
      - 与 BusFlowLog 通过 work_item_id 建立一对多的审计记录关系
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键，自增
    type_code: str                                            # 事项类型标识（与流程配置关联）
    title: str                                                # 标题
    content: str                                              # 内容/描述
    current_state: str = Field(default="DRAFT")               # 当前状态指针（状态机核心）
    current_owner_id: Optional[int] = None                    # 当前处理人（可能为空）
    creator_id: int                                           # 创建者用户ID
    created_at: datetime = Field(default_factory=datetime.now)# 创建时间戳

class BusFlowLog(SQLModel, table=True):
    """
    流转审计日志（Transition 记录）
    - 主要功能：记录每次状态变更的轨迹与上下文数据，用于审计与回溯
    - 典型用法：通过 work_item_id 查询该事项的所有流转历史（见 workflow.py 日志查询）
    - 关键字段含义：
      - from_state/to_state：状态迁移的起点与终点
      - action：触发迁移的动作（如 SUBMIT/REJECT/APPROVE）
      - operator_id：执行该动作的操作者
      - payload：节点特有表单数据（如 priority/reason/comment），便于保留过程信息
      - created_at：日志创建时间
    - 约束与关系：
      - work_item_id 与 BusWorkItem.id 关联（一对多）
    """
    id: Optional[int] = Field(default=None, primary_key=True)                 # 主键，自增
    work_item_id: int = Field(index=True)                                     # 关联事项ID（索引加速查询）
    from_state: str                                                           # 变更前状态
    to_state: str                                                             # 变更后状态
    action: str                                                               # 触发动作
    operator_id: int                                                          # 操作人ID
    payload: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))       # 节点特有表单数据
    created_at: datetime = Field(default_factory=datetime.now)                # 创建时间戳
