# Kafka 模块

`app/shared/kafka` 现在拆成四层职责：

- `config.py`：Kafka 连接、topic、consumer group 配置
- `producer.py`：producer 生命周期和消息发送
- `consumer.py` / `router.py` / `dead_letter.py`：consumer runtime、topic 分发、死信
- `KafkaMessageManager`：兼容旧调用的 producer-only 包装类

## 配置来源

模块只认一套配置来源：环境变量。

支持的变量：

- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_CLIENT_ID`
- `KAFKA_RESULT_TOPIC`
- `KAFKA_DEAD_LETTER_TOPIC`
- `KAFKA_EXECUTION_RESULT_GROUP_ID`
- `KAFKA_TEST_EVENTS_TOPIC`
- `KAFKA_TEST_EVENTS_GROUP_ID`

其中 `KAFKA_BOOTSTRAP_SERVERS` 支持逗号分隔多个地址。

## 使用方式

```python
from app.shared.kafka import KafkaMessageManager, ResultMessage

manager = KafkaMessageManager()
manager.start()

try:
    manager.send_result(
        ResultMessage(
            task_id="task-001",
            status="PASSED",
            result_data={"summary": "ok"},
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

独立 consumer worker 启动方式：

```bash
python -m app.workers.kafka_worker_main
```
