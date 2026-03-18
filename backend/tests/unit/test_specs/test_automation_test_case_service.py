from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.test_specs.service import automation_test_case_service as service_module
from app.modules.test_specs.service.automation_test_case_service import AutomationTestCaseService


@pytest.mark.asyncio
async def test_report_automation_test_case_metadata_creates_new_doc(monkeypatch):
    service = AutomationTestCaseService()
    payload = {
        "cases": [{
            "__type__": "CaseMetadata",
            "case_id": "001_basic_check",
            "requirement_id": "suite-fan-001",
            "title": "风扇基础功能测试",
            "module": "universal",
            "project_tag": "universal",
            "project_scope": "",
            "description": "desc",
            "author": "BMC 测试团队",
            "timeout": 300,
            "tags": ["fan"],
            "config_path": "tests/universal/suite/fan/001_basic_check/config.py",
            "param_spec": [{"name": "target_ip", "type": "str"}],
            "git_snapshot": {
                "commit_short_id": "f8a26e1",
                "branch": "dev-bmc-12345",
                "commit_id": "full-commit",
            },
        }],
        "summary": {"total_cases": 1},
    }

    created_docs = []

    class FakeAutomationTestCaseDoc:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        async def insert(self):
            self.id = "mock-id"
            created_docs.append(self)

        def model_dump(self, by_alias=True):
            return {
                "auto_case_id": self.auto_case_id,
                "source_case_id": self.source_case_id,
                "name": self.name,
                "description": self.description,
                "status": self.status,
                "framework": self.framework,
                "automation_type": self.automation_type,
                "script_ref": self.script_ref.model_dump(),
                "code_snapshot": self.code_snapshot.model_dump(),
                "param_spec": [field.model_dump(by_alias=by_alias) for field in self.param_spec],
                "tags": self.tags,
                "report_meta": self.report_meta.model_dump(),
                "created_at": getattr(self, "created_at", None),
                "updated_at": getattr(self, "updated_at", None),
            }

        @staticmethod
        async def find_one(*args, **kwargs):
            return None

    class FakeTestCaseDoc:
        @staticmethod
        async def find_one(*args, **kwargs):
            return None

    monkeypatch.setattr(service_module, "AutomationTestCaseDoc", FakeAutomationTestCaseDoc)
    monkeypatch.setattr(service_module, "TestCaseDoc", FakeTestCaseDoc)
    monkeypatch.setattr(service, "_generate_auto_case_id", AsyncMock(return_value="ATC-2026-00001"))

    result = await service.report_automation_test_case_metadata(payload)

    assert result["total_cases"] == 1
    assert result["saved_count"] == 1
    assert result["summary"] == {"total_cases": 1}
    assert result["cases"][0]["auto_case_id"] == "ATC-2026-00001"
    assert result["cases"][0]["source_case_id"] == "001_basic_check"
    assert result["cases"][0]["code_snapshot"]["version"] == "f8a26e1"
    assert result["cases"][0]["script_ref"]["entity_id"] == "tests/universal/suite/fan/001_basic_check/config.py"
    assert result["cases"][0]["report_meta"]["requirement_id"] == "suite-fan-001"
    assert result["cases"][0]["linked"] is False
    assert result["cases"][0]["linked_case_id"] is None
    assert result["cases"][0]["conflict"] is False
    assert created_docs[0].param_spec[0].name == "target_ip"


@pytest.mark.asyncio
async def test_report_automation_test_case_metadata_updates_existing_doc(monkeypatch):
    service = AutomationTestCaseService()
    payload = {
        "cases": [{
            "__type__": "CaseMetadata",
            "case_id": "001_basic_check",
            "platform_case_id": "TC-2026-00003",
            "title": "风扇基础功能测试",
            "module": "universal",
            "project_tag": "universal",
            "description": "new desc",
            "tags": ["fan", "smoke"],
            "param_spec": [{"name": "target_ip", "type": "str"}],
            "git_snapshot": {"commit_short_id": "f8a26e1"},
        }],
        "summary": {},
    }

    existing = SimpleNamespace(
        id="mock-id",
        auto_case_id="ATC-2026-00001",
        source_case_id="001_basic_check",
        name="old",
        description=None,
        status="ACTIVE",
        framework="CaseMetadata",
        automation_type=None,
        script_ref=SimpleNamespace(entity_id="old-script", model_dump=lambda: {"entity_id": "old-script"}),
        code_snapshot=SimpleNamespace(version="old", model_dump=lambda: {"version": "old"}),
        param_spec=[],
        tags=[],
        report_meta=SimpleNamespace(model_dump=lambda: {}),
        created_at="created",
        updated_at="updated",
        model_dump=lambda by_alias=True: {
            "auto_case_id": existing.auto_case_id,
            "source_case_id": existing.source_case_id,
            "name": existing.name,
            "description": existing.description,
            "status": existing.status,
            "framework": existing.framework,
            "automation_type": existing.automation_type,
            "script_ref": existing.script_ref.model_dump(),
            "code_snapshot": existing.code_snapshot.model_dump(),
            "param_spec": [],
            "tags": existing.tags,
            "report_meta": existing.report_meta.model_dump(),
            "created_at": existing.created_at,
            "updated_at": existing.updated_at,
        },
    )
    existing.save = AsyncMock()

    class FakeAutomationTestCaseDoc:
        @staticmethod
        async def find_one(*args, **kwargs):
            return existing

    class FakeTestCaseDoc:
        @staticmethod
        async def find_one(*args, **kwargs):
            return None

    monkeypatch.setattr(service_module, "AutomationTestCaseDoc", FakeAutomationTestCaseDoc)
    monkeypatch.setattr(service_module, "TestCaseDoc", FakeTestCaseDoc)

    result = await service.report_automation_test_case_metadata(payload)

    assert result["cases"][0]["source_case_id"] == "001_basic_check"
    assert result["cases"][0]["linked"] is False
    assert result["cases"][0]["linked_case_id"] is None
    assert result["cases"][0]["conflict"] is False
    assert existing.name == "风扇基础功能测试"
    assert existing.tags == ["fan", "smoke"]
    assert existing.code_snapshot.version == "f8a26e1"
    existing.save.assert_awaited_once()


def test_extract_report_payload_rejects_invalid_cases():
    payload = {
        "cases": [],
        "summary": {},
    }

    with pytest.raises(ValueError, match="non-empty list"):
        AutomationTestCaseService._extract_report_payload(payload)


@pytest.mark.asyncio
async def test_report_automation_test_case_metadata_not_linked_without_matching_case_id(monkeypatch):
    service = AutomationTestCaseService()
    payload = {
        "cases": [{
            "__type__": "CaseMetadata",
            "case_id": "001_basic_check",
            "platform_case_id": "TC-001",
            "title": "风扇基础功能测试",
            "module": "universal",
            "param_spec": [{"name": "target_ip", "type": "str"}],
            "git_snapshot": {"commit_short_id": "f8a26e1"},
        }],
        "summary": {},
    }

    existing_auto_doc = SimpleNamespace(
        id="mock-id",
        auto_case_id="ATC-2026-00002",
        source_case_id="001_basic_check",
        name="风扇基础功能测试",
        description=None,
        status="ACTIVE",
        framework="CaseMetadata",
        automation_type="universal",
        script_ref=SimpleNamespace(entity_id="tests/path/config.py", model_dump=lambda: {"entity_id": "tests/path/config.py"}),
        code_snapshot=SimpleNamespace(version="f8a26e1", model_dump=lambda: {"version": "f8a26e1"}),
        param_spec=[],
        tags=[],
        report_meta=SimpleNamespace(model_dump=lambda: {}),
        created_at="created",
        updated_at="updated",
        model_dump=lambda by_alias=True: {
            "auto_case_id": existing_auto_doc.auto_case_id,
            "source_case_id": existing_auto_doc.source_case_id,
            "name": existing_auto_doc.name,
            "description": existing_auto_doc.description,
            "status": existing_auto_doc.status,
            "framework": existing_auto_doc.framework,
            "automation_type": existing_auto_doc.automation_type,
            "script_ref": existing_auto_doc.script_ref.model_dump(),
            "code_snapshot": existing_auto_doc.code_snapshot.model_dump(),
            "param_spec": [],
            "tags": existing_auto_doc.tags,
            "report_meta": existing_auto_doc.report_meta.model_dump(),
            "created_at": existing_auto_doc.created_at,
            "updated_at": existing_auto_doc.updated_at,
        },
    )
    existing_auto_doc.save = AsyncMock()

    class FakeAutomationTestCaseDoc:
        @staticmethod
        async def find_one(*args, **kwargs):
            return existing_auto_doc

    class FakeTestCaseDoc:
        @staticmethod
        async def find_one(*args, **kwargs):
            return None

    monkeypatch.setattr(service_module, "AutomationTestCaseDoc", FakeAutomationTestCaseDoc)
    monkeypatch.setattr(service_module, "TestCaseDoc", FakeTestCaseDoc)

    result = await service.report_automation_test_case_metadata(payload)

    assert result["cases"][0]["linked"] is False
    assert result["cases"][0]["linked_case_id"] is None
    assert result["cases"][0]["conflict"] is False


@pytest.mark.asyncio
async def test_report_automation_test_case_metadata_saves_multiple_cases(monkeypatch):
    service = AutomationTestCaseService()
    payload = {
        "cases": [
            {
                "__type__": "CaseMetadata",
                "case_id": "001_basic_check",
                "title": "case-1",
                "module": "universal",
                "config_path": "tests/a.py",
                "git_snapshot": {"commit_short_id": "abc1234"},
            },
            {
                "__type__": "CaseMetadata",
                "case_id": "002_power_cycle",
                "title": "case-2",
                "module": "jdm",
                "config_path": "tests/b.py",
                "git_snapshot": {"commit_short_id": "def5678"},
            },
        ],
        "summary": {"total_cases": 2},
    }

    created_docs = []

    class FakeAutomationTestCaseDoc:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        async def insert(self):
            self.id = f"mock-{len(created_docs) + 1}"
            created_docs.append(self)

        def model_dump(self, by_alias=True):
            return {
                "auto_case_id": self.auto_case_id,
                "source_case_id": self.source_case_id,
                "name": self.name,
                "description": self.description,
                "status": self.status,
                "framework": self.framework,
                "automation_type": self.automation_type,
                "script_ref": self.script_ref.model_dump(),
                "code_snapshot": self.code_snapshot.model_dump(),
                "param_spec": [],
                "tags": self.tags,
                "report_meta": self.report_meta.model_dump(),
                "created_at": getattr(self, "created_at", None),
                "updated_at": getattr(self, "updated_at", None),
            }

        @staticmethod
        async def find_one(*args, **kwargs):
            return None

    class FakeTestCaseDoc:
        @staticmethod
        async def find_one(*args, **kwargs):
            return None

    monkeypatch.setattr(service_module, "AutomationTestCaseDoc", FakeAutomationTestCaseDoc)
    monkeypatch.setattr(service_module, "TestCaseDoc", FakeTestCaseDoc)
    monkeypatch.setattr(
        service,
        "_generate_auto_case_id",
        AsyncMock(side_effect=["ATC-2026-00001", "ATC-2026-00002"]),
    )

    result = await service.report_automation_test_case_metadata(payload)

    assert result["total_cases"] == 2
    assert result["saved_count"] == 2
    assert len(result["cases"]) == 2
    assert created_docs[0].source_case_id == "001_basic_check"
    assert created_docs[1].source_case_id == "002_power_cycle"


@pytest.mark.asyncio
async def test_report_automation_test_case_metadata_links_by_matching_test_case_id(monkeypatch):
    service = AutomationTestCaseService()
    payload = {
        "cases": [{
            "__type__": "CaseMetadata",
            "case_id": "TC-2026-00003",
            "title": "风扇基础功能测试",
            "module": "universal",
            "config_path": "tests/universal/suite/fan/config.py",
            "git_snapshot": {"commit_short_id": "f8a26e1"},
        }],
        "summary": {},
    }

    created_docs = []

    class FakeAutomationTestCaseDoc:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        async def insert(self):
            self.id = "mock-id"
            created_docs.append(self)

        def model_dump(self, by_alias=True):
            return {
                "auto_case_id": self.auto_case_id,
                "source_case_id": self.source_case_id,
                "name": self.name,
                "description": self.description,
                "status": self.status,
                "framework": self.framework,
                "automation_type": self.automation_type,
                "script_ref": self.script_ref.model_dump(),
                "code_snapshot": self.code_snapshot.model_dump(),
                "param_spec": [],
                "tags": self.tags,
                "report_meta": self.report_meta.model_dump(),
                "created_at": getattr(self, "created_at", None),
                "updated_at": getattr(self, "updated_at", None),
            }

        @staticmethod
        async def find_one(*args, **kwargs):
            return None

    class FakeTestCaseDoc:
        @staticmethod
        async def find_one(*args, **kwargs):
            return SimpleNamespace(case_id="TC-2026-00003")

    monkeypatch.setattr(service_module, "AutomationTestCaseDoc", FakeAutomationTestCaseDoc)
    monkeypatch.setattr(service_module, "TestCaseDoc", FakeTestCaseDoc)
    monkeypatch.setattr(service, "_generate_auto_case_id", AsyncMock(return_value="ATC-2026-00011"))

    result = await service.report_automation_test_case_metadata(payload)

    assert created_docs[0].source_case_id == "TC-2026-00003"
    assert result["cases"][0]["linked"] is True
    assert result["cases"][0]["linked_case_id"] == "TC-2026-00003"
