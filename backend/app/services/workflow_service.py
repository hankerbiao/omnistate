from typing import Dict, Any, Optional, List
from beanie import PydanticObjectId

from app.models import (
    SysWorkflowConfigDoc, BusWorkItemDoc, BusFlowLogDoc,
    SysWorkTypeDoc, SysWorkflowStateDoc, OwnerStrategy, WorkItemState,
)
from app.services.exceptions import (
    WorkItemNotFoundError, InvalidTransitionError, MissingRequiredFieldError
)
from app.core.logger import log as logger


class AsyncWorkflowService:
    # 说明：该服务负责「工作流状态机」的核心业务逻辑
    # - 所有方法均为异步方法，直接使用 Beanie 文档模型访问 MongoDB
    # - 路由层只依赖此服务，不关心底层持久化实现细节

    def __init__(self) -> None:
        # 目前无需在构造函数中注入依赖
        # 如需支持多数据源或可测试性，可在这里加入显式依赖注入
        pass

    # ========== 查询方法 ==========

    async def get_work_types(self) -> List[Dict]:
        # 查询所有「事项类型」配置，常用于前端下拉列表或配置管理页面
        docs = await SysWorkTypeDoc.find_all().to_list()
        return [doc.model_dump() for doc in docs]

    async def get_workflow_states(self) -> List[Dict]:
        # 查询所有「流程状态」配置，用于渲染状态枚举或看板列
        docs = await SysWorkflowStateDoc.find_all().to_list()
        return [doc.model_dump() for doc in docs]

    async def get_workflow_configs(self, type_code: str) -> List[Dict]:
        # 查询某个事项类型下的所有「状态流转规则」配置
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
        query = BusWorkItemDoc.find(BusWorkItemDoc.is_deleted == False)

        if type_code:
            query = query.find(BusWorkItemDoc.type_code == type_code)
        if state:
            query = query.find(BusWorkItemDoc.current_state == state)

        or_conditions = []
        if owner_id is not None:
            or_conditions.append(BusWorkItemDoc.current_owner_id == owner_id)
        if creator_id is not None:
            or_conditions.append(BusWorkItemDoc.creator_id == creator_id)

        if or_conditions:
            query = query.find({"$or": or_conditions})

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        results = []
        for doc in docs:
            d = doc.model_dump()
            d["id"] = str(doc.id)
            results.append(d)
        return results

    async def list_items_sorted(
            self,
            type_code: Optional[str] = None,
            state: Optional[str] = None,
            owner_id: Optional[int] = None,
            creator_id: Optional[int] = None,
            limit: int = 20,
            offset: int = 0,
            order_by: str = "created_at",
            direction: str = "desc"
    ) -> List[Dict]:
        query = BusWorkItemDoc.find(BusWorkItemDoc.is_deleted == False)

        if type_code:
            query = query.find(BusWorkItemDoc.type_code == type_code)
        if state:
            query = query.find(BusWorkItemDoc.current_state == state)

        or_conditions = []
        if owner_id is not None:
            or_conditions.append(BusWorkItemDoc.current_owner_id == owner_id)
        if creator_id is not None:
            or_conditions.append(BusWorkItemDoc.creator_id == creator_id)

        if or_conditions:
            query = query.find({"$or": or_conditions})

        allowed_fields = {"created_at": "created_at", "updated_at": "updated_at", "title": "title"}
        field = allowed_fields.get(order_by, "created_at")
        prefix = "-" if direction.lower() == "desc" else ""
        sort_expr = f"{prefix}{field}"

        docs = await query.sort(sort_expr).skip(offset).limit(limit).to_list()
        results = []
        for doc in docs:
            d = doc.model_dump()
            d["id"] = str(doc.id)
            results.append(d)
        return results

    async def search_items(
            self,
            keyword: str,
            type_code: Optional[str] = None,
            state: Optional[str] = None,
            owner_id: Optional[int] = None,
            creator_id: Optional[int] = None,
            limit: int = 20,
            offset: int = 0
    ) -> List[Dict]:
        query = BusWorkItemDoc.find(BusWorkItemDoc.is_deleted == False)

        if type_code:
            query = query.find(BusWorkItemDoc.type_code == type_code)
        if state:
            query = query.find(BusWorkItemDoc.current_state == state)

        or_conditions = []
        if owner_id is not None:
            or_conditions.append(BusWorkItemDoc.current_owner_id == owner_id)
        if creator_id is not None:
            or_conditions.append(BusWorkItemDoc.creator_id == creator_id)

        if or_conditions:
            query = query.find({"$or": or_conditions})

        search_conditions = [
            {"title": {"$regex": keyword, "$options": "i"}},
            {"content": {"$regex": keyword, "$options": "i"}},
        ]
        query = query.find({"$or": search_conditions})

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        results = []
        for doc in docs:
            d = doc.model_dump()
            d["id"] = str(doc.id)
            results.append(d)
        return results

    async def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        # 根据业务事项 ID 查询详情
        # - 会校验 ObjectId 合法性
        # - 会过滤掉已逻辑删除的数据
        try:
            if not PydanticObjectId.is_valid(item_id):
                return None
            doc = await BusWorkItemDoc.get(item_id)
            if doc and not doc.is_deleted:
                d = doc.model_dump()
                d["id"] = str(doc.id)
                return d
        except Exception as e:
            # 兜底捕获异常，避免非法 ID 导致接口 500
            logger.warning(f"获取事项 {item_id} 时发生错误: {e}")
            pass
        return None

    async def get_logs(self, item_id: str, limit: int = 50) -> List[Dict]:
        # 查询单个事项的流转历史
        # - 会先校验事项是否存在
        # - 按创建时间倒序返回最近若干条记录
        item = await self.get_item_by_id(item_id)
        if not item:
            raise WorkItemNotFoundError(item_id)

        docs = await BusFlowLogDoc.find(
            BusFlowLogDoc.work_item_id == PydanticObjectId(item_id)
        ).sort("-created_at").limit(limit).to_list()
        results = []
        for doc in docs:
            d = doc.model_dump()
            d["id"] = str(doc.id)
            d["work_item_id"] = str(doc.work_item_id)
            results.append(d)
        return results

    async def batch_get_logs(self, item_ids: List[str], limit: int = 20) -> Dict[str, List[Dict]]:
        # 批量查询多个事项的流转历史
        # 返回结构：{ item_id: [log1, log2, ...] }，每个列表内部按时间倒序
        if not item_ids:
            return {}

        # 一次性用 $in 查询所有相关日志，减少数据库往返次数
        object_ids = [PydanticObjectId(item_id) for item_id in item_ids]
        all_logs = await BusFlowLogDoc.find(
            {"work_item_id": {"$in": object_ids}}
        ).sort("-created_at").to_list()

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
        # 同时返回事项详情 + 当前状态下可用的所有流转动作
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
        # 根据「事项类型 + 当前状态 + 动作」查询唯一匹配的流转配置
        doc = await SysWorkflowConfigDoc.find_one(
            SysWorkflowConfigDoc.type_code == type_code,
            SysWorkflowConfigDoc.from_state == from_state,
            SysWorkflowConfigDoc.action == action
        )
        return doc.model_dump() if doc else None

    # ========== 核心流转逻辑 ==========

    async def create_item(self, type_code: str, title: str, content: str, creator_id: int) -> Dict:
        # 创建新的业务事项：
        # - 初始状态为 DRAFT
        # - 当前处理人默认设置为创建人
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
        # 单条事项的状态流转核心流程：
        # 1. 校验事项存在性
        # 2. 根据当前状态 + 动作匹配对应配置
        # 3. 校验必填业务字段
        # 4. 更新状态与处理人
        # 5. 写入流转日志
        logger.info(f"开始处理状态流转: work_item_id={work_item_id}, action={action}, operator={operator_id}")

        item_doc = await BusWorkItemDoc.get(work_item_id)
        if not item_doc or item_doc.is_deleted:
            logger.error(f"流转失败: 未找到业务事项 ID={work_item_id}")
            raise WorkItemNotFoundError(work_item_id)

        config_doc = await SysWorkflowConfigDoc.find_one(
            SysWorkflowConfigDoc.type_code == item_doc.type_code,
            SysWorkflowConfigDoc.from_state == item_doc.current_state,
            SysWorkflowConfigDoc.action == action
        )
        if not config_doc:
            logger.error(f"流转失败: 非法操作。当前状态 {item_doc.current_state} 不支持动作 {action}")
            raise InvalidTransitionError(item_doc.current_state, action)

        required_fields = config_doc.required_fields
        for field in required_fields:
            if field not in form_data:
                logger.error(f"流转失败: 缺少必填字段 {field}")
                raise MissingRequiredFieldError(field)

        process_payload = {field: form_data[field] for field in required_fields}
        if "remark" in form_data and form_data["remark"] is not None:
            process_payload["remark"] = form_data["remark"]

        old_state = item_doc.current_state
        new_state = config_doc.to_state

        # 根据配置中的「处理人策略」计算新的处理人
        new_owner_id = self._apply_owner_strategy(item_doc.model_dump(), config_doc.model_dump(), form_data)

        item_doc.current_state = new_state
        item_doc.current_owner_id = new_owner_id
        await item_doc.save()

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
        # 根据配置中的 target_owner_strategy 字段决定新的处理人：
        # - KEEP：保持当前处理人不变
        # - TO_CREATOR：流转回创建人
        # - TO_SPECIFIC_USER：流转给表单中指定的用户
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
        # 逻辑删除业务事项：
        # - 标记 is_deleted = True
        # - 同时写入一条「DELETE」类型的流转日志
        item_doc = await BusWorkItemDoc.get(item_id)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)

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

    async def reassign_item(self, item_id: str, operator_id: int, target_owner_id: int, remark: Optional[str] = None) -> Dict:
        # 改派当前事项的处理人：
        # - 记录一条「REASSIGN」流转日志
        # - 只改变 current_owner_id，不改变状态
        item_doc = await BusWorkItemDoc.get(item_id)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)

        payload: Dict[str, Any] = {"target_owner_id": target_owner_id}
        if remark is not None:
            payload["remark"] = remark

        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(item_id),
            from_state=item_doc.current_state,
            to_state=item_doc.current_state,
            action="REASSIGN",
            operator_id=operator_id,
            payload=payload
        )
        await log_entry.insert()

        item_doc.current_owner_id = target_owner_id
        await item_doc.save()

        d = item_doc.model_dump()
        d["id"] = str(item_doc.id)
        return d
