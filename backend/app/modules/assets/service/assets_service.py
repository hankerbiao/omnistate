"""硬件与资产管理服务。"""

import asyncio
import time
from typing import Any, Dict, List, Optional

import paramiko
import requests

from app.modules.assets.repository.models import (
    ComponentLibraryDoc,
    DutDoc,
    TestPlanComponentDoc,
)
from app.shared.service import BaseService


class AssetsService(BaseService):
    """资产管理核心服务（异步）"""

    COMPONENT_UPDATE_FIELDS = {
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
    DUT_UPDATE_FIELDS = {
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

    @staticmethod
    def _sanitize_dut(doc: DutDoc) -> Dict[str, Any]:
        data = BaseService._doc_to_dict(doc)
        data.pop("login_password", None)
        return data

    @staticmethod
    async def _get_by_field_or_raise(doc_cls, field, value, error_message: str):
        doc = await doc_cls.find_one(field == value)
        if not doc:
            raise KeyError(error_message)
        return doc

    @staticmethod
    def _probe_result(status: str, error: Optional[str] = None, response_time_ms: float = 0) -> Dict[str, Any]:
        return {
            "status": status,
            "response_time_ms": round(response_time_ms, 2),
            "error": error,
        }

    @classmethod
    def _probe_exception_result(cls, exc: Exception) -> Dict[str, Any]:
        return cls._probe_result("error", str(exc))

    async def create_component(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建部件字典项。"""
        existing = await ComponentLibraryDoc.find_one(
            ComponentLibraryDoc.part_number == data["part_number"]
        )
        if existing:
            raise ValueError("part_number already exists")
        doc = ComponentLibraryDoc(**data)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_component(self, part_number: str) -> Dict[str, Any]:
        """获取单个部件信息。"""
        doc = await self._get_by_field_or_raise(
            ComponentLibraryDoc,
            ComponentLibraryDoc.part_number,
            part_number,
            "component not found",
        )
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
        """分页查询部件列表。"""
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
        """更新部件信息。"""
        doc = await self._get_by_field_or_raise(
            ComponentLibraryDoc,
            ComponentLibraryDoc.part_number,
            part_number,
            "component not found",
        )
        self._apply_updates(doc, data, self.COMPONENT_UPDATE_FIELDS)
        await doc.save()
        return self._doc_to_dict(doc)

    async def delete_component(self, part_number: str) -> None:
        """删除部件。"""
        doc = await self._get_by_field_or_raise(
            ComponentLibraryDoc,
            ComponentLibraryDoc.part_number,
            part_number,
            "component not found",
        )
        await doc.delete()

    async def create_dut(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建 DUT 资产。"""
        existing = await DutDoc.find_one(DutDoc.asset_id == data["asset_id"])
        if existing:
            raise ValueError("asset_id already exists")
        doc = DutDoc(**data)
        await doc.insert()
        return self._sanitize_dut(doc)

    async def get_dut(self, asset_id: str) -> Dict[str, Any]:
        """获取 DUT 资产详情。"""
        doc = await self._get_by_field_or_raise(DutDoc, DutDoc.asset_id, asset_id, "dut not found")
        return self._sanitize_dut(doc)

    async def list_duts(
            self,
            status: Optional[str] = None,
            owner_team: Optional[str] = None,
            rack_location: Optional[str] = None,
            health_status: Optional[str] = None,
            limit: int = 20,
            offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """分页查询 DUT 列表。"""
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
        return [self._sanitize_dut(doc) for doc in docs]

    async def update_dut(self, asset_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新 DUT 资产信息。"""
        doc = await self._get_by_field_or_raise(DutDoc, DutDoc.asset_id, asset_id, "dut not found")
        self._apply_updates(doc, data, self.DUT_UPDATE_FIELDS)
        await doc.save()
        return self._sanitize_dut(doc)

    async def delete_dut(self, asset_id: str) -> None:
        """删除 DUT。"""
        doc = await self._get_by_field_or_raise(DutDoc, DutDoc.asset_id, asset_id, "dut not found")
        await doc.delete()

    async def test_dut_status(
            self,
            asset_id: str,
    ) -> Dict[str, Any]:
        """测试 DUT 的 OS 和 BMC 可达性。"""
        doc = await self._get_by_field_or_raise(DutDoc, DutDoc.asset_id, asset_id, "dut not found")

        os_test, bmc_test = await asyncio.gather(
            self._test_os_status(doc),
            self._test_bmc_status(doc),
            return_exceptions=True
        )

        os_result = os_test if not isinstance(os_test, Exception) else self._probe_exception_result(os_test)
        bmc_result = bmc_test if not isinstance(bmc_test, Exception) else self._probe_exception_result(bmc_test)

        overall_status = self._calculate_overall_status(os_result, bmc_result)

        return {
            "asset_id": asset_id,
            "os_status": os_result,
            "bmc_status": bmc_result,
            "overall_status": overall_status,
        }

    async def _test_os_status(self, dut: DutDoc) -> Dict[str, Any]:
        """测试 OS 状态。"""
        if not dut.os_ip or not dut.login_username or not dut.login_password:
            return self._probe_result("unreachable", "OS IP or credentials not configured")

        os_port = dut.os_port or 22
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
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
            return self._probe_result("reachable", response_time_ms=response_time)
        except paramiko.AuthenticationException as e:
            return self._probe_result("unreachable", f"SSH authentication failed: {str(e)}")
        except paramiko.SSHException as e:
            return self._probe_result("unreachable", f"SSH connection failed: {str(e)}")
        except Exception as e:
            return self._probe_result("unreachable", f"Unexpected error: {str(e)}")
        finally:
            try:
                ssh.close()
            except Exception:
                pass

    async def _test_bmc_status(self, dut: DutDoc) -> Dict[str, Any]:
        """测试 BMC 状态。"""
        if not dut.bmc_ip or not dut.login_username or not dut.login_password:
            return self._probe_result("unreachable", "BMC IP or credentials not configured")

        bmc_port = dut.bmc_port or 443
        bmc_url = f"https://{dut.bmc_ip}:{bmc_port}/redfish/v1/Systems"

        try:
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
                return self._probe_result("reachable", response_time_ms=response_time)
            return self._probe_result(
                "unreachable",
                f"Redfish API returned status {response.status_code}",
                response_time,
            )
        except requests.exceptions.Timeout:
            return self._probe_result("unreachable", "BMC connection timeout")
        except requests.exceptions.ConnectionError as e:
            return self._probe_result("unreachable", f"BMC connection failed: {str(e)}")
        except Exception as e:
            return self._probe_result("unreachable", f"Unexpected error: {str(e)}")

    def _calculate_overall_status(self, os_result: Dict[str, Any], bmc_result: Dict[str, Any]) -> str:
        """计算整体状态。"""
        os_reachable = os_result.get("status") == "reachable"
        bmc_reachable = bmc_result.get("status") == "reachable"

        if os_reachable and bmc_reachable:
            return "healthy"
        elif os_reachable or bmc_reachable:
            return "degraded"
        else:
            return "unreachable"

    async def create_plan_component(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建测试计划与部件的关联记录。"""
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
        """查询测试计划关联部件列表。"""
        query = TestPlanComponentDoc.find()
        if plan_id:
            query = query.find(TestPlanComponentDoc.plan_id == plan_id)
        if part_number:
            query = query.find(TestPlanComponentDoc.part_number == part_number)

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def delete_plan_component(self, plan_id: str, part_number: str) -> None:
        """删除测试计划关联部件。"""
        doc = await TestPlanComponentDoc.find_one(
            TestPlanComponentDoc.plan_id == plan_id,
            TestPlanComponentDoc.part_number == part_number,
        )
        if not doc:
            raise KeyError("plan component not found")
        await doc.delete()
