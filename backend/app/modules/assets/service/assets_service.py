"""硬件与资产管理服务"""
from typing import List, Dict, Any, Optional
from app.modules.assets.repository.models import (
    ComponentLibraryDoc,
    DutDoc,
    TestPlanComponentDoc,
)


class AssetsService:
    """资产管理核心服务（异步）"""

    # ========== Component Library ==========

    async def create_component(self, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await ComponentLibraryDoc.find_one(
            ComponentLibraryDoc.part_number == data["part_number"]
        )
        if existing:
            raise ValueError("part_number already exists")
        doc = ComponentLibraryDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_component(self, part_number: str) -> Dict[str, Any]:
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
        doc = await ComponentLibraryDoc.find_one(
            ComponentLibraryDoc.part_number == part_number
        )
        if not doc:
            raise KeyError("component not found")
        for key, value in data.items():
            setattr(doc, key, value)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_component(self, part_number: str) -> None:
        doc = await ComponentLibraryDoc.find_one(
            ComponentLibraryDoc.part_number == part_number
        )
        if not doc:
            raise KeyError("component not found")
        await doc.delete()

    # ========== DUT ==========

    async def create_dut(self, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = await DutDoc.find_one(DutDoc.asset_id == data["asset_id"])
        if existing:
            raise ValueError("asset_id already exists")
        doc = DutDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_dut(self, asset_id: str) -> Dict[str, Any]:
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
        doc = await DutDoc.find_one(DutDoc.asset_id == asset_id)
        if not doc:
            raise KeyError("dut not found")
        for key, value in data.items():
            setattr(doc, key, value)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_dut(self, asset_id: str) -> None:
        doc = await DutDoc.find_one(DutDoc.asset_id == asset_id)
        if not doc:
            raise KeyError("dut not found")
        await doc.delete()

    # ========== Test Plan Component ==========

    async def create_plan_component(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
        query = TestPlanComponentDoc.find()
        if plan_id:
            query = query.find(TestPlanComponentDoc.plan_id == plan_id)
        if part_number:
            query = query.find(TestPlanComponentDoc.part_number == part_number)

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def delete_plan_component(self, plan_id: str, part_number: str) -> None:
        doc = await TestPlanComponentDoc.find_one(
            TestPlanComponentDoc.plan_id == plan_id,
            TestPlanComponentDoc.part_number == part_number,
        )
        if not doc:
            raise KeyError("plan component not found")
        await doc.delete()

    # ========== Helpers ==========

    @staticmethod
    def _doc_to_dict(doc) -> Dict[str, Any]:
        data = doc.model_dump()
        data["id"] = str(doc.id)
        return data
