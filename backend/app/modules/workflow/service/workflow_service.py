import re
from typing import Dict, Any, Optional, List
from beanie import PydanticObjectId
from pymongo import AsyncMongoClient
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.modules.workflow.repository.models import (
    SysWorkflowConfigDoc,
    BusWorkItemDoc,
    BusFlowLogDoc,
    SysWorkTypeDoc,
    SysWorkflowStateDoc,
    WorkItemState,
)
from app.modules.test_specs.repository.models import TestRequirementDoc, TestCaseDoc
from app.modules.workflow.domain.exceptions import (
    WorkItemNotFoundError,
    InvalidTransitionError,
    PermissionDeniedError,
)
from app.modules.workflow.domain.rules import (
    ensure_required_fields,
    build_process_payload,
    resolve_owner,
    normalize_sort,
)
from app.modules.workflow.domain.policies import (
    can_delete_work_item,
    can_reassign,
    can_transition,
)
from app.shared.core.logger import log as logger
from app.shared.core.mongo_client import get_mongo_client


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

    @staticmethod
    def _get_mongo_client_or_none() -> Optional[AsyncMongoClient]:
        try:
            return get_mongo_client()
        except RuntimeError:
            return None

    @staticmethod
    def _is_transaction_not_supported(exc: Exception) -> bool:
        message = str(exc).lower()
        return (
                "transaction numbers are only allowed on a replica set member" in message
                or "this mongodb deployment does not support retryable writes" in message
                or "sessions are not supported" in message
        )

    # ========== 查询方法 ==========

    def _base_item_query(
            self,
            type_code: Optional[str] = None,
            state: Optional[str] = None,
            owner_id: Optional[str] = None,
            creator_id: Optional[str] = None,
    ):
        """
        构建业务事项的基础查询对象。

        特性：
        - 统一过滤逻辑删除的数据（is_deleted=False）
        - 支持按事项类型、当前状态精确过滤
        - 支持将当前处理人 / 创建人条件合并为 OR 查询
        """
        query = BusWorkItemDoc.find({"is_deleted": False})

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
        - 将 ObjectId 转换为字符串形式的 item_id（与前端保持一致）
        - 对 parent_item_id 做同样的字符串转换，便于前端直接使用
        """
        results: List[Dict] = []
        for doc in docs:
            d = doc.model_dump()
            d["item_id"] = str(doc.id)  # 修改字段名为 item_id
            if d.get("parent_item_id") is not None:
                d["parent_item_id"] = str(d["parent_item_id"])
            results.append(d)
        return results

    @staticmethod
    def _serialize_work_item(doc: BusWorkItemDoc) -> Dict[str, Any]:
        data = doc.model_dump()
        data["id"] = str(doc.id)
        data["item_id"] = str(doc.id)
        if data.get("parent_item_id") is not None:
            data["parent_item_id"] = str(data["parent_item_id"])
        return data

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
        results: List[Dict[str, Any]] = []
        for doc in docs:
            data = doc.model_dump()
            data["id"] = str(doc.id)
            results.append(data)
        return results

    async def list_items(
            self,
            type_code: Optional[str] = None,
            state: Optional[str] = None,
            owner_id: Optional[str] = None,
            creator_id: Optional[str] = None,
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
            owner_id: Optional[str] = None,
            creator_id: Optional[str] = None,
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

        sort_expr = normalize_sort(order_by, direction)

        docs = await query.sort(sort_expr).skip(offset).limit(limit).to_list()
        return self._docs_to_dicts(docs)

    async def search_items(
            self,
            keyword: str,
            type_code: Optional[str] = None,
            state: Optional[str] = None,
            owner_id: Optional[str] = None,
            creator_id: Optional[str] = None,
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
        normalized_keyword = keyword.strip()
        if len(normalized_keyword) < 2:
            raise ValueError("keyword length must be at least 2")

        query = self._base_item_query(type_code, state, owner_id, creator_id).find(
            {"$text": {"$search": normalized_keyword}}
        )

        try:
            docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        except OperationFailure as exc:
            # Backward compatible fallback when text index has not been created yet.
            if "text index required" not in str(exc).lower():
                raise
            escaped_keyword = re.escape(normalized_keyword)
            search_conditions = [
                {"title": {"$regex": escaped_keyword, "$options": "i"}},
                {"content": {"$regex": escaped_keyword, "$options": "i"}},
            ]
            fallback_query = self._base_item_query(type_code, state, owner_id, creator_id).find(
                {"$or": search_conditions}
            )
            docs = await fallback_query.sort("-created_at").skip(offset).limit(limit).to_list()
        return self._docs_to_dicts(docs)

    async def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """
        根据业务事项 ID 查询详情。

        特性：
        - 会先校验 ObjectId 合法性（非法直接返回 None）
        - 会过滤逻辑删除的数据（is_deleted=True 的记录不会返回）
        - 所有 ObjectId 字段会被转换为字符串
        """
        try:
            if not PydanticObjectId.is_valid(item_id):
                return None
            doc = await BusWorkItemDoc.get(item_id)
            if doc and not doc.is_deleted:
                return self._serialize_work_item(doc)
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

        invalid_item_ids: List[str] = []
        object_ids: List[PydanticObjectId] = []
        for item_id in item_ids:
            if not PydanticObjectId.is_valid(item_id):
                invalid_item_ids.append(item_id)
                continue
            object_ids.append(PydanticObjectId(item_id))

        if invalid_item_ids:
            raise ValueError(f"invalid item_ids: {invalid_item_ids}")

        if not object_ids:
            return {item_id: [] for item_id in item_ids}

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
        3. 过滤掉逻辑删除的数据（is_deleted=False）
        4. 按创建时间倒序返回
        """
        requirement = await self.get_item_by_id(requirement_id)
        if not requirement or requirement.get("type_code") != "REQUIREMENT":
            raise WorkItemNotFoundError(requirement_id)

        docs = await BusWorkItemDoc.find(
            {"is_deleted": False},
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
            creator_id: str,
            parent_item_id: Optional[str] = None,
            session: Optional[AsyncClientSession] = None,
    ) -> Dict:
        """
        创建新的业务事项。

        行为：
        - 初始状态固定为 DRAFT
        - 当前处理人默认设置为创建人
        - 同类型 + 同标题若已存在未删除事项，则拒绝创建
        - 可选挂载到父事项（例如测试用例挂在需求下）
        - 支持通过 session 参与上层事务
        """
        try:
            existing_item = await BusWorkItemDoc.find_one(
                {
                    "type_code": type_code,
                    "title": title,
                    "is_deleted": False,
                },
                session=session,
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
            await new_item.insert(session=session)
            logger.success(f"业务事项创建成功: ID={new_item.id}, state={new_item.current_state}")
            return self._serialize_work_item(new_item)
        except DuplicateKeyError as e:
            logger.warning(f"业务事项并发创建冲突(type_code={type_code}, title={title}): {e}")
            raise ValueError(f"已存在相同标题的{type_code}: {title}")
        except Exception as e:
            logger.error(f"创建业务事项失败: {e}")
            raise

    async def handle_transition(
            self,
            work_item_id: str,
            action: str,
            operator_id: str,
            form_data: Dict[str, Any],
            actor_role_ids: Optional[List[str]] = None,
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

        client = self._get_mongo_client_or_none()
        if client is None:
            logger.error("MongoDB 客户端未初始化，无法执行原子状态流转")
            raise RuntimeError("workflow transition requires initialized MongoDB client")

        try:
            async with client.start_session() as session:
                async with await session.start_transaction():
                    return await self._handle_transition_core(
                        work_item_id=work_item_id,
                        action=action,
                        operator_id=operator_id,
                        form_data=form_data,
                        actor_role_ids=actor_role_ids,
                        session=session,
                    )
        except Exception as exc:
            if self._is_transaction_not_supported(exc):
                logger.error("MongoDB 部署不支持事务，已拒绝执行非原子状态流转")
                raise RuntimeError("workflow transition requires MongoDB transaction support") from exc
            raise

    async def _handle_transition_core(
            self,
            work_item_id: str,
            action: str,
            operator_id: str,
            form_data: Dict[str, Any],
            actor_role_ids: Optional[List[str]],
            session: Optional[AsyncClientSession],
    ) -> Dict[str, Any]:
        item_doc = await self._get_work_item(work_item_id, session=session)
        if not item_doc or item_doc.is_deleted:
            logger.error(f"流转失败: 未找到业务事项 ID={work_item_id}")
            raise WorkItemNotFoundError(work_item_id)

        config_doc = await SysWorkflowConfigDoc.find_one(
            {
                "type_code": item_doc.type_code,
                "from_state": item_doc.current_state,
                "action": action,
            },
            session=session,
        )
        if not config_doc:
            logger.error(f"流转失败: 非法操作。当前状态 {item_doc.current_state} 不支持动作 {action}")
            raise InvalidTransitionError(item_doc.current_state, action)
        actor = {"actor_id": operator_id, "role_ids": actor_role_ids or []}
        if not can_transition(actor, item_doc, config_doc):
            raise PermissionDeniedError(operator_id, "transition")

        required_fields = config_doc.required_fields
        ensure_required_fields(required_fields, form_data)
        process_payload = build_process_payload(required_fields, form_data)

        old_state = item_doc.current_state
        new_state = config_doc.to_state
        new_owner_id = resolve_owner(
            strategy=config_doc.target_owner_strategy,
            work_item=item_doc.model_dump(),
            form_data=form_data,
        )

        item_doc.current_state = new_state
        item_doc.current_owner_id = new_owner_id
        await self._save_doc(item_doc, session=session)

        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(work_item_id),
            from_state=old_state,
            to_state=new_state,
            action=action,
            operator_id=operator_id,
            payload=process_payload,
        )
        await self._insert_doc(log_entry, session=session)

        if item_doc.type_code == "REQUIREMENT":
            requirement = await TestRequirementDoc.find_one(
                {
                    "workflow_item_id": str(item_doc.id),
                    "is_deleted": False,
                },
                session=session,
            )
            if requirement:
                requirement.status = new_state
                await self._save_doc(requirement, session=session)
        elif item_doc.type_code == "TEST_CASE":
            test_case = await TestCaseDoc.find_one(
                {
                    "workflow_item_id": str(item_doc.id),
                    "is_deleted": False,
                },
                session=session,
            )
            if test_case:
                test_case.status = new_state
                await self._save_doc(test_case, session=session)

        logger.success(f"状态流转完成: ID={work_item_id}, new_state={new_state}")

        item_dict = self._serialize_work_item(item_doc)

        return {
            "work_item_id": str(item_doc.id),
            "from_state": old_state,
            "to_state": new_state,
            "action": action,
            "new_owner_id": new_owner_id,
            "work_item": item_dict,
        }

    @staticmethod
    async def _get_work_item(
            work_item_id: str,
            session: Optional[AsyncClientSession],
    ):
        if session is None:
            return await BusWorkItemDoc.get(work_item_id)
        try:
            return await BusWorkItemDoc.get(work_item_id, session=session)
        except TypeError:
            return await BusWorkItemDoc.get(work_item_id)

    @staticmethod
    async def _save_doc(doc, session: Optional[AsyncClientSession]) -> None:
        if session is None:
            await doc.save()
            return
        try:
            await doc.save(session=session)
        except TypeError:
            await doc.save()

    @staticmethod
    async def _insert_doc(doc, session: Optional[AsyncClientSession]) -> None:
        if session is None:
            await doc.insert()
            return
        try:
            await doc.insert(session=session)
        except TypeError:
            await doc.insert()

    async def delete_item(
            self,
            item_id: str,
            operator_id: str,
            actor_role_ids: Optional[List[str]] = None,
    ) -> bool:
        """
        逻辑删除业务事项。

        行为：
        - 将 is_deleted 标记为 True
        - 写入一条 action 为 "DELETE" 的流转日志，状态不变
        """
        client = self._get_mongo_client_or_none()
        if client is None:
            logger.error("MongoDB 客户端未初始化，无法执行原子删除")
            raise RuntimeError("workflow delete requires initialized MongoDB client")

        try:
            async with client.start_session() as session:
                async with await session.start_transaction():
                    return await self._delete_item_core(
                        item_id=item_id,
                        operator_id=operator_id,
                        actor_role_ids=actor_role_ids,
                        session=session,
                    )
        except Exception as exc:
            if self._is_transaction_not_supported(exc):
                logger.error("MongoDB 部署不支持事务，已拒绝执行非原子删除")
                raise RuntimeError("workflow delete requires MongoDB transaction support") from exc
            raise

    async def _delete_item_core(
            self,
            item_id: str,
            operator_id: str,
            actor_role_ids: Optional[List[str]],
            session: Optional[AsyncClientSession],
    ) -> bool:
        item_doc = await self._get_work_item(item_id, session=session)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)
        actor = {"actor_id": operator_id, "role_ids": actor_role_ids or []}
        if not can_delete_work_item(actor, item_doc):
            raise PermissionDeniedError(operator_id, "delete")

        if item_doc.type_code == "REQUIREMENT":
            requirement = await TestRequirementDoc.find_one(
                {
                    "workflow_item_id": str(item_doc.id),
                    "is_deleted": False,
                },
                session=session,
            )
            if requirement is None:
                raise ValueError("linked requirement not found")

            related_cases = await TestCaseDoc.find(
                TestCaseDoc.ref_req_id == requirement.req_id,
                {"is_deleted": False},
                session=session,
            ).count()
            if related_cases > 0:
                raise ValueError("requirement has related test cases")

            requirement.is_deleted = True
            await self._save_doc(requirement, session=session)
        elif item_doc.type_code == "TEST_CASE":
            test_case = await TestCaseDoc.find_one(
                {
                    "workflow_item_id": str(item_doc.id),
                    "is_deleted": False,
                },
                session=session,
            )
            if test_case is None:
                raise ValueError("linked test case not found")
            test_case.is_deleted = True
            await self._save_doc(test_case, session=session)

        log_entry = BusFlowLogDoc(
            work_item_id=PydanticObjectId(item_id),
            from_state=item_doc.current_state,
            to_state=item_doc.current_state,
            action="DELETE",
            operator_id=operator_id,
            payload={"info": "Soft deleted"},
        )
        await self._insert_doc(log_entry, session=session)

        item_doc.is_deleted = True
        await self._save_doc(item_doc, session=session)
        logger.success(f"事项 ID={item_id} 已逻辑删除")
        return True

    async def reassign_item(
            self,
            item_id: str,
            operator_id: str,
            target_owner_id: str,
            remark: Optional[str] = None,
            actor_role_ids: Optional[List[str]] = None,
    ) -> Dict:
        """
        改派当前事项的处理人（不改变状态）。

        行为：
        - 写入一条 action 为 "REASSIGN" 的流转日志
        - 仅更新 current_owner_id，保持状态不变
        """
        item_doc = await BusWorkItemDoc.get(item_id)
        if not item_doc or item_doc.is_deleted:
            raise WorkItemNotFoundError(item_id)
        actor = {"actor_id": operator_id, "role_ids": actor_role_ids or []}
        if not can_reassign(actor, item_doc):
            raise PermissionDeniedError(operator_id, "reassign")

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

        return self._serialize_work_item(item_doc)
