from app.modules.execution.service.execution_service import ExecutionService


def test_execution_service_constructor_is_side_effect_free(monkeypatch):
    started = False

    class FakeKafkaMessageManager:
        def __init__(self):
            pass

        def start(self):
            nonlocal started
            started = True

    monkeypatch.setattr(
        "app.modules.execution.service.execution_service.KafkaMessageManager",
        FakeKafkaMessageManager,
    )

    service = ExecutionService()

    assert service.kafka_manager is not None
    assert started is False
