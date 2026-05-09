"""DUT 测试机服务层"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.modules.assets.repository.models import DutCreateModel, DutDoc
from app.modules.assets.schemas.dut import (
    SyncTmmsRequest,
    SyncTmmsResponse,
)


class DutNotFoundError(Exception):
    """DUT 未找到异常"""

    pass


class DutAlreadyExistsError(Exception):
    """DUT 已存在异常"""

    pass


class DutService:
    """DUT 测试机服务"""

    @staticmethod
    def _doc_to_dict(doc: DutDoc) -> Dict[str, Any]:
        """将文档转换为字典"""
        data = doc.model_dump()
        data["id"] = str(doc.id)
        return data

    @staticmethod
    def _generate_dut_id() -> str:
        """生成 DUT 业务编号"""
        import uuid

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        short_id = str(uuid.uuid4())[:8]
        return f"DUT-{timestamp}-{short_id}"

    async def create_dut(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建 DUT"""
        # 生成或使用提供的 dut_id
        dut_id = data.get("dut_id") or self._generate_dut_id()

        # 检查是否已存在
        existing = await DutDoc.find_one(DutDoc.dut_id == dut_id)
        if existing:
            raise DutAlreadyExistsError(f"DUT with id '{dut_id}' already exists")

        # 创建文档
        doc = DutDoc(
            dut_id=dut_id,
            name=data["name"],
            status=data.get("status", "AVAILABLE"),
            region=data.get("region", "default"),
            description=data.get("description"),
            tags=data.get("tags", []),
            bmc_ip=data["bmc_ip"],
            bmc_username=data.get("bmc_username", "admin"),
            bmc_password=data["bmc_password"],
            os_ip=data["os_ip"],
            os_username=data.get("os_username", "root"),
            os_password=data["os_password"],
            os_type=data.get("os_type", "Linux"),
            metadata=data.get("metadata", {}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await doc.insert()

        return self._doc_to_dict(doc)

    async def list_duts(
        self,
        status: Optional[str] = None,
        region: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """查询 DUT 列表"""
        query = {}
        if status:
            query["status"] = status
        if region:
            query["region"] = region
        if search:
            # 支持名称、BMC IP、OS IP 搜索
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"bmc_ip": {"$regex": search, "$options": "i"}},
                {"os_ip": {"$regex": search, "$options": "i"}},
            ]

        total = await DutDoc.find(query).count()
        docs = await DutDoc.find(query).skip(offset).limit(limit).to_list()

        return [self._doc_to_dict(doc) for doc in docs], total

    async def get_dut(self, dut_id: str) -> Dict[str, Any]:
        """获取 DUT 详情"""
        doc = await DutDoc.find_one(DutDoc.dut_id == dut_id)
        if not doc:
            raise DutNotFoundError(f"DUT with id '{dut_id}' not found")
        return self._doc_to_dict(doc)

    async def update_dut(self, dut_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新 DUT"""
        doc = await DutDoc.find_one(DutDoc.dut_id == dut_id)
        if not doc:
            raise DutNotFoundError(f"DUT with id '{dut_id}' not found")

        # 只更新提供的字段
        update_data = {k: v for k, v in data.items() if v is not None}
        if not update_data:
            raise ValueError("no fields to update")

        update_data["updated_at"] = datetime.utcnow()

        await doc.update({"$set": update_data})
        await doc.reload()

        return self._doc_to_dict(doc)

    async def delete_dut(self, dut_id: str) -> bool:
        """删除 DUT"""
        doc = await DutDoc.find_one(DutDoc.dut_id == dut_id)
        if not doc:
            raise DutNotFoundError(f"DUT with id '{dut_id}' not found")

        await doc.delete()
        return True

    async def get_dut_regions(self) -> List[str]:
        """获取所有区域列表"""
        pipeline = [
            {"$group": {"_id": "$region"}},
            {"$sort": {"_id": 1}},
        ]
        results = await DutDoc.aggregate(pipeline).to_list()
        return [r["_id"] for r in results if r["_id"]]

    async def sync_from_tmms(self, request: SyncTmmsRequest) -> SyncTmmsResponse:
        """从 TMMS 同步 DUT（预留接口）"""
        # TODO: 实现 TMMS API 集成
        return SyncTmmsResponse(
            success=False,
            message="TMMS 同步功能预留中，暂未实现",
            synced_count=0,
            error_count=0,
        )