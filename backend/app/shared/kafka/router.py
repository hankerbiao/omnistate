"""Kafka topic routing registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel


KafkaHandler = Callable[[BaseModel, dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class KafkaTopicRegistration:
    """Topic handler registration."""

    topic: str
    schema: type[BaseModel]
    handler: KafkaHandler


class KafkaTopicHandlerRegistry:
    """Manage topic -> schema -> async handler routing."""

    def __init__(self) -> None:
        self._registrations: dict[str, KafkaTopicRegistration] = {}

    def register(
        self,
        topic: str,
        schema: type[BaseModel],
        handler: KafkaHandler,
    ) -> None:
        self._registrations[topic] = KafkaTopicRegistration(
            topic=topic,
            schema=schema,
            handler=handler,
        )

    async def dispatch(
        self,
        topic: str,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        registration = self._registrations.get(topic)
        if registration is None:
            raise KeyError(f"No Kafka handler registered for topic: {topic}")

        event = registration.schema.model_validate(payload)
        await registration.handler(event, metadata)

    def has_topic(self, topic: str) -> bool:
        return topic in self._registrations

    def list_topics(self) -> list[str]:
        return sorted(self._registrations.keys())
