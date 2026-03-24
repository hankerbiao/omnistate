# RabbitMQ 模块

`app/shared/rabbitmq` 提供与 `shared/kafka` 平级的 producer-only 下发能力。

- `config.py`：RabbitMQ 连接和队列配置
- `producer.py`：producer 生命周期和消息发送
- `rabbitmq_message_manager.py`：兼容旧式 manager 命名的包装类

当前模块复用 `TaskMessage` 的 JSON 序列化格式，因此切换到 RabbitMQ 时不会修改任务消息体。
