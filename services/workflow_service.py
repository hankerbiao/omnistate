from typing import Dict, Any, Optional, Union
from models import (
    Session, select, SysWorkflowConfig, BusWorkItem, BusFlowLog, 
    OwnerStrategy
)
from .exceptions import (
    WorkItemNotFoundError, InvalidTransitionError, MissingRequiredFieldError
)
from core.logger import log as logger

class WorkflowService:
    """
    工作流核心服务（基于有限状态机 FSM 设计）
    - 职责：管理业务事项（BusWorkItem）的状态生命周期。
    - 驱动方式：通过 SysWorkflowConfig 配置表驱动状态迁移，实现解耦。
    """
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_item(self, type_code: str, title: str, content: str, creator_id: int) -> BusWorkItem:
        """
        初始化业务事项
        - 设置初始状态为 DRAFT。
        - 默认处理人为创建者。
        """
        logger.info(f"正在创建业务事项: type={type_code}, title={title}, creator={creator_id}")
        new_item = BusWorkItem(
            type_code=type_code,
            title=title,
            content=content,
            creator_id=creator_id,
            current_owner_id=creator_id,
            current_state="DRAFT"
        )
        self.session.add(new_item)
        self.session.flush()  # 获取自增 ID
        self.session.refresh(new_item)
        logger.success(f"业务事项创建成功: ID={new_item.id}, state={new_item.current_state}")
        return new_item

    def get_next_transition(self, type_code: str, current_state: str, action_val: str) -> Optional[SysWorkflowConfig]:
        """
        查询状态机迁移规则 (Transition Map)
        - 参数：事项类型、当前状态、执行动作。
        - 返回：匹配的配置对象，若无匹配则表示非法操作。
        """
        statement = select(SysWorkflowConfig).where(
            SysWorkflowConfig.type_code == type_code,
            SysWorkflowConfig.from_state == current_state,
            SysWorkflowConfig.action == action_val
        )
        return self.session.exec(statement).first()

    def handle_transition(
        self, 
        work_item_id: int, 
        action: str, 
        operator_id: int, 
        form_data: Dict[str, Any]
    ) -> BusWorkItem:
        """
        执行状态流转核心逻辑
        1. 校验：检查事项是否存在、动作是否合法。
        2. 验证：根据配置校验必填业务字段。
        3. 执行：更新事项状态及处理人。
        4. 审计：记录流转日志（BusFlowLog）。
        """
        logger.info(f"开始处理状态流转: work_item_id={work_item_id}, action={action}, operator={operator_id}")
        # 1. 获取事项实例
        work_item = self.session.get(BusWorkItem, work_item_id)
        if not work_item:
            logger.error(f"流转失败: 未找到业务事项 ID={work_item_id}")
            raise WorkItemNotFoundError(work_item_id)

        # 2. 匹配迁移规则
        config = self.get_next_transition(work_item.type_code, work_item.current_state, action)
        if not config:
            logger.error(f"流转失败: 非法操作。当前状态 {work_item.current_state} 不支持动作 {action}")
            raise InvalidTransitionError(work_item.current_state, action)

        # 3. 业务字段校验与提取 (Payload)
        # 只提取配置中声明需要的字段，防止冗余数据进入日志
        process_payload = {field: form_data[field] for field in config.required_fields if field in form_data}
        for field in config.required_fields:
            if field not in form_data:
                logger.error(f"流转失败: 缺少必填字段 {field}")
                raise MissingRequiredFieldError(field)

        # 4. 更新事项状态
        old_state = work_item.current_state
        new_state = config.to_state
        work_item.current_state = new_state
        logger.debug(f"状态迁移: {old_state} -> {new_state}")

        # 5. 应用处理人流转策略
        self._apply_owner_strategy(work_item, config, form_data)

        self.session.add(work_item)

        # 6. 写入流转日志 (用于审计和历史回溯)
        log = BusFlowLog(
            work_item_id=work_item.id,
            from_state=old_state,
            to_state=new_state,
            action=action,
            operator_id=operator_id,
            payload=process_payload
        )
        self.session.add(log)

        self.session.flush()
        self.session.refresh(work_item)
        logger.success(f"状态流转完成: ID={work_item.id}, new_state={work_item.current_state}")

        return work_item

    def _apply_owner_strategy(self, work_item: BusWorkItem, config: SysWorkflowConfig, form_data: Dict[str, Any]) -> None:
        """
        内部逻辑：根据策略更新当前处理人 (Owner)
        - TO_CREATOR: 回退/流转给事项发起人。
        - TO_SPECIFIC_USER: 流转给指定的具体用户。
        """
        if config.target_owner_strategy == OwnerStrategy.TO_CREATOR:
            work_item.current_owner_id = work_item.creator_id
        elif config.target_owner_strategy == OwnerStrategy.TO_SPECIFIC_USER:
            target_owner_id = form_data.get("target_owner_id")
            if not target_owner_id:
                raise MissingRequiredFieldError("target_owner_id")
            work_item.current_owner_id = target_owner_id
