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
    """
    工作流核心领域服务（异步）

    职责：
    - 封装所有与「业务事项」及其「状态流转」相关的读写逻辑
    - 直接使用 Beanie 文档模型访问 MongoDB
    - 为 API 路由层提供稳定的服务接口，路由层无需关心持久化细节
    """

    def __init__(self) -> None:
        """
        当前实现中不注入外部依赖。

        如后续需要支持多数据源或可测试性，可以在此处增加依赖注入参数。
        """
        pass

    # ========== 查询方法 ==========

    def _base_item_query(
            self,
            type_code: Optional[str] = None,
            state: Optional[str] = None,
            owner_id: Optional[int] = None,
            creator_id: Optional[int] = None,
    ):
        """
        构建业务事项的基础查询对象。

        特性：
        - 统一过滤逻辑删除的数据（is_deleted == False）
        - 支持按事项类型、当前状态精确过滤
        - 支持将当前处理人 / 创建人条件合并为 OR 查询
        """
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

        return query

    def _docs_to_dicts(self, docs: List[BusWorkItemDoc]) -> List[Dict]:
        """
        将 Beanie 文档列表转换为适合 API 返回的字典列表。

        处理要点：
        - 将 ObjectId 转换为字符串形式的 id
        - 对 parent_item_id 做同样的字符串转换，便于前端直接使用
        """
        results: List[Dict] = []
        for doc in docs:
            d = doc.model_dump()
            d["id"] = str(doc.id)
            if d.get("parent_item_id") is not None:
                d["parent_item_id"] = str(d["parent_item_id"])
            results.append(d)
        return results

    async def get_work_types(self) -> List[Dict]:
        """
        查询所有「事项类型」配置。

        常见用途：
        - 前端下拉列表
        - 配置管理页面
        """
        docs = await SysWorkTypeDoc.find_all().to_list()
        return [doc.model_dump() for doc in docs]

    async def get_workflow_states(self) -> List[Dict]:
        """
        查询所有「流程状态」配置。

        常见用途：
        - 状态枚举展示
        - 看板列定义
        """
        docs = await SysWorkflowStateDoc.find_all().to_list()
        return [doc.model_dump() for doc in docs]

    async def get_workflow_configs(self, type_code: str) -> List[Dict]:
        """
        查询某个事项类型下的全部「状态流转规则」配置。

        用于：
        - 配置页面展示该类型的状态机
        - 调试和排查流转问题
        """
        docs = await SysWorkflowConfigDoc.find(
            SysWorkflowConfigDoc.type_code == type_code
        ).to_list()
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
        """
        列出业务事项列表（按创建时间倒序）。

        支持条件：
        - type_code: 事项类型筛选
        - state: 当前状态筛选
        - owner_id / creator_id: 处理人 OR 创建人筛选（见 _base_item_query）
        - limit + offset: 分页
        """
        query = self._base_item_query(type_code, state, owner_id, creator_id)
        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return self._docs_to_dicts(docs)

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
        """
        列出业务事项列表，并按指定字段排序。

        排序字段限制：
        - 只允许 created_at / updated_at / title
        - direction 为 "desc" 或 "asc"，默认为倒序
        """
        query = self._base_item_query(type_code, state, owner_id, creator_id)

        allowed_fields = {"created_at": "created_at", "updated_at": "updated_at", "title": "title"}
        field = allowed_fields.get(order_by, "created_at")
        prefix = "-" if direction.lower() == "desc" else ""
        sort_expr = f"{prefix}{field}"

        docs = await query.sort(sort_expr).skip(offset).limit(limit).to_list()
        return self._docs_to_dicts(docs)

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
        """
        按关键字搜索业务事项。

        搜索范围：
        - 标题 title 模糊匹配（不区分大小写）
        - 内容 content 模糊匹配（不区分大小写）

        其余过滤条件与分页逻辑复用 _base_item_query 和 list_items。
        """
        query = self._base_item_query(type_code, state, owner_id, creator_id)
        search_conditions = [
            {"title": {"$regex": keyword, "$options": "i"}},
            {"content": {"$regex": keyword, "$options": "i"}},
        ]
        query = query.find({"$or": search_conditions})

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return self._docs_to_dicts(docs)

    async def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """
        根据业务事项 ID 查询详情。

        特性：
        - 会先校验 ObjectId 合法性（非法直接返回 None）
        - 会过滤逻辑删除的数据（is_deleted == True 的记录不会返回）
        - 所有 ObjectId 字段会被转换为字符串
        """
        try:
            if not PydanticObjectId.is_valid(item_id):
                return None
            doc = await BusWorkItemDoc.get(item_id)
            if doc and not doc.is_deleted:
                d = doc.model_dump()
                d["id"] = str(doc.id)
                if d.get("parent_item_id") is not None:
                    d["parent_item_id"] = str(d["parent_item_id"])
                return d
        except Exception as e:
            # 避免非法 ID 或数据库异常直接导致接口 500
            logger.warning(f"获取事项 {item_id} 时发生错误: {e}")
        return None

    async def get_logs(self, item_id: str, limit: int = 50) -> List[Dict]:
        """
        查询单个事项的流转历史（最近若干条，按时间倒序）。

        约束：
        - 会先校验事项是否存在（不存在抛 WorkItemNotFoundError）
        - 日志中的 work_item_id 会被转换为字符串
        """
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
        """
        批量查询多个事项的流转历史。

        返回结构：
            { item_id: [log1, log2, ...] }
        - 每个 item_id 对应的列表内部按时间倒序
        - 单个事项最多返回 limit 条
        - 未找到日志的事项会返回空列表
        """
        if not item_ids:
            return {}

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
        """
        获取事项详情及其当前状态下可用的流转动作列表。

        返回结构：
        {
            "item": 事项详情,
            "available_transitions": [
                { action, to_state, target_owner_strategy, required_fields },
                ...
            ]
        }
        """
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

    async def list_test_cases_for_requirement(self, requirement_id: str) -> List[Dict]:
        """
        查询指定需求下的所有测试用例。

        逻辑：
        1. 先确认 requirement_id 对应的事项存在且类型为 "REQUIREMENT"
        2. 查询所有 type_code == "TEST_CASE" 且 parent_item_id 指向该需求的事项
        3. 过滤掉逻辑删除的数据（is_deleted == False）
        4. 按创建时间倒序返回
        """
        requirement = await self.get_item_by_id(requirement_id)
        if not requirement or requirement.get("type_code") != "REQUIREMENT":
            raise WorkItemNotFoundError(requirement_id)

        docs = await BusWorkItemDoc.find(
            BusWorkItemDoc.is_deleted == False,
            BusWorkItemDoc.type_code == "TEST_CASE",
            BusWorkItemDoc.parent_item_id == PydanticObjectId(requirement_id)
        ).sort("-created_at").to_list()
        return self._docs_to_dicts(docs)

    async def get_requirement_for_test_case(self, test_case_id: str) -> Optional[Dict]:
        """
        反查某个测试用例所属的需求。

        逻辑：
        1. 获取 test_case_id 对应的事项，确认其存在且类型为 "TEST_CASE"
        2. 检查是否存在 parent_item_id（需求 ID）
        3. 若存在，则通过 parent_item_id 查询需求详情；否则返回 None
        """
        doc = await BusWorkItemDoc.get(test_case_id)
        if not doc or doc.is_deleted or doc.type_code != "TEST_CASE":
            return None
        if not doc.parent_item_id:
            return None
        parent_id = str(doc.parent_item_id)
        return await self.get_item_by_id(parent_id)

    # ========== 核心流转逻辑 ==========

    async def create_item(
            self,
            type_code: str,
            title: str,
            content: str,
            creator_id: int,
            parent_item_id: Optional[str] = None
    ) -> Dict:
        """
        创建新的业务事项。

        行为：
        - 初始状态固定为 DRAFT
        - 当前处理人默认设置为创建人
        - 同类型 + 同标题若已存在未删除事项，则拒绝创建
        - 可选挂载到父事项（例如测试用例挂在需求下）
        """
        try:
            existing_item = await BusWorkItemDoc.find_one(
                BusWorkItemDoc.type_code == type_code,
                BusWorkItemDoc.title == title,
                BusWorkItemDoc.is_deleted == False
            )
            if existing_item:
                raise ValueError(f"已存在相同标题的{type_code}: {title}")

            parent_oid = None
            if parent_item_id:
                if PydanticObjectId.is_valid(parent_item_id):
                    parent_oid = PydanticObjectId(parent_item_id)
                else:
                    logger.warning(f"无效的父事项 ID: {parent_item_id}，将忽略 parent_item_id")
            new_item = BusWorkItemDoc(
                type_code=type_code,
                title=title,
                content=content,
                parent_item_id=parent_oid,
                creator_id=creator_id,
                current_owner_id=creator_id,
                current_state=WorkItemState.DRAFT.value
            )
            await new_item.insert()
            logger.success(f"业务事项创建成功: ID={new_item.id}, state={new_item.current_state}")
            d = new_item.model_dump()
            d["id"] = str(new_item.id)
            if d.get("parent_item_id") is not None:
                d["parent_item_id"] = str(d["parent_item_id"])
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
        """
        对单条事项执行状态流转。

        流程：
        1. 校验事项存在性（逻辑未删除）
        2. 根据当前状态 + 动作查找匹配的工作流配置
        3. 校验配置中声明的必填业务字段是否在 form_data 中存在
        4. 根据配置中的处理人策略计算新的处理人
        5. 更新事项状态与处理人
        6. 写入一条流转日志（包含业务表单 payload）
        """
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
        if item_dict.get("parent_item_id") is not None:
            item_dict["parent_item_id"] = str(item_dict["parent_item_id"])

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
        """
        根据配置中的 target_owner_strategy 字段计算新的处理人。

        策略说明：
        - KEEP：保持当前处理人不变
        - TO_CREATOR：设置为创建人
        - TO_SPECIFIC_USER：设置为表单中传入的 target_owner_id
        """
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
        """
        逻辑删除业务事项。

        行为：
        - 将 is_deleted 标记为 True
        - 写入一条 action 为 "DELETE" 的流转日志，状态不变
        """
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
        """
        改派当前事项的处理人（不改变状态）。

        行为：
        - 写入一条 action 为 "REASSIGN" 的流转日志
        - 仅更新 current_owner_id，保持状态不变
        """
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
        if d.get("parent_item_id") is not None:
            d["parent_item_id"] = str(d["parent_item_id"])
        return d
