from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_

from models import (
    SysWorkflowConfig, BusWorkItem, BusFlowLog,
    OwnerStrategy, SysWorkType, SysWorkflowState
)
from .exceptions import (
    WorkItemNotFoundError, InvalidTransitionError, MissingRequiredFieldError
)
from core.logger import log as logger


class AsyncWorkflowService:
    """
    工作流核心服务（异步版本，基于有限状态机 FSM 设计）
    - 职责：管理业务事项（BusWorkItem）的状态生命周期。
    - 驱动方式：通过 SysWorkflowConfig 配置表驱动状态迁移，实现解耦。
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_work_types(self) -> List[SysWorkType]:
        """获取所有业务事项类型"""
        stmt = select(SysWorkType)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_workflow_states(self) -> List[SysWorkflowState]:
        """获取所有流程状态"""
        stmt = select(SysWorkflowState)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_workflow_configs(self, type_code: str) -> List[SysWorkflowConfig]:
        """获取指定类型的所有流转配置"""
        stmt = select(SysWorkflowConfig).where(SysWorkflowConfig.type_code == type_code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_items(
            self,
            type_code: Optional[str] = None,
            state: Optional[str] = None,
            owner_id: Optional[int] = None,
            creator_id: Optional[int] = None,
            limit: int = 20,
            offset: int = 0
    ) -> List[BusWorkItem]:
        """查询业务事项列表，支持多种筛选条件"""
        stmt = select(BusWorkItem)

        if type_code:
            stmt = stmt.where(BusWorkItem.type_code == type_code)
        if state:
            stmt = stmt.where(BusWorkItem.current_state == state)

        if owner_id is not None and creator_id is not None:
            stmt = stmt.where(
                or_(
                    BusWorkItem.current_owner_id == owner_id,
                    BusWorkItem.creator_id == creator_id
                )
            )
        elif owner_id is not None:
            stmt = stmt.where(BusWorkItem.current_owner_id == owner_id)
        elif creator_id is not None:
            stmt = stmt.where(BusWorkItem.creator_id == creator_id)

        stmt = stmt.order_by(desc(BusWorkItem.created_at)).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_item(self, item_id: int) -> bool:
        """删除业务事项及其关联的流转日志"""
        item = await self.session.get(BusWorkItem, item_id)
        if not item:
            raise WorkItemNotFoundError(item_id)

        try:
            # 删除关联日志
            stmt = select(BusFlowLog).where(BusFlowLog.work_item_id == item_id)
            logs_result = await self.session.execute(stmt)
            logs = logs_result.scalars().all()
            for log in logs:
                await self.session.delete(log)

            # 删除事项
            await self.session.delete(item)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"删除事项失败 ID={item_id}: {e}")
            raise

    async def reassign_item(self, item_id: int, operator_id: int, target_owner_id: int) -> BusWorkItem:
        """改派任务给其他处理人"""
        item = await self.session.get(BusWorkItem, item_id)
        if not item:
            raise WorkItemNotFoundError(item_id)

        try:
            # 记录改派日志
            log_entry = BusFlowLog(
                work_item_id=item.id,
                from_state=item.current_state,
                to_state=item.current_state,
                action="REASSIGN",
                operator_id=operator_id,
                payload={"target_owner_id": target_owner_id}
            )
            self.session.add(log_entry)

            # 更新处理人
            item.current_owner_id = target_owner_id
            self.session.add(item)

            await self.session.commit()
            await self.session.refresh(item)
            return item
        except Exception as e:
            await self.session.rollback()
            logger.error(f"改派事项失败 ID={item_id}: {e}")
            raise

    async def get_logs(self, item_id: int, limit: int = 50) -> List[BusFlowLog]:
        """获取指定事项的流转日志"""
        item = await self.session.get(BusWorkItem, item_id)
        if not item:
            raise WorkItemNotFoundError(item_id)

        stmt = select(BusFlowLog).where(
            BusFlowLog.work_item_id == item_id
        ).order_by(desc(BusFlowLog.created_at)).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def batch_get_logs(self, item_ids: List[int], limit: int = 20) -> Dict[int, List[BusFlowLog]]:
        """批量获取多个事项的流转日志"""
        if not item_ids:
            return {}

        result_dict = {}
        for item_id in item_ids:
            # 注意：此处为简单实现，实际高并发下建议使用更优化的批量查询 SQL
            stmt = select(BusFlowLog).where(
                BusFlowLog.work_item_id == item_id
            ).order_by(desc(BusFlowLog.created_at)).limit(limit)

            logs_result = await self.session.execute(stmt)
            result_dict[item_id] = list(logs_result.scalars().all())

        return result_dict

    async def get_item_with_transitions(self, item_id: int) -> Dict[str, Any]:
        """获取事项详情及其当前可用的流转动作"""
        item = await self.session.get(BusWorkItem, item_id)
        if not item:
            raise WorkItemNotFoundError(item_id)

        stmt = select(SysWorkflowConfig).where(
            SysWorkflowConfig.type_code == item.type_code,
            SysWorkflowConfig.from_state == item.current_state
        )
        result = await self.session.execute(stmt)
        configs = result.scalars().all()

        return {
            "item": item,
            "available_transitions": [
                {
                    "action": config.action,
                    "to_state": config.to_state,
                    "target_owner_strategy": config.target_owner_strategy,
                    "required_fields": config.required_fields
                }
                for config in configs
            ]
        }

    async def create_item(self, type_code: str, title: str, content: str, creator_id: int) -> BusWorkItem:
        """
        初始化业务事项
        - 设置初始状态为 DRAFT。
        - 默认处理人为创建者。
        """
        logger.info(f"正在创建业务事项: type={type_code}, title={title}, creator={creator_id}")
        try:
            new_item = BusWorkItem(
                type_code=type_code,
                title=title,
                content=content,
                creator_id=creator_id,
                current_owner_id=creator_id,
                current_state="DRAFT"
            )
            self.session.add(new_item)
            await self.session.commit()  # 在 Service 层提交
            await self.session.refresh(new_item)
            logger.success(f"业务事项创建成功: ID={new_item.id}, state={new_item.current_state}")
            return new_item
        except Exception as e:
            await self.session.rollback()
            logger.error(f"创建业务事项失败: {e}")
            raise

    async def get_next_transition(self, type_code: str, current_state: str, action_val: str) \
            -> Optional[SysWorkflowConfig]:
        """
        查询状态机迁移规则 (Transition Map)
        - 参数：事项类型、当前状态、执行动作。
        - 返回：匹配的配置对象，若无匹配则表示非法操作。
        """

        statement = select(SysWorkflowConfig).where(
            SysWorkflowConfig.type_code == type_code,  # type: ignore
            SysWorkflowConfig.from_state == current_state,  # type: ignore
            SysWorkflowConfig.action == action_val  # type: ignore
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def handle_transition(
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

        try:
            # 1. 获取事项实例
            work_item = await self.session.get(BusWorkItem, work_item_id)
            if not work_item:
                logger.error(f"流转失败: 未找到业务事项 ID={work_item_id}")
                raise WorkItemNotFoundError(work_item_id)

            # 2. 匹配迁移规则
            config = await self.get_next_transition(work_item.type_code, work_item.current_state, action)
            if not config:
                logger.error(f"流转失败: 非法操作。当前状态 {work_item.current_state} 不支持动作 {action}")
                raise InvalidTransitionError(work_item.current_state, action)

            # 3. 业务字段校验与提取 (Payload)
            for field in config.required_fields:
                if field not in form_data:
                    logger.error(f"流转失败: 缺少必填字段 {field}")
                    raise MissingRequiredFieldError(field)

            # 校验通过后提取数据，防止冗余数据进入日志
            process_payload = {field: form_data[field] for field in config.required_fields}

            # 4. 更新事项状态
            old_state = work_item.current_state
            new_state = config.to_state
            work_item.current_state = new_state
            logger.debug(f"状态迁移: {old_state} -> {new_state}")

            # 5. 应用处理人流转策略
            self._apply_owner_strategy(work_item, config, form_data)

            self.session.add(work_item)

            # 6. 写入流转日志
            log_entry = BusFlowLog(
                work_item_id=work_item.id,
                from_state=old_state,
                to_state=new_state,
                action=action,
                operator_id=operator_id,
                payload=process_payload
            )
            self.session.add(log_entry)

            await self.session.commit()  # 提交事务
            await self.session.refresh(work_item)
            logger.success(f"状态流转完成: ID={work_item.id}, new_state={work_item.current_state}")

            return work_item
        except Exception as e:
            await self.session.rollback()  # 发生任何异常都回滚
            if not isinstance(e, (WorkItemNotFoundError, InvalidTransitionError, MissingRequiredFieldError)):
                logger.error(f"状态流转过程中发生未知错误: {e}")
            raise

    def _apply_owner_strategy(self, work_item: BusWorkItem, config: SysWorkflowConfig,
                              form_data: Dict[str, Any]) -> None:
        """
        内部逻辑：根据策略更新当前处理人 (Owner)
        - TO_CREATOR: 回退/流转给事项发起人。
        - TO_SPECIFIC_USER: 流转给指定的具体用户。
        """
        strategy = config.target_owner_strategy
        logger.debug(f"正在应用处理人流转策略: {strategy}")

        if strategy == OwnerStrategy.TO_CREATOR:
            work_item.current_owner_id = work_item.creator_id
            logger.debug(f"处理人已变更为创建者: {work_item.creator_id}")
        elif strategy == OwnerStrategy.TO_SPECIFIC_USER:
            target_owner_id = form_data.get("target_owner_id")
            if not target_owner_id:
                logger.error("策略应用失败: TO_SPECIFIC_USER 模式下缺失 target_owner_id")
                raise MissingRequiredFieldError("target_owner_id")
            work_item.current_owner_id = target_owner_id
            logger.debug(f"处理人已变更为指定用户: {target_owner_id}")
        elif strategy == OwnerStrategy.KEEP:
            logger.debug("处理人保持不变")
        else:
            logger.warning(f"未知的处理人策略: {strategy}，将保持当前处理人不变")
