"""硬件与资产管理服务

AI 友好注释说明：
- Service 层负责业务规则与数据库访问的编排。
- 本服务包含三个子域：部件字典、DUT 资产、测试计划关联部件。
- 这里不处理鉴权，仅实现 CRUD 与基础校验。
"""
import asyncio
import uuid
import paramiko
import requests
from typing import List, Dict, Any, Optional
from app.modules.assets.repository.models import (
    ComponentLibraryDoc,
    DutDoc,
    TestPlanComponentDoc,
)
from app.shared.service import BaseService
from app.shared.infrastructure.resource_lock import get_lock_manager, ResourceLockContext


class AssetsService(BaseService):
    """资产管理核心服务（异步）"""

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
        """更新部件信息"""
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
        """更新 DUT 资产信息"""
        doc = await DutDoc.find_one(DutDoc.asset_id == asset_id)
        if not doc:
            raise KeyError("dut not found")
        for key, value in data.items():
            setattr(doc, key, value)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_dut(self, asset_id: str) -> None:
        """删除 DUT（物理删除）"""
        doc = await DutDoc.find_one(DutDoc.asset_id == asset_id)
        if not doc:
            raise KeyError("dut not found")
        await doc.delete()

    async def test_dut_status(
        self,
        asset_id: str,
        use_lock: bool = True,
        lock_ttl: int = 300,
        wait_timeout: float = 0
    ) -> Dict[str, Any]:
        """测试 DUT 机器状态（OS 状态 + BMC 状态）

        流程：
        1. 获取 DUT 信息
        2. 获取资源锁（防止并发测试冲突）
        3. 并发测试 OS 状态（SSH）和 BMC 状态（Redfish）
        4. 释放资源锁
        5. 返回综合测试结果

        Args:
            asset_id: 资产编号
            use_lock: 是否使用资源锁，默认为 True
            lock_ttl: 锁超时时间（秒），默认 300 秒
            wait_timeout: 等待获取锁的超时时间（秒），0 表示不等待

        Returns:
            包含 OS 和 BMC 状态的字典：
            {
                "asset_id": str,
                "os_status": {
                    "status": "reachable" | "unreachable",
                    "response_time_ms": float,
                    "error": str | None
                },
                "bmc_status": {
                    "status": "reachable" | "unreachable",
                    "response_time_ms": float,
                    "error": str | None
                },
                "overall_status": "healthy" | "degraded" | "unreachable",
                "lock_acquired": bool,
                "lock_owner": str | None
            }
        """
        doc = await DutDoc.find_one(DutDoc.asset_id == asset_id)
        if not doc:
            raise KeyError("dut not found")

        lock_manager = get_lock_manager()
        lock_owner = str(uuid.uuid4())
        lock_acquired = False

        try:
            if use_lock:
                lock_context = ResourceLockContext(
                    manager=lock_manager,
                    resource_id=asset_id,
                    lock_type="dut_test",
                    owner=lock_owner,
                    ttl_seconds=lock_ttl,
                    wait_timeout=wait_timeout
                )
                await lock_context.__aenter__()
                lock_acquired = True

            os_test, bmc_test = await asyncio.gather(
                self._test_os_status(doc),
                self._test_bmc_status(doc),
                return_exceptions=True
            )

            os_result = os_test if not isinstance(os_test, Exception) else {
                "status": "error",
                "response_time_ms": 0,
                "error": str(os_test)
            }

            bmc_result = bmc_test if not isinstance(bmc_test, Exception) else {
                "status": "error",
                "response_time_ms": 0,
                "error": str(bmc_test)
            }

            overall_status = self._calculate_overall_status(os_result, bmc_result)

            return {
                "asset_id": asset_id,
                "os_status": os_result,
                "bmc_status": bmc_result,
                "overall_status": overall_status,
                "lock_acquired": lock_acquired,
                "lock_owner": lock_owner if lock_acquired else None
            }

        finally:
            if lock_acquired:
                await lock_manager.release_lock(
                    resource_id=asset_id,
                    lock_type="dut_test",
                    owner=lock_owner
                )

    async def _test_os_status(self, dut: DutDoc) -> Dict[str, Any]:
        """测试 OS 状态（SSH 连接）

        Args:
            dut: DUT 文档对象

        Returns:
            OS 状态测试结果
        """
        if not dut.os_ip or not dut.login_username or not dut.login_password:
            return {
                "status": "unreachable",
                "response_time_ms": 0,
                "error": "OS IP or credentials not configured"
            }

        os_port = dut.os_port or 22
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            import time
            start_time = time.time()
            await asyncio.to_thread(
                ssh.connect,
                dut.os_ip,
                port=os_port,
                username=dut.login_username,
                password=dut.login_password,
                timeout=10
            )
            response_time = (time.time() - start_time) * 1000

            ssh.close()
            return {
                "status": "reachable",
                "response_time_ms": round(response_time, 2),
                "error": None
            }
        except paramiko.AuthenticationException as e:
            return {
                "status": "unreachable",
                "response_time_ms": 0,
                "error": f"SSH authentication failed: {str(e)}"
            }
        except paramiko.SSHException as e:
            return {
                "status": "unreachable",
                "response_time_ms": 0,
                "error": f"SSH connection failed: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "response_time_ms": 0,
                "error": f"Unexpected error: {str(e)}"
            }
        finally:
            try:
                ssh.close()
            except:
                pass

    async def _test_bmc_status(self, dut: DutDoc) -> Dict[str, Any]:
        """测试 BMC 状态（Redfish API）

        Args:
            dut: DUT 文档对象

        Returns:
            BMC 状态测试结果
        """
        if not dut.bmc_ip or not dut.login_username or not dut.login_password:
            return {
                "status": "unreachable",
                "response_time_ms": 0,
                "error": "BMC IP or credentials not configured"
            }

        bmc_port = dut.bmc_port or 443
        bmc_url = f"https://{dut.bmc_ip}:{bmc_port}/redfish/v1/Systems"

        try:
            import time
            start_time = time.time()
            response = await asyncio.to_thread(
                requests.get,
                bmc_url,
                auth=(dut.login_username, dut.login_password),
                verify=False,
                timeout=10
            )
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return {
                    "status": "reachable",
                    "response_time_ms": round(response_time, 2),
                    "error": None
                }
            else:
                return {
                    "status": "unreachable",
                    "response_time_ms": round(response_time, 2),
                    "error": f"Redfish API returned status {response.status_code}"
                }
        except requests.exceptions.Timeout:
            return {
                "status": "unreachable",
                "response_time_ms": 0,
                "error": "BMC connection timeout"
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "status": "unreachable",
                "response_time_ms": 0,
                "error": f"BMC connection failed: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "response_time_ms": 0,
                "error": f"Unexpected error: {str(e)}"
            }

    def _calculate_overall_status(self, os_result: Dict[str, Any], bmc_result: Dict[str, Any]) -> str:
        """计算整体状态

        Args:
            os_result: OS 状态测试结果
            bmc_result: BMC 状态测试结果

        Returns:
            整体状态：healthy | degraded | unreachable
        """
        os_reachable = os_result.get("status") == "reachable"
        bmc_reachable = bmc_result.get("status") == "reachable"

        if os_reachable and bmc_reachable:
            return "healthy"
        elif os_reachable or bmc_reachable:
            return "degraded"
        else:
            return "unreachable"

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
