from typing import Dict, Any, Optional, List
from beanie import PydanticObjectId

from app.models import (
    SysWorkflowConfigDoc, BusWorkItemDoc, BusFlowLogDoc,
    SysWorkTypeDoc, SysWorkflowStateDoc, OwnerStrategy, WorkItemState,
)
from .exceptions import (
    WorkItemNotFoundError, InvalidTransitionError, MissingRequiredFieldError
)
from ..core.logger import log as logger


class WorkflowMongoDBService:
    """
    工作流核心服务 (Beanie ODM 版本)
    - 职责：管理业务事项（BusWorkItem）的状态生命周期。
    - 驱动方式：通过 SysWorkflowConfigDoc 配置表驱动状态迁移，实现解耦。
    """

    def __init__(self) -> None:
        """初始化服务，Beanie 使用全局初始化，无需显式传递 db"""
        pass

    # ========== 查询方法 ==========

    async def get_work_types(self) -> List[Dict]:
        """获取所有业务事项类型"""
        docs = await SysWorkTypeDoc.find_all().to_list()
        return [doc.model_dump() for doc in docs]

    async def get_workflow_states(self) -> List[Dict]:
        """获取所有流程状态"""
        docs = await SysWorkflowStateDoc.find_all().to_list()
        return [doc.model_dump() for doc in docs]

    async def get_workflow_configs(self, type_code: str) -> List[Dict]:
        """获取指定类型的所有流转配置"""
        docs = await SysWorkflowConfigDoc.find(SysWorkflowConfigDoc.type_code == type_code).to_list()
        return [doc.model_dump() for doc in docs]

    async def list_items(
            self,
            type_code: Optional[str] = None,
            state: Optional[str] = None,
            owner_id: Optional[int] = None,
            creator_id: Optional[int] = None,
            limit: int = 20,
            offset: int = 0
    ) -> List[Dict]:
        """查询业务事项列表"""
        query = BusWorkItemDoc.find(BusWorkItemDoc.is_deleted == False)

        if type_code:
            query = query.find(BusWorkItemDoc.type_code == type_code)
        if state:
            query = query.find(BusWorkItemDoc.current_state == state)

        # 构建 OR 条件
        or_conditions = []
        if owner_id is not None:
            or_conditions.append(BusWorkItemDoc.current_owner_id == owner_id)
        if creator_id is not None:
            or_conditions.append(BusWorkItemDoc.creator_id == creator_id)

        if or_conditions:
            query = query.find({"$or": or_conditions})

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        # 将 Beanie 文档转换为字典，并确保 id 字段作为字符串存在
        results = []
        for doc in docs:
            d = doc.model_dump()
            d["id"] = str(doc.id)
            results.append(d)
        return results

    async def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """根据 ID 获取业务事项详情"""
        try:
            # 确保 item_id 是有效的 ObjectId 格式
            if not PydanticObjectId.is_valid(item_id):
                return None
            doc = await BusWorkItemDoc.get(item_id)
            if doc and not doc.is_deleted:
                d = doc.model_dump()
                d["id"] = str(doc.id)
                return d
        except Exception as e:
            # 记录异常但对于“未找到”类的错误可以根据需要处理，
            # 这里的 catch all 主要是为了防止非法的 ObjectId 导致程序崩溃
            logger.warning(f"获取事项 {item_id} 时发生错误: {e}")
            pass
        return None

    async def get_logs(self, item_id: str, limit: int = 50) -> List[Dict]:
        """获取指定事项的流转日志"""
        # 先验证事项是否存在
        item = await self.get_item_by_id(item_id)
        if not item:
            raise WorkItemNotFoundError(item_id)

        docs = await BusFlowLogDoc.find(BusFlowLogDoc.work_item_id == item_id).sort("-created_at").limit(
            limit).to_list()
        results = []
        for doc in docs:
            d = doc.model_dump()
            d["id"] = str(doc.id)
            d["work_item_id"] = str(doc.work_item_id)
            results.append(d)
        return results

    async def batch_get_logs(self, item_ids: List[str], limit: int = 20) -> Dict[str, List[Dict]]:
        """批量获取多个事项的流转日志"""
        if not item_ids:
            return {}

        # 使用 $in 查询所有相关日志，减少数据库往返次数
        object_ids = [PydanticObjectId(item_id) for item_id in item_ids]
        all_logs = await BusFlowLogDoc.find(
            {"work_item_id": {"$in": object_ids}}
        ).sort("-created_at").to_list()

        # 按 work_item_id 分组并应用 limit
        result: Dict[str, List[Dict]] = {item_id: [] for item_id in item_ids}
        for log_doc in all_logs:
            wid = str(log_doc.work_item_id)
            if wid in result and len(result[wid]) < limit:
                d = log_doc.model_dump()
                d["id"] = str(log_doc.id)
                d["work_item_id"] = str(log_doc.work_item_id)
                result[wid].append(d)

        return result

    async def get_item_with_transitions(self, item_id: str) -> Dict[str, Any]:
        """获取事项详情及其当前可用的流转动作"""
        item = await self.get_item_by_id(item_id)
        if not item:
            raise WorkItemNotFoundError(item_id)

        configs = await SysWorkflowConfigDoc.find(
            SysWorkflowConfigDoc.type_code == item["type_code"],
            SysWorkflowConfigDoc.from_state == item["current_state"]
        ).to_list()

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

    async def get_next_transition(self, type_code: str, from_state: str, action: str) -> Optional[Dict]:
        """查找匹配的迁移规则"""
        doc = await SysWorkflowConfigDoc.find_one(
            SysWorkflowConfigDoc.type_code == type_code,
            SysWorkflowConfigDoc.from_state == from_state,
            SysWorkflowConfigDoc.action == action
        )
        return doc.model_dump() if doc else None

    # ========== 核心流转逻辑 ==========

    async def create_item(self, type_code: str, title: str, content: str, creator_id: int) -> Dict:
        """创建业务事项"""
        try:
            new_item = BusWorkItemDoc(
                type_code=type_code,
                title=title,
                content=content,
                creator_id=creator_id,
                current_owner_id=creator_id,
                current_state=WorkItemState.DRAFT.value
            )
            await new_item.insert()
            logger.success(f"业务事项创建成功: ID={new_item.id}, state={new_item.current_state}")
            d = new_item.model_dump()
            d["id"] = str(new_item.id)
            return d
        except Exception as e:
            logger.error(f"创建业务事项失败: {e}")
            raise

    async def handle_transition(
            self,
            work_item_id: str,
            action: str,
            operator_id: int,
            form_data: Dict[str, Any]
    ) -> Dict:
        """执行状态流转核心逻辑 (单机模式，无事务)"""
        logger.info(f"开始处理状态流转: work_item_id={work_item_id}, action={action}, operator={operator_id}")

        # 1. 获取事项实例
        item_doc = await BusWorkItemDoc.get(work_item_id)
        if not item_doc or item_doc.is_deleted:
            logger.error(f"流转失败: 未找到业务事项 ID={work_item_id}")
            raise WorkItemNotFoundError(work_item_id)

        # 2. 匹配迁移规则
        config_doc = await SysWorkflowConfigDoc.find_one(
            SysWorkflowConfigDoc.type_code == item_doc.type_code,
            SysWorkflowConfigDoc.from_state == item_doc.current_state,
            SysWorkflowConfigDoc.action == action
        )
        if not config_doc:
            logger.error(f"流转失败: 非法操作。当前状态 {item_doc.current_state} 不支持动作 {action}")
            raise InvalidTransitionError(item_doc.current_state, action)

        # 3. 业务字段校验
        required_fields = config_doc.required_fields
        for field in required_fields:
            if field not in form_data:
                logger.error(f"流转失败: 缺少必填字段 {field}")
                raise MissingRequiredFieldError(field)

        process_payload = {field: form_data[field] for field in required_fields}

        # 4. 更新事项状态
        old_state = item_doc.current_state
        new_state = config_doc.to_state

        # 5. 应用处理人流转策略
        new_owner_id = self._apply_owner_strategy(item_doc.model_dump(), config_doc.model_dump(), form_data)

        # 6. 执行更新
        item_doc.current_state = new_state
        item_doc.current_owner_id = new_owner_id
        await item_doc.save()

        # 7. 写入流转日志
        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(work_item_id),
            from_state=old_state,
            to_state=new_state,
            action=action,
            operator_id=operator_id,
            payload=process_payload
        )
        await log_entry.insert()

        logger.success(f"状态流转完成: ID={work_item_id}, new_state={new_state}")

        # 确保 work_item 包含字符串 ID
        item_dict = item_doc.model_dump()
        item_dict["id"] = str(item_doc.id)

        return {
            "work_item_id": str(item_doc.id),
            "from_state": old_state,
            "to_state": new_state,
            "action": action,
            "new_owner_id": new_owner_id,
            "work_item": item_dict
        }

    def _apply_owner_strategy(
            self,
            work_item: Dict[str, Any],
            config: Dict[str, Any],
            form_data: Dict[str, Any]
    ) -> Optional[int]:
        """内部逻辑：根据策略更新当前处理人 (Owner)"""
        strategy = config.get("target_owner_strategy", "KEEP")
        logger.debug(f"正在应用处理人流转策略: {strategy}")

        if strategy == OwnerStrategy.TO_CREATOR.value:
            new_owner_id = work_item["creator_id"]
            return new_owner_id
        elif strategy == OwnerStrategy.TO_SPECIFIC_USER.value:
            target_owner_id = form_data.get("target_owner_id")
            if not target_owner_id:
                raise MissingRequiredFieldError("target_owner_id")
            return target_owner_id
        else:
            return work_item.get("current_owner_id")

    async def delete_item(self, item_id: str) -> bool:
        """逻辑删除业务事项 (单机模式，无事务)"""
        item_doc = await BusWorkItemDoc.get(item_id)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)

        # 记录删除日志
        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(item_id),
            from_state=item_doc.current_state,
            to_state=item_doc.current_state,
            action="DELETE",
            operator_id=item_doc.creator_id,
            payload={"info": "Soft deleted"}
        )
        await log_entry.insert()

        item_doc.is_deleted = True
        await item_doc.save()
        logger.success(f"事项 ID={item_id} 已逻辑删除")
        return True

    async def reassign_item(self, item_id: str, operator_id: int, target_owner_id: int) -> Dict:
        """改派任务给其他处理人 (单机模式，无事务)"""
        item_doc = await BusWorkItemDoc.get(item_id)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)

        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(item_id),
            from_state=item_doc.current_state,
            to_state=item_doc.current_state,
            action="REASSIGN",
            operator_id=operator_id,
            payload={"target_owner_id": target_owner_id}
        )
        await log_entry.insert()

        item_doc.current_owner_id = target_owner_id
        await item_doc.save()

        d = item_doc.model_dump()
        d["id"] = str(item_doc.id)
        return d


# 别名
AsyncWorkflowService = WorkflowMongoDBService
