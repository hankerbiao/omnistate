# Kafka 模块

`app/shared/kafka` 现在只保留三类职责：

- `TaskMessage` 和 `ResultMessage`：Kafka 消息载体
- `KafkaConfig`：运行时配置对象
- `KafkaMessageManager`：生产、消费、健康检查和生命周期管理

## 配置来源

模块只认一套配置来源：环境变量。

支持的变量：

- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_CLIENT_ID`
- `KAFKA_TASK_TOPIC`
- `KAFKA_RESULT_TOPIC`
- `KAFKA_DEAD_LETTER_TOPIC`

其中 `KAFKA_BOOTSTRAP_SERVERS` 支持逗号分隔多个地址。

## 使用方式

```python
from app.shared.kafka import KafkaMessageManager, TaskMessage

manager = KafkaMessageManager()
manager.start()

try:
    manager.send_task(
        TaskMessage(
            task_id="task-001",
            task_type="execution_task",
            task_data={"foo": "bar"},
        )
    )
finally:
    manager.stop()
```

如果需要显式注入配置：

```python
from app.shared.kafka import KafkaConfig, KafkaMessageManager

manager = KafkaMessageManager(
    config=KafkaConfig(
        bootstrap_servers=["127.0.0.1:9092"],
        client_id="local-dev",
    )
)
```
