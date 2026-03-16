"""自动化测试用例库服务。"""

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.modules.test_specs.repository.models import AutomationTestCaseDoc
from app.shared.service import BaseService, SequenceIdService


class AutomationTestCaseService(BaseService):
    """自动化测试用例库 CRUD 服务。"""

    async def create_automation_test_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建自动化测试用例。"""
        payload = deepcopy(data)
        payload["auto_case_id"] = payload.get("auto_case_id") or await self._generate_auto_case_id()

        existing = await AutomationTestCaseDoc.find_one(
            AutomationTestCaseDoc.auto_case_id == payload["auto_case_id"],
            AutomationTestCaseDoc.version == payload.get("version", "1.0.0"),
            {"is_deleted": False},
        )
        if existing:
            raise ValueError("automation test case already exists")

        doc = AutomationTestCaseDoc(**payload)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_automation_test_case(self, auto_case_id: str) -> Dict[str, Any]:
        """按业务编号获取自动化测试用例最新版本。"""
        doc = await AutomationTestCaseDoc.find_one(
            AutomationTestCaseDoc.auto_case_id == auto_case_id,
            {"is_deleted": False},
            sort=[("updated_at", -1)],
        )
        if not doc:
            raise KeyError("automation test case not found")
        return self._doc_to_dict(doc)

    async def list_automation_test_cases(
        self,
        framework: Optional[str] = None,
        automation_type: Optional[str] = None,
        status: Optional[str] = None,
        maintainer_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """分页查询自动化测试用例列表。"""
        query = AutomationTestCaseDoc.find({"is_deleted": False})
        if framework:
            query = query.find(AutomationTestCaseDoc.framework == framework)
        if automation_type:
            query = query.find(AutomationTestCaseDoc.automation_type == automation_type)
        if status:
            query = query.find(AutomationTestCaseDoc.status == status)
        if maintainer_id:
            query = query.find(AutomationTestCaseDoc.maintainer_id == maintainer_id)

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def _generate_auto_case_id(self) -> str:
        """自动生成自动化用例编号。"""
        year = datetime.now().year
        prefix = f"ATC-{year}-"
        counter_key = f"automation_test_case:{year}"
        next_seq = await SequenceIdService().next(counter_key)
        return f"{prefix}{str(next_seq).zfill(5)}"
