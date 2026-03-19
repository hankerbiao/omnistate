from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.kafka.config import ConsumerSubscription, KafkaConfig  # noqa: E402
from app.shared.kafka.consumer import KafkaConsumerRunner  # noqa: E402


def test_register_subscription_overrides_enable_auto_commit(monkeypatch):
    captured_kwargs = {}

    class FakeKafkaConsumer:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        def subscribe(self, topics):
            self.topics = topics

    import app.shared.kafka.consumer as consumer_module

    monkeypatch.setattr(consumer_module, "KafkaConsumer", FakeKafkaConsumer)

    runner = KafkaConsumerRunner(
        config=KafkaConfig(
            consumer_options={
                "auto_offset_reset": "earliest",
                "enable_auto_commit": True,
            },
        )
    )

    runner.register_subscription(
        "test_events",
        ConsumerSubscription(topic="test-events", group_id="test-group"),
    )

    assert captured_kwargs["enable_auto_commit"] is False
    assert captured_kwargs["group_id"] == "test-group"
