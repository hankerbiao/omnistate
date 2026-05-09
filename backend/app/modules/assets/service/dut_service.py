"""DUT 测试机服务层"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.modules.assets.infrastructure.tmms_client import TMMSClient, TMMSSyncError
from app.modules.assets.repository.models import DutCreateModel, DutDoc
from app.modules.assets.schemas.dut import (
    ImportExternalMachineItem,
    ImportExternalMachinesResponse,
    SyncTmmsRequest,
    SyncTmmsResponse,
)

logger = logging.getLogger(__name__)


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
        """从 TMMS 同步 DUT（全量拉取 + 差异比对）。

        流程：
        1. 调用 TMMS API 获取全量机器列表
        2. 遍历远程机器，按 source_id 匹配本地记录进行创建或更新
        3. 如果 prune_stale=True，标记本地有但远程无的 tmms 记录为 RETIRED
        """
        client = TMMSClient()
        response = SyncTmmsResponse(
            success=False,
            message="",
            synced_count=0,
            created_count=0,
            updated_count=0,
            skipped_count=0,
            error_count=0,
            errors=[],
        )

        # 1. 拉取 TMMS 机器列表
        try:
            remote_machines = await client.fetch_machines(regions=request.regions)
        except TMMSSyncError as exc:
            response.message = f"TMMS API 请求失败: {exc}"
            response.error_count = 1
            response.errors.append({"machine_id": "", "reason": str(exc)})
            logger.error("TMMS sync failed: %s", exc)
            return response

        if not remote_machines:
            response.success = True
            response.message = "TMMS 返回空机器列表，无需同步"
            return response

        remote_ids = set()
        conflict_strategy = request.conflict_strategy

        # 2. 遍历远程机器
        for machine in remote_machines:
            remote_id = machine.get("id") or machine.get("machine_id") or ""
            remote_ids.add(remote_id)

            try:
                local = await DutDoc.find_one({
                    "source": "tmms",
                    "source_id": remote_id,
                })

                if local is None:
                    await self._create_from_tmms(machine, remote_id)
                    response.created_count += 1
                else:
                    if conflict_strategy == "skip":
                        response.skipped_count += 1
                        continue
                    await self._update_from_tmms(local, machine, conflict_strategy)
                    response.updated_count += 1

                response.synced_count += 1

            except Exception as exc:
                response.error_count += 1
                response.errors.append({
                    "machine_id": remote_id,
                    "reason": str(exc),
                })
                logger.error("Failed to sync machine %s: %s", remote_id, exc)

        # 3. 清理不在远程列表中的本地记录
        if request.prune_stale and remote_ids:
            stale_docs = await DutDoc.find({
                "source": "tmms",
                "source_id": {"$nin": list(remote_ids)},
                "status": {"$ne": "RETIRED"},
            }).to_list()
            for doc in stale_docs:
                doc.status = "RETIRED"
                doc.updated_at = datetime.utcnow()
                await doc.save()
                logger.info("Marked stale DUT %s as RETIRED", doc.dut_id)

        response.success = True
        response.message = (
            f"同步完成: 新建 {response.created_count}, "
            f"更新 {response.updated_count}, "
            f"跳过 {response.skipped_count}"
            + (f", 失败 {response.error_count}" if response.error_count else "")
        )
        return response

    async def _create_from_tmms(self, machine: Dict[str, Any], remote_id: str) -> None:
        """根据 TMMS 数据创建本地 DUT 记录。"""
        now = datetime.utcnow()
        dut_id = self._generate_dut_id()
        doc = DutDoc(
            dut_id=dut_id,
            name=machine.get("name", remote_id),
            status=machine.get("status", "AVAILABLE"),
            region=machine.get("region", "default"),
            description=machine.get("description"),
            tags=machine.get("tags", []),
            bmc_ip=machine.get("bmc_ip", ""),
            bmc_username=machine.get("bmc_username", "admin"),
            bmc_password=machine.get("bmc_password", machine.get("password", "")),
            os_ip=machine.get("os_ip", ""),
            os_username=machine.get("os_username", "root"),
            os_password=machine.get("os_password", machine.get("password", "")),
            os_type=machine.get("os_type", "Linux"),
            metadata=machine.get("metadata", {}),
            source="tmms",
            source_id=remote_id,
            last_synced_at=now,
            created_at=now,
            updated_at=now,
        )
        await doc.insert()

    async def _update_from_tmms(
        self,
        doc: DutDoc,
        machine: Dict[str, Any],
        strategy: str,
    ) -> None:
        """根据 TMMS 数据更新本地 DUT 记录。"""
        now = datetime.utcnow()
        # overwrite: 远程覆盖全部字段
        # merge: 只更新非敏感字段
        doc.name = machine.get("name", doc.name)
        doc.status = machine.get("status", doc.status)
        doc.region = machine.get("region", doc.region)
        doc.description = machine.get("description", doc.description)
        doc.tags = machine.get("tags", doc.tags)
        doc.bmc_ip = machine.get("bmc_ip", doc.bmc_ip)
        doc.bmc_username = machine.get("bmc_username", doc.bmc_username)
        doc.os_ip = machine.get("os_ip", doc.os_ip)
        doc.os_username = machine.get("os_username", doc.os_username)

        if strategy == "overwrite":
            doc.bmc_password = machine.get("bmc_password", doc.bmc_password)
            doc.os_password = machine.get("os_password", doc.os_password)

        doc.os_type = machine.get("os_type", doc.os_type)
        doc.metadata = machine.get("metadata", doc.metadata)
        doc.last_synced_at = now
        doc.updated_at = now
        await doc.save()

    async def import_external_machines(
        self,
        external_items: List[ImportExternalMachineItem],
        created_by: str = "system",
    ) -> ImportExternalMachinesResponse:
        """批量导入外部系统机器到 DUT 列表。"""
        response = ImportExternalMachinesResponse(
            success=True,
            message="",
            total=len(external_items),
            created_count=0,
            skipped_count=0,
            error_count=0,
            results=[],
        )

        for item in external_items:
            try:
                # 检查是否已存在（按 external_id 检查）
                existing = await DutDoc.find_one({"source_id": item.external_id, "source": "external"})
                if existing:
                    response.skipped_count += 1
                    response.results.append({
                        "external_id": item.external_id,
                        "name": item.name,
                        "status": "skipped",
                        "reason": "已存在",
                    })
                    continue

                # 构建 metadata
                metadata = dict(item.metadata) if item.metadata else {}
                metadata.update({
                    "_external_source": "external",
                    "_original_name": item.name,
                    "_model": getattr(item, "model", None),
                    "_cpu": getattr(item, "cpu", None),
                    "_memory": getattr(item, "memory", None),
                    "_storage": getattr(item, "storage", None),
                    "_owner": getattr(item, "owner", None),
                })

                now = datetime.utcnow()
                dut_id = self._generate_dut_id()
                doc = DutDoc(
                    dut_id=dut_id,
                    name=item.name,
                    status="AVAILABLE",
                    region=item.region,
                    description=f"从外部系统 {item.external_id} 导入",
                    tags=item.tags,
                    bmc_ip=item.bmc_ip,
                    bmc_username="admin",
                    bmc_password=item.bmc_password,
                    os_ip=item.os_ip,
                    os_username="root",
                    os_password=item.os_password,
                    os_type=item.os_type.value if hasattr(item.os_type, "value") else item.os_type,
                    metadata=metadata,
                    source="external",
                    source_id=item.external_id,
                    last_synced_at=now,
                    created_at=now,
                    updated_at=now,
                    created_by=created_by,
                )
                await doc.insert()

                response.created_count += 1
                response.results.append({
                    "external_id": item.external_id,
                    "name": item.name,
                    "dut_id": dut_id,
                    "status": "created",
                })

            except Exception as exc:
                response.error_count += 1
                response.results.append({
                    "external_id": item.external_id,
                    "name": item.name,
                    "status": "error",
                    "reason": str(exc),
                })
                logger.error("Failed to import machine %s: %s", item.external_id, exc)

        # 判断整体成功
        if response.error_count == 0:
            response.success = True
            response.message = f"导入完成: 成功 {response.created_count}, 跳过 {response.skipped_count}"
        else:
            response.message = f"导入完成: 成功 {response.created_count}, 跳过 {response.skipped_count}, 失败 {response.error_count}"

        return response