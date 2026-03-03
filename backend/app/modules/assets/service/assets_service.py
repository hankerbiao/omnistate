"""硬件与资产管理服务

AI 友好注释说明：
- Service 层负责业务规则与数据库访问的编排。
- 本服务包含三个子域：部件字典、DUT 资产、测试计划关联部件。
- 这里不处理鉴权，仅实现 CRUD 与基础校验。
"""
from typing import List, Dict, Any, Optional
from app.modules.assets.repository.models import (
    ComponentLibraryDoc,
    DutDoc,
    TestPlanComponentDoc,
)
from app.shared.service import BaseService


class AssetsService(BaseService):
    """资产管理核心服务（异步）"""

    # 允许更新的字段白名单，避免主键或无效字段被写入
    _COMPONENT_UPDATABLE_FIELDS = {
        "category",
        "subcategory",
        "vendor",
        "model",
        "revision",
        "form_factor",
        "interface_type",
        "interface_gen",
        "protocol",
        "attributes",
        "power_watt",
        "firmware_baseline",
        "spec",
        "datasheet_url",
        "lifecycle_status",
        "aliases",
    }
    _DUT_UPDATABLE_FIELDS = {
        "model",
        "status",
        "owner_team",
        "rack_location",
        "bmc_ip",
        "bmc_port",
        "os_ip",
        "os_port",
        "login_username",
        "login_password",
        "health_status",
        "notes",
    }

    # ========== Component Library ==========

    async def create_component(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建部件字典项

        流程：
        1. 校验 part_number 是否已存在
        2. 插入文档
        3. 返回标准化字典
        """
        existing = await ComponentLibraryDoc.find_one(
            ComponentLibraryDoc.part_number == data["part_number"]
        )
        if existing:
            raise ValueError("part_number already exists")
        doc = ComponentLibraryDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_component(self, part_number: str) -> Dict[str, Any]:
        """获取单个部件信息"""
        doc = await ComponentLibraryDoc.find_one(
            ComponentLibraryDoc.part_number == part_number
        )
        if not doc:
            raise KeyError("component not found")
        return self._doc_to_dict(doc)

    async def list_components(
        self,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        vendor: Optional[str] = None,
        model: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """分页查询部件列表，支持按类别/厂商等过滤"""
        query = ComponentLibraryDoc.find()
        if category:
            query = query.find(ComponentLibraryDoc.category == category)
        if subcategory:
            query = query.find(ComponentLibraryDoc.subcategory == subcategory)
        if vendor:
            query = query.find(ComponentLibraryDoc.vendor == vendor)
        if model:
            query = query.find(ComponentLibraryDoc.model == model)
        if lifecycle_status:
            query = query.find(ComponentLibraryDoc.lifecycle_status == lifecycle_status)

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_component(self, part_number: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新部件信息（白名单字段）"""
        doc = await ComponentLibraryDoc.find_one(
            ComponentLibraryDoc.part_number == part_number
        )
        if not doc:
            raise KeyError("component not found")
        self._apply_updates(doc, data, self._COMPONENT_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_component(self, part_number: str) -> None:
        """删除部件（物理删除）"""
        doc = await ComponentLibraryDoc.find_one(
            ComponentLibraryDoc.part_number == part_number
        )
        if not doc:
            raise KeyError("component not found")
        await doc.delete()

    # ========== DUT ==========

    async def create_dut(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建 DUT 资产"""
        existing = await DutDoc.find_one(DutDoc.asset_id == data["asset_id"])
        if existing:
            raise ValueError("asset_id already exists")
        doc = DutDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_dut(self, asset_id: str) -> Dict[str, Any]:
        """获取 DUT 资产详情"""
        doc = await DutDoc.find_one(DutDoc.asset_id == asset_id)
        if not doc:
            raise KeyError("dut not found")
        return self._doc_to_dict(doc)

    async def list_duts(
        self,
        status: Optional[str] = None,
        owner_team: Optional[str] = None,
        rack_location: Optional[str] = None,
        health_status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """分页查询 DUT 列表，支持状态/归属等过滤"""
        query = DutDoc.find()
        if status:
            query = query.find(DutDoc.status == status)
        if owner_team:
            query = query.find(DutDoc.owner_team == owner_team)
        if rack_location:
            query = query.find(DutDoc.rack_location == rack_location)
        if health_status:
            query = query.find(DutDoc.health_status == health_status)

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def update_dut(self, asset_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新 DUT 资产信息（白名单字段）"""
        doc = await DutDoc.find_one(DutDoc.asset_id == asset_id)
        if not doc:
            raise KeyError("dut not found")
        self._apply_updates(doc, data, self._DUT_UPDATABLE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_dut(self, asset_id: str) -> None:
        """删除 DUT（物理删除）"""
        doc = await DutDoc.find_one(DutDoc.asset_id == asset_id)
        if not doc:
            raise KeyError("dut not found")
        await doc.delete()

    # ========== Test Plan Component ==========

    async def create_plan_component(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建测试计划与部件的关联记录"""
        existing = await TestPlanComponentDoc.find_one(
            TestPlanComponentDoc.plan_id == data["plan_id"],
            TestPlanComponentDoc.part_number == data["part_number"],
        )
        if existing:
            raise ValueError("plan component already exists")
        doc = TestPlanComponentDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def list_plan_components(
        self,
        plan_id: Optional[str] = None,
        part_number: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """查询测试计划关联部件列表"""
        query = TestPlanComponentDoc.find()
        if plan_id:
            query = query.find(TestPlanComponentDoc.plan_id == plan_id)
        if part_number:
            query = query.find(TestPlanComponentDoc.part_number == part_number)

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def delete_plan_component(self, plan_id: str, part_number: str) -> None:
        """删除测试计划关联部件"""
        doc = await TestPlanComponentDoc.find_one(
            TestPlanComponentDoc.plan_id == plan_id,
            TestPlanComponentDoc.part_number == part_number,
        )
        if not doc:
            raise KeyError("plan component not found")
        await doc.delete()
