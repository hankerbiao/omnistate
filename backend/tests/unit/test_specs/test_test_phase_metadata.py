from app.modules.test_specs.schemas.test_case import CreateTestCaseRequest, UpdateTestCaseRequest
from app.modules.test_specs.service.metadata_service import DEFAULT_METADATA, MetadataService


def test_test_phase_metadata_definition_and_defaults():
    definition = MetadataService.definition("TEST_PHASE")

    assert definition == {
        "type_code": "TEST_PHASE",
        "label": "测试阶段",
        "field_name": "test_phase",
    }
    assert [item["code"] for item in DEFAULT_METADATA if item["type_code"] == "TEST_PHASE"] == [
        "EVT",
        "DVT",
        "PVT",
    ]


def test_test_phase_is_available_on_create_and_update_requests():
    base = {
        "lab_id": "lab-1",
        "catalog_path": ["smoke"],
        "title": "phase case",
        "test_phase": "dvt",
    }

    assert CreateTestCaseRequest.model_validate(base).test_phase == "dvt"
    assert UpdateTestCaseRequest(test_phase="PVT").test_phase == "PVT"
