from app.modules.test_specs.schemas.requirement import (
    CreateRequirementRequest,
    UpdateRequirementRequest,
)
from app.modules.test_specs.schemas.test_case import (
    CreateTestCaseRequest,
    UpdateTestCaseRequest,
)
from app.modules.test_specs.service.requirement_service import RequirementService
from app.modules.test_specs.service.test_case_service import TestCaseService


def test_requirement_request_schemas_do_not_expose_status_field():
    assert "status" not in CreateRequirementRequest.model_fields
    assert "status" not in UpdateRequirementRequest.model_fields


def test_test_case_request_schemas_do_not_expose_status_field():
    assert "status" not in CreateTestCaseRequest.model_fields
    assert "status" not in UpdateTestCaseRequest.model_fields


def test_requirement_service_update_whitelist_excludes_status():
    assert "status" not in RequirementService._UPDATABLE_FIELDS


def test_test_case_service_update_whitelist_excludes_status():
    assert "status" not in TestCaseService._UPDATABLE_FIELDS
