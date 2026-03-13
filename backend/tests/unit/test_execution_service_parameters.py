from types import SimpleNamespace

import pytest

from app.modules.execution.application.execution_service import ExecutionService


class TestExecutionServiceParameters:
    def test_select_parameter_doc_prefers_requested_set(self):
        service = ExecutionService()
        default_doc = SimpleNamespace(case_id="TC-001", parameter_set_id="DEFAULT", is_default=True)
        requested_doc = SimpleNamespace(case_id="TC-001", parameter_set_id="SIT", is_default=False)
        grouped = {"TC-001": [default_doc, requested_doc]}

        selected = service._select_parameter_doc("TC-001", grouped, "SIT")

        assert selected is requested_doc

    def test_select_parameter_doc_falls_back_to_default(self):
        service = ExecutionService()
        default_doc = SimpleNamespace(case_id="TC-001", parameter_set_id="DEFAULT", is_default=True)
        grouped = {"TC-001": [default_doc]}

        selected = service._select_parameter_doc("TC-001", grouped)

        assert selected is default_doc

    def test_select_parameter_doc_raises_when_requested_set_missing(self):
        service = ExecutionService()

        with pytest.raises(KeyError, match="Parameter set not found for case TC-001: SIT"):
            service._select_parameter_doc("TC-001", {"TC-001": []}, "SIT")

    def test_build_case_payload_includes_parameters(self):
        service = ExecutionService()
        case_doc = SimpleNamespace(
            case_id="TC-001",
            title="Login smoke",
            version=2,
            priority="P1",
            status="approved",
            custom_fields={"absolute_path": "/tmp/test_login.py"},
            script_entity_id="SCRIPT-001",
            automation_type="api",
            automation_case_ref=SimpleNamespace(auto_case_id="AUTO-001", version="1.0.0"),
            estimated_duration_sec=60,
            required_env={"env": "sit"},
            tags=["smoke"],
        )
        parameter_doc = SimpleNamespace(
            parameter_set_id="PARAM-SIT",
            profile_name="SIT params",
            version=3,
            parameters={"base_url": "http://sit.example.com"},
        )

        payload = service._build_case_payload(case_doc, parameter_doc)

        assert payload["absolute_path"] == "/tmp/test_login.py"
        assert payload["parameter_set_id"] == "PARAM-SIT"
        assert payload["parameter_profile_name"] == "SIT params"
        assert payload["parameter_version"] == 3
        assert payload["parameters"] == {"base_url": "http://sit.example.com"}
