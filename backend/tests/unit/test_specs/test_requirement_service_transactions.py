import pytest

from app.modules.test_specs.service.requirement_service import RequirementService


class _FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self):
        self.transaction_started = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def start_transaction(self):
        self.transaction_started = True
        return _FakeTransaction()


class _FakeClient:
    def __init__(self):
        self.session = _FakeSession()

    def start_session(self):
        return self.session


@pytest.mark.asyncio
async def test_create_requirement_transaction_awaits_start_transaction(monkeypatch):
    service = RequirementService()
    client = _FakeClient()

    class _FakeRequirementDoc:
        req_id = "req_id"

        def __init__(self, **kwargs):
            self.id = "req-doc-1"
            self.__dict__.update(kwargs)

        @classmethod
        async def find_one(cls, *args, **kwargs):
            return None

        async def insert(self, session=None):
            return None

        def model_dump(self):
            return {
                "req_id": self.req_id,
                "title": self.title,
                "description": self.description,
                "tpm_owner_id": self.tpm_owner_id,
                "workflow_item_id": self.workflow_item_id,
                "status": self.status,
            }

    async def fake_create_item(self, **kwargs):
        return {"id": "workflow-1", "current_state": "DRAFT"}

    monkeypatch.setattr(
        "app.modules.test_specs.service.requirement_service.AsyncWorkflowService.create_item",
        fake_create_item,
    )
    monkeypatch.setattr(
        "app.modules.test_specs.service.requirement_service.TestRequirementDoc",
        _FakeRequirementDoc,
    )

    payload = {
        "req_id": "TR-2026-00001",
        "title": "Requirement A",
        "description": "desc",
        "tpm_owner_id": "user-1",
    }

    result = await service._create_requirement_with_transaction(client, payload)

    assert client.session.transaction_started is True
    assert result["req_id"] == "TR-2026-00001"
    assert result["workflow_item_id"] == "workflow-1"
