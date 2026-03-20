"""自动化测试用例库服务。"""

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.modules.test_specs.repository.models import (
    AutomationTestCaseDoc,
    CodeSnapshotModel,
    ConfigFieldModel,
    ReportMetaModel,
    ScriptRefModel,
    TestCaseDoc,
)
from app.shared.service import BaseService, SequenceIdService


class AutomationTestCaseService(BaseService):
    """自动化测试用例库 CRUD 服务。"""

    async def create_automation_test_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建自动化测试用例。"""
        payload = deepcopy(data)
        payload["auto_case_id"] = payload.get("auto_case_id") or await self._generate_auto_case_id()

        existing = await AutomationTestCaseDoc.find_one(
            AutomationTestCaseDoc.auto_case_id == payload["auto_case_id"],
            {"is_deleted": False},
        )
        if existing:
            raise ValueError("automation test case already exists")

        doc = AutomationTestCaseDoc(**payload)
        await doc.insert()
        return self._doc_to_dict(doc)

    async def get_automation_test_case(self, auto_case_id: str) -> Dict[str, Any]:
        """按业务编号获取自动化测试用例。"""
        doc = await AutomationTestCaseDoc.find_one(
            AutomationTestCaseDoc.auto_case_id == auto_case_id,
            {"is_deleted": False},
        )
        if not doc:
            raise KeyError("automation test case not found")
        return self._doc_to_dict(doc)

    async def get_automation_test_case_by_manual_case_id(self, dml_manual_case_id: str) -> Dict[str, Any]:
        """按 dml_manual_case_id 查询记录。"""
        doc = await AutomationTestCaseDoc.find_one(
            {"dml_manual_case_id": dml_manual_case_id, "is_deleted": False},
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
        dml_manual_case_id: Optional[str] = None,
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
        if dml_manual_case_id:
            query = query.find({"dml_manual_case_id": dml_manual_case_id})

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def report_automation_test_case_metadata(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """接收自动化测试框架批量上报的用例配置元数据并逐条 upsert。"""
        cases, summary = self._extract_report_payload(payload)

        results: List[Dict[str, Any]] = []
        linked_count = 0
        conflict_count = 0

        for metadata in cases:
            dml_manual_case_id = self._extract_manual_case_id(metadata)
            existing = await AutomationTestCaseDoc.find_one(
                {"dml_manual_case_id": dml_manual_case_id, "is_deleted": False},
            )
            doc_data = self._build_report_doc_data(dml_manual_case_id, metadata, summary)

            if existing:
                self._apply_updates(existing, doc_data, doc_data.keys())
                await existing.save()
                result = await self._finalize_report_result(existing, metadata)
            else:
                doc_data["auto_case_id"] = await self._generate_auto_case_id()
                doc = AutomationTestCaseDoc(**doc_data)
                await doc.insert()
                result = await self._finalize_report_result(doc, metadata)

            if result.get("linked"):
                linked_count += 1
            if result.get("conflict"):
                conflict_count += 1
            results.append(result)

        return {
            "total_cases": len(cases),
            "saved_count": len(results),
            "linked_count": linked_count,
            "conflict_count": conflict_count,
            "summary": summary,
            "cases": results,
        }

    @staticmethod
    def _build_report_doc_data(
        dml_manual_case_id: str,
        metadata: Dict[str, Any],
        summary: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """将框架上报载荷转换为规范化自动化用例文档。"""
        summary = summary or {}
        git_snapshot = metadata.get("git_snapshot") or summary.get("git_snapshot") or {}
        param_spec = AutomationTestCaseService._normalize_param_spec(metadata.get("param_spec") or [])
        framework = str(
            metadata.get("framework")
            or metadata.get("test_framework")
            or metadata.get("runner")
            or "reported"
        )
        script_path = metadata.get("script_path")
        config_path = metadata.get("config_path")

        return {
            "name": dml_manual_case_id,
            "dml_manual_case_id": dml_manual_case_id,
            "description": metadata.get("description"),
            "status": "ACTIVE",
            "framework": framework,
            "automation_type": metadata.get("module"),
            "script_ref": ScriptRefModel(
                entity_id=script_path or config_path or dml_manual_case_id,
                module=metadata.get("module"),
                project_tag=metadata.get("project_tag"),
                project_scope=metadata.get("project_scope"),
            ),
            "config_path": config_path,
            "script_name": metadata.get("script_name"),
            "script_path": script_path,
            "code_snapshot": CodeSnapshotModel(
                version=str(git_snapshot.get("commit_short_id") or "reported"),
                commit_id=git_snapshot.get("commit_id"),
                commit_short_id=git_snapshot.get("commit_short_id"),
                branch=git_snapshot.get("branch"),
                author=git_snapshot.get("commit_author"),
                commit_time=git_snapshot.get("commit_time"),
                message=git_snapshot.get("commit_message"),
            ),
            "param_spec": param_spec,
            "tags": metadata.get("tags") or [],
            "report_meta": ReportMetaModel(
                requirement_id=metadata.get("requirement_id"),
                author=metadata.get("author"),
                timeout=metadata.get("timeout"),
            ),
        }

    @staticmethod
    def _extract_report_payload(payload: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """校验上报体结构，并提取批量 case 元数据。"""
        if not payload:
            raise ValueError("report payload cannot be empty")
        case_items = payload.get("cases")
        if not isinstance(case_items, list) or not case_items:
            raise ValueError("report payload.cases must be a non-empty list")
        for metadata in case_items:
            if not isinstance(metadata, dict):
                raise ValueError("case metadata must be an object")
        summary = payload.get("summary") or {}
        if not isinstance(summary, dict):
            raise ValueError("report payload.summary must be an object")
        total_cases = summary.get("total_cases")
        if total_cases is not None:
            if not isinstance(total_cases, int):
                raise ValueError("report payload.summary.total_cases must be an integer")
            if total_cases != len(case_items):
                raise ValueError("report payload.summary.total_cases must match cases length")
        modules = summary.get("modules")
        if modules is not None and not isinstance(modules, dict):
            raise ValueError("report payload.summary.modules must be an object")
        git_snapshot = summary.get("git_snapshot")
        if git_snapshot is not None and not isinstance(git_snapshot, dict):
            raise ValueError("report payload.summary.git_snapshot must be an object")
        return case_items, summary

    @staticmethod
    def _extract_manual_case_id(metadata: Dict[str, Any]) -> str:
        """从单条上报元数据中提取框架侧 case 标识。"""
        dml_manual_case_id = str(
            metadata.get("dml_manual_case_id")
            or metadata.get("case_id")
            or ""
        ).strip()
        if not dml_manual_case_id:
            raise ValueError("case metadata.dml_manual_case_id is required")
        return dml_manual_case_id

    @staticmethod
    def _normalize_param_spec(param_spec: List[Dict[str, Any]]) -> List[ConfigFieldModel]:
        """将参数定义标准化为 ConfigFieldModel，保证新建/更新路径一致。"""
        return [field if isinstance(field, ConfigFieldModel) else ConfigFieldModel(**field) for field in param_spec]

    async def _finalize_report_result(
        self,
        auto_doc: AutomationTestCaseDoc,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """在自动化用例落库后，尽力回链测试用例并返回结果。"""
        link_result = await self._try_link_test_case(auto_doc, metadata)
        result = self._doc_to_dict(auto_doc)
        result.update(link_result)
        return result

    async def _try_link_test_case(
        self,
        auto_doc: AutomationTestCaseDoc,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """根据唯一关联键查找是否存在已关联的平台测试用例。"""
        dml_manual_case_id = auto_doc.dml_manual_case_id
        if not dml_manual_case_id:
            return {
                "linked": False,
                "linked_case_id": None,
                "conflict": False,
                "conflict_message": None,
            }

        case_doc = await TestCaseDoc.find_one(
            {"case_id": dml_manual_case_id, "is_deleted": False},
        )
        if not case_doc:
            return {
                "linked": False,
                "linked_case_id": None,
                "conflict": False,
                "conflict_message": None,
            }
        return {
            "linked": True,
            "linked_case_id": case_doc.case_id,
            "conflict": False,
            "conflict_message": None,
        }

    async def _generate_auto_case_id(self) -> str:
        """自动生成自动化用例编号。"""
        year = datetime.now().year
        prefix = f"ATC-{year}-"
        counter_key = f"automation_test_case:{year}"
        next_seq = await SequenceIdService().next(counter_key)
        return f"{prefix}{str(next_seq).zfill(5)}"
