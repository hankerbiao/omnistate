"""
Kafka 消息管理模块配置 - Kafka 消息管理相关配置
"""

import os
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class KafkaConfig:
    """Kafka 配置类"""

    # Kafka 集群地址
    bootstrap_servers: List[str] = field(default_factory=lambda: [
        os.getenv("KAFKA_BOOTSTRAP_SERVERS", "10.17.154.252:9092")
    ])

    # 客户端 ID
    client_id: str = os.getenv("KAFKA_CLIENT_ID", "dmlv4-shard")

    # 生产者配置
    producer_config: Dict[str, Any] = field(default_factory=lambda: {
        "acks": "all",
        "retries": 3,
        "batch_size": 16384,
        "linger_ms": 10,
        "buffer_memory": 33554432,  # 32MB
        "compression_type": "gzip",
        "max_in_flight_requests_per_connection": 5,
        "request_timeout_ms": 30000,
    })

    # 消费者配置
    consumer_config: Dict[str, Any] = field(default_factory=lambda: {
        "auto_offset_reset": "earliest",
        "enable_auto_commit": True,
        "session_timeout_ms": 30000,
        "heartbeat_interval_ms": 3000,
        "max_poll_records": 100,
        "consumer_timeout_ms": 1000,
        "fetch_max_wait_ms": 500,
        "fetch_min_bytes": 1024,
        "fetch_max_bytes": 52428800,  # 50MB
    })

    # 主题配置
    topic_config: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "dmlv4.tasks": {
            "partitions": 3,
            "replication_factor": 1,
            "retention_hours": 168,  # 7天
            "config": {
                "compression.type": "gzip",
                "min.insync.replicas": 1
            }
        },
        "dmlv4.results": {
            "partitions": 3,
            "replication_factor": 1,
            "retention_hours": 72,  # 3天
            "config": {
                "compression.type": "gzip",
                "min.insync.replicas": 1
            }
        },
        "dmlv4.deadletter": {
            "partitions": 1,
            "replication_factor": 1,
            "retention_hours": 720,  # 30天
            "config": {
                "compression.type": "gzip",
                "min.insync.replicas": 1
            }
        }
    })

    # 安全配置
    security_config: Dict[str, Any] = field(default_factory=lambda: {
        "security_protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
        "sasl_mechanism": os.getenv("KAFKA_SASL_MECHANISM"),
        "sasl_plain_username": os.getenv("KAFKA_USERNAME"),
        "sasl_plain_password": os.getenv("KAFKA_PASSWORD"),
        "ssl_cafile": os.getenv("KAFKA_SSL_CAFILE"),
        "ssl_certfile": os.getenv("KAFKA_SSL_CERTFILE"),
        "ssl_keyfile": os.getenv("KAFKA_SSL_KEYFILE"),
        "ssl_password": os.getenv("KAFKA_SSL_PASSWORD"),
    })

    # 重连配置
    retry_config: Dict[str, Any] = field(default_factory=lambda: {
        "max_reconnect_attempts": 10,
        "reconnect_backoff_ms": 500,
        "reconnect_backoff_max_ms": 10000,
        "retry_backoff_ms": 100,
    })

    # 监控配置
    monitoring_config: Dict[str, Any] = field(default_factory=lambda: {
        "enable_metrics": True,
        "metrics_port": int(os.getenv("SHARD_METRICS_PORT", "8080")),
        "health_check_interval": 30,  # 秒
        "log_level": os.getenv("SHARD_LOG_LEVEL", "INFO")
    })


@dataclass
class TaskConfig:
    """任务相关配置"""

    # 任务类型配置
    task_types: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "test_execution": {
            "description": "测试执行任务",
            "timeout_seconds": 3600,  # 1小时
            "retry_times": 3,
            "priority": 1
        },
        "data_processing": {
            "description": "数据处理任务",
            "timeout_seconds": 1800,  # 30分钟
            "retry_times": 2,
            "priority": 1
        },
        "system_maintenance": {
            "description": "系统维护任务",
            "timeout_seconds": 7200,  # 2小时
            "retry_times": 1,
            "priority": 2
        }
    })

    # 任务分发配置
    dispatch_config: Dict[str, Any] = field(default_factory=lambda: {
        "max_concurrent_tasks": 100,
        "task_queue_size": 1000,
        "priority_levels": 3,  # 0=低, 1=正常, 2=高
        "fair_dispatch": True,  # 公平分发
        "load_balancing": "round_robin"  # 负载均衡策略
    })

    # 任务重试配置
    retry_config: Dict[str, Any] = field(default_factory=lambda: {
        "initial_delay": 1,  # 秒
        "max_delay": 300,    # 5分钟
        "backoff_multiplier": 2,
        "jitter": True
    })


@dataclass
class MessageConfig:
    """消息相关配置"""

    # 序列化配置
    serialization_config: Dict[str, Any] = field(default_factory=lambda: {
        "format": "json",
        "encoding": "utf-8",
        "ensure_ascii": False,
        "compact": True,
        "date_format": "iso8601"
    })

    # 消息大小限制
    size_limits: Dict[str, int] = field(default_factory=lambda: {
        "max_message_size": 1048576,  # 1MB
        "max_batch_size": 10485760,   # 10MB
        "max_request_size": 10485760  # 10MB
    })

    # 消息验证配置
    validation_config: Dict[str, Any] = field(default_factory=lambda: {
        "validate_schema": True,
        "required_fields": ["task_id", "task_type", "task_data", "source"],
        "field_validators": {
            "task_id": {"type": "string", "min_length": 1, "max_length": 255},
            "task_type": {"type": "string", "min_length": 1, "max_length": 100},
            "priority": {"type": "integer", "min": 0, "max": 10}
        }
    })


# 默认配置实例
kafka_config = KafkaConfig()
task_config = TaskConfig()
message_config = MessageConfig()


# 配置方法
def get_kafka_config() -> KafkaConfig:
    """获取 Kafka 配置"""
    return kafka_config


def get_task_config() -> TaskConfig:
    """获取任务配置"""
    return task_config


def get_message_config() -> MessageConfig:
    """获取消息配置"""
    return message_config


def update_config(**kwargs):
    """更新配置"""
    if 'kafka' in kwargs:
        kafka_config.bootstrap_servers = kwargs['kafka'].get('bootstrap_servers', kafka_config.bootstrap_servers)
        kafka_config.client_id = kwargs['kafka'].get('client_id', kafka_config.client_id)

    if 'tasks' in kwargs:
        task_config.task_types.update(kwargs['tasks'].get('types', {}))

    if 'monitoring' in kwargs:
        kafka_config.monitoring_config.update(kwargs['monitoring'])


# 环境变量映射
ENV_MAPPINGS = {
    # Kafka 配置
    "KAFKA_BOOTSTRAP_SERVERS": "kafka.bootstrap_servers",
    "KAFKA_CLIENT_ID": "kafka.client_id",

    # 任务配置
    "SHARD_MAX_CONCURRENT_TASKS": "task.dispatch_config.max_concurrent_tasks",
    "SHARD_TASK_QUEUE_SIZE": "task.dispatch_config.task_queue_size",

    # 监控配置
    "SHARD_METRICS_PORT": "kafka.monitoring_config.metrics_port",
    "SHARD_LOG_LEVEL": "kafka.monitoring_config.log_level",

    # 安全配置
    "KAFKA_SECURITY_PROTOCOL": "kafka.security_config.security_protocol",
    "KAFKA_SASL_MECHANISM": "kafka.security_config.sasl_mechanism",
    "KAFKA_USERNAME": "kafka.security_config.sasl_plain_username",
    "KAFKA_PASSWORD": "kafka.security_config.sasl_plain_password",
}


def load_from_environment():
    """从环境变量加载配置"""
    import os

    for env_var, config_path in ENV_MAPPINGS.items():
        value = os.getenv(env_var)
        if value is None:
            continue

        # 根据配置路径更新配置
        if config_path.startswith("kafka."):
            if config_path == "kafka.bootstrap_servers":
                kafka_config.bootstrap_servers = [value]
            elif config_path == "kafka.client_id":
                kafka_config.client_id = value
        elif config_path.startswith("task.dispatch_config."):
            key = config_path.replace("task.dispatch_config.", "")
            if hasattr(task_config.dispatch_config, key):
                setattr(task_config.dispatch_config, key, int(value))
        elif config_path.startswith("kafka.monitoring_config."):
            key = config_path.replace("kafka.monitoring_config.", "")
            if key == "metrics_port":
                kafka_config.monitoring_config["metrics_port"] = int(value)
            elif key == "log_level":
                kafka_config.monitoring_config["log_level"] = value

