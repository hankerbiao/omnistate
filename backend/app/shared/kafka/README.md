# Kafka 模块

`app/shared/kafka` 现在拆成四层职责：

- `config.py`：Kafka 连接、topic、consumer group 配置
- `producer.py`：producer 生命周期和消息发送
- `consumer.py` / `router.py` / `dead_letter.py`：consumer runtime、topic 分发、死信

## 配置来源

模块只认一套配置来源：项目根目录的 `config.yaml`。

`app/shared/config/settings.py` 负责读取和校验 YAML，`app/shared/kafka/config.py`
只把统一配置对象转换成 Kafka runtime 需要的结构，并派生 consumer subscription
元数据。

## 使用方式

```python
from app.shared.kafka import KafkaProducerManager, ResultMessage

manager = KafkaProducerManager()
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
from app.shared.kafka import KafkaProducerManager, load_kafka_config

manager = KafkaProducerManager(
    config=load_kafka_config()
)
```

独立 consumer worker 启动方式：

```bash
python -m app.workers.kafka_worker_main
```
