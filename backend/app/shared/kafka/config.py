"""Kafka 模块配置适配层。

Kafka 的真实配置来源可以是 `config/config.yaml`（默认）或 MongoDB `system_configs`
集合（动态覆盖）。本模块通过 `_dynamic_config` 机制支持运行时从数据库加载配置。
"""

from dataclasses import dataclass, field
from typing import Any

from app.shared.config import KafkaConfig as BaseKafkaConfig, get_settings
from app.shared.core.logger import log


# ── 动态配置（启动时从 MongoDB 加载，覆盖 config/config.yaml）─────────
_dynamic_config: dict[str, Any] | None = None


def override_kafka_config(config: dict[str, Any]) -> None:
    """设置动态 Kafka 配置（从 MongoDB 加载的覆盖值）。

    必须在任何 load_kafka_config() 调用之前设置，由 lifespan 中的
    load_kafka_config_from_db() 触发。
    """
    global _dynamic_config
    _dynamic_config = config
    log.info("Kafka 动态配置已设置: {}", list(config.keys()))


def _parse_db_value(value: str, config_type: str) -> Any:
    """解析 MongoDB 中存储的配置值为 Python 类型。"""
    if config_type == "integer":
        return int(value)
    elif config_type == "float":
        return float(value)
    elif config_type == "boolean":
        return value.lower() in ("true", "1", "yes", "on")
    elif config_type == "json":
        import json
        return json.loads(value)
    return value


async def load_kafka_config_from_db() -> None:
    """从 MongoDB system_configs 集合加载 Kafka 配置覆盖。

    生命周期调用顺序：先连 MongoDB → 初始化 Beanie → 初始化默认配置
    → 加载 Kafka 数据库配置。

    仅在数据库中有 kafka.* 配置项且 is_active=True 时生效，
    否则静默跳过，使用 config/config.yaml 中的配置。
    """
    try:
        from app.modules.system_config.repository.models import SystemConfigDoc

        docs = await SystemConfigDoc.find(
            {"config_key": {"$regex": r"^kafka\."}, "is_active": True}
        ).to_list()

        if not docs:
            return

        config: dict[str, Any] = {}
        for doc in docs:
            key = doc.config_key[len("kafka."):]
            value = _parse_db_value(doc.config_value, doc.config_type)
            if value is not None:
                config[key] = value

        if config:
            override_kafka_config(config)
    except Exception as exc:
        log.warning("从数据库加载 Kafka 配置失败（使用 config/config.yaml 默认值）: {}", exc)


@dataclass(slots=True)
class ConsumerSubscription:
    """单个 consumer 订阅配置。"""

    topic: str
    group_id: str
    parser: str = "json"
    dead_letter_topic: str | None = None


@dataclass(slots=True)
class KafkaConfig:
    """Kafka 运行时配置。

    该对象不再定义 Kafka 默认值，避免与 `app.shared.config.settings.KafkaConfig`
    形成第二套配置来源。所有字段都由 `config/config.yaml` 经统一 settings 加载后传入。
    """

    bootstrap_servers: list[str]
    client_id: str
    result_topic: str
    dead_letter_topic: str
    test_events_topic: str
    execution_result_group_id: str
    test_events_group_id: str
    producer_options: dict[str, Any]
    consumer_options: dict[str, Any]

    # Kafka consumer runner 需要的派生订阅配置，不作为独立配置源维护。
    consumer_subscriptions: dict[str, ConsumerSubscription] = field(default_factory=dict)

    def __post_init__(self):
        if not self.consumer_subscriptions:
            self.consumer_subscriptions = {
                "execution_result": ConsumerSubscription(
                    topic=self.result_topic,
                    group_id=self.execution_result_group_id,
                    dead_letter_topic=self.dead_letter_topic,
                ),
                "test_events": ConsumerSubscription(
                    topic=self.test_events_topic,
                    group_id=self.test_events_group_id,
                    dead_letter_topic=self.dead_letter_topic,
                ),
            }


def _to_runtime_config(base_config: BaseKafkaConfig) -> KafkaConfig:
    """把统一配置模型转换成 Kafka 模块运行时配置。"""
    return KafkaConfig(
        bootstrap_servers=list(base_config.bootstrap_servers),
        client_id=base_config.client_id,
        result_topic=base_config.result_topic,
        dead_letter_topic=base_config.dead_letter_topic,
        test_events_topic=base_config.test_events_topic,
        execution_result_group_id=base_config.execution_result_group_id,
        test_events_group_id=base_config.test_events_group_id,
        producer_options=base_config.producer_options.model_dump(),
        consumer_options=base_config.consumer_options.model_dump(),
    )


def load_kafka_config() -> KafkaConfig:
    """从统一配置加载 Kafka 配置，并转换成 Kafka 模块运行时结构。

    配置优先级：
    1. 动态配置（从 MongoDB 加载，覆盖优先）
    2. 静态配置（config/config.yaml）
    """
    global _dynamic_config
    if _dynamic_config is not None:
        log.debug("Kafka 使用数据库动态配置: {}", {k: v for k, v in _dynamic_config.items() if k not in ("producer_options", "consumer_options")})
        return KafkaConfig(**_dynamic_config)
    return _to_runtime_config(get_settings().kafka)


__all__ = ["KafkaConfig", "ConsumerSubscription", "load_kafka_config", "load_kafka_config_from_db", "override_kafka_config"]
