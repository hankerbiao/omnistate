# Kafka 消息管理模块

Kafka 消息管理模块为 DMLv4 系统提供了完整的消息队列解决方案，用于任务分发、结果收集和系统解耦。本模块基于 Apache Kafka 实现，支持高吞吐量的异步任务处理。

## 📋 目录结构

```
kafka/
├── __init__.py                 # 模块初始化和导出
├── config.py                   # Kafka 配置管理
├── kafka_message_manager.py    # 核心消息管理器
└── README.md                   # 本文档
```

## 🏗️ 架构概览

本模块采用生产者-消费者模式，主要包含三个核心主题：

- **`dmlv4.tasks`** - 任务分发主题，用于发送待执行的任务
- **`dmlv4.results`** - 结果收集主题，用于接收任务执行结果
- **`dmlv4.deadletter`** - 死信队列，用于处理失败或无法处理的消息

## 🔧 核心组件

### 1. TaskMessage（任务消息）

任务消息是发送到 Kafka 集群的基本单位，包含任务的所有必要信息。

**核心属性：**
- `task_id` - 唯一任务标识符
- `task_type` - 任务类型（如：test_execution、data_processing）
- `task_data` - 任务数据（字典格式）
- `source` - 消息来源系统
- `priority` - 任务优先级（0=正常，1=高优先级，2=紧急）
- `create_time` - 任务创建时间

**主要方法：**
```python
# 创建任务消息
task_msg = TaskMessage(
    task_id="task-001",
    task_type="test_execution",
    task_data={"test_name": "DDR5 Test", "duration": 5},
    source="dmlv4-system",
    priority=1
)

# 转换为 JSON
json_str = task_msg.to_json()

# 从 JSON 创建实例
task_msg = TaskMessage.from_json(json_str)
```

### 2. ResultMessage（结果消息）

结果消息用于传递任务执行结果，包含执行状态和返回数据。

**核心属性：**
- `task_id` - 对应的任务 ID
- `status` - 执行状态（SUCCESS、FAILED、RUNNING）
- `result_data` - 执行结果数据
- `error_message` - 错误信息（如有）
- `executor` - 执行器标识
- `complete_time` - 完成时间

**主要方法：**
```python
# 创建结果消息
result_msg = ResultMessage(
    task_id="task-001",
    status="SUCCESS",
    result_data={"duration": 5, "result": "PASSED"},
    executor="test-executor"
)

# JSON 序列化/反序列化
json_str = result_msg.to_json()
result_msg = ResultMessage.from_json(json_str)
```

### 3. KafkaMessageManager（消息管理器）

核心的消息管理类，提供完整的生产者和消费者功能。

**主要功能：**
- 生产者功能：发送任务消息、结果消息、死信消息
- 消费者功能：处理任务消息、收集结果消息
- 任务处理：支持同步和异步任务处理模式
- 死信队列：处理无法处理的消息
- 上下文管理：支持 `with` 语句自动管理生命周期

**初始化：**
```python
from app.shared.kafka import KafkaMessageManager

# 使用默认配置
mgr = KafkaMessageManager()

# 使用自定义配置
mgr = KafkaMessageManager(
    bootstrap_servers=["10.17.154.252:9092"],
    client_id="dmlv4-shard-01"
)
```

**基本使用模式：**
```python
# 方式 1：上下文管理器（推荐）
with KafkaMessageManager() as mgr:
    # 创建任务
    task = TaskMessage("task-001", "test_execution", {"test": "data"})

    # 发送任务
    success = mgr.send_task(task)

    # 注册处理器
    mgr.register_task_handler("test_execution", my_handler)

    # 处理任务
    mgr.process_tasks(max_tasks=10)

    # 收集结果
    results = mgr.collect_results()

# 方式 2：手动管理
mgr = KafkaMessageManager()
mgr.start()

try:
    # 使用管理器
    mgr.send_task(task)
finally:
    mgr.stop()
```

### 4. KafkaConfig（配置管理）

统一的 Kafka 配置管理，支持环境变量和代码配置。

**配置类别：**

#### 基础连接配置
```python
from app.shared.kafka.config import KafkaConfig

config = KafkaConfig(
    bootstrap_servers=["10.17.154.252:9092"],
    client_id="dmlv4-shard"
)
```

#### 生产者配置
```python
config.producer_config = {
    "acks": "all",                           # 确认级别
    "retries": 3,                            # 重试次数
    "batch_size": 16384,                     # 批处理大小
    "linger_ms": 10,                         # 批处理延迟
    "buffer_memory": 33554432,               # 32MB 缓冲区
    "compression_type": "gzip",              # 压缩类型
}
```

#### 消费者配置
```python
config.consumer_config = {
    "auto_offset_reset": "earliest",         # 偏移量重置策略
    "enable_auto_commit": True,              # 自动提交偏移量
    "session_timeout_ms": 30000,             # 会话超时
    "heartbeat_interval_ms": 3000,           # 心跳间隔
    "max_poll_records": 100,                 # 最大拉取记录数
}
```

#### 主题配置
```python
config.topic_config = {
    "dmlv4.tasks": {
        "partitions": 3,                      # 分区数
        "replication_factor": 1,              # 副本因子
        "retention_hours": 168,               # 保留时间（7天）
    }
}
```

#### 安全配置
```python
config.security_config = {
    "security_protocol": "PLAINTEXT",         # 安全协议
    "sasl_mechanism": "PLAIN",               # SASL 机制
    "sasl_plain_username": "user",            # 用户名
    "sasl_plain_password": "pass",            # 密码
}
```

**从环境变量加载配置：**
```python
from app.shared.kafka.config import load_from_environment

# 自动从环境变量加载配置
load_from_environment()
```

## 🚀 使用示例

### 示例 1：基础任务处理

```python
import logging
from app.shared.kafka import KafkaMessageManager, TaskMessage, ResultMessage

# 配置日志
logging.basicConfig(level=logging.INFO)

# 定义任务处理器
def test_execution_handler(task_msg: TaskMessage) -> ResultMessage:
    """测试执行处理器"""
    test_name = task_msg.task_data.get("test_name")
    duration = task_msg.task_data.get("duration", 5)

    # 模拟任务执行
    import time
    time.sleep(duration)

    return ResultMessage(
        task_id=task_msg.task_id,
        status="SUCCESS",
        result_data={
            "test_name": test_name,
            "duration": duration,
            "result": "PASSED"
        },
        executor="test-executor"
    )

# 使用消息管理器
with KafkaMessageManager() as mgr:
    # 注册处理器
    mgr.register_task_handler("test_execution", test_execution_handler)

    # 创建并发送任务
    task = TaskMessage(
        task_id="task-001",
        task_type="test_execution",
        task_data={
            "test_name": "DDR5 Memory Test",
            "duration": 3
        }
    )

    # 发送任务
    if mgr.send_task(task):
        print(f"任务已发送: {task.task_id}")

        # 处理任务
        mgr.process_tasks(max_tasks=1)

        # 收集结果
        results = mgr.collect_results()
        for result in results:
            print(f"任务结果: {result.task_id} - {result.status}")
```

### 示例 2：批量任务处理

```python
from app.shared.kafka import KafkaMessageManager, TaskMessage

def batch_task_processing():
    """批量任务处理示例"""
    with KafkaMessageManager() as mgr:
        # 创建多个任务
        tasks = []
        for i in range(10):
            task = TaskMessage(
                task_id=f"task-batch-{i:03d}",
                task_type="data_processing",
                task_data={
                    "batch_id": f"batch-{i:03d}",
                    "input_data": list(range(100))
                }
            )
            tasks.append(task)
            mgr.send_task(task)

        # 处理所有任务
        mgr.process_tasks(max_tasks=len(tasks))

        # 批量收集结果
        results = mgr.collect_results()
        print(f"处理完成，共 {len(results)} 个结果")

batch_task_processing()
```

### 示例 3：异步任务处理

```python
import asyncio
from app.shared.kafka import KafkaMessageManager, TaskMessage

async def async_task_processing():
    """异步任务处理示例"""
    mgr = KafkaMessageManager()
    mgr.start()

    try:
        # 发送任务
        task = TaskMessage("async-task-001", "test_execution", {"test": "async"})
        mgr.send_task(task)

        # 异步处理任务
        await mgr.process_tasks_async(max_tasks=1)

    finally:
        mgr.stop()

# 运行异步处理
asyncio.run(async_task_processing())
```

### 示例 4：错误处理和死信队列

```python
from app.shared.kafka import KafkaMessageManager, TaskMessage, ResultMessage

def error_handling_example():
    """错误处理示例"""
    def unreliable_handler(task_msg: TaskMessage) -> ResultMessage:
        """可能失败的处理器"""
        import random
        if random.random() < 0.5:  # 50% 失败率
            raise Exception("随机错误")

        return ResultMessage(
            task_id=task_msg.task_id,
            status="SUCCESS",
            result_data={"message": "成功"},
            executor="unreliable-handler"
        )

    with KafkaMessageManager() as mgr:
        mgr.register_task_handler("unreliable", unreliable_handler)

        # 发送多个任务
        for i in range(5):
            task = TaskMessage(
                task_id=f"unreliable-task-{i}",
                task_type="unreliable",
                task_data={"attempt": i}
            )
            mgr.send_task(task)

        # 处理任务（失败的会进入死信队列）
        mgr.process_tasks(max_tasks=5)

        # 收集结果
        results = mgr.collect_results()
        for result in results:
            print(f"任务 {result.task_id}: {result.status}")

error_handling_example()
```

## ⚙️ 配置最佳实践

### 1. 环境变量配置

推荐使用环境变量配置 Kafka 连接：

```bash
# .env 文件
KAFKA_BOOTSTRAP_SERVERS=10.17.154.252:9092
KAFKA_CLIENT_ID=dmlv4-production
KAFKA_USERNAME=admin
KAFKA_PASSWORD=secret
KAFKA_SECURITY_PROTOCOL=SASL_PLAINTEXT
```

```python
# 加载配置
from app.shared.kafka.config import load_from_environment
load_from_environment()
```

### 2. 主题规划

根据业务需求规划主题：

| 主题 | 分区数 | 副本因子 | 保留时间 | 用途 |
|------|--------|----------|----------|------|
| dmlv4.tasks | 3 | 1 | 7天 | 任务分发 |
| dmlv4.results | 3 | 1 | 3天 | 结果收集 |
| dmlv4.deadletter | 1 | 1 | 30天 | 死信队列 |

### 3. 性能调优

**生产者优化：**
- 调整 `batch_size` 和 `linger_ms` 平衡延迟和吞吐量
- 使用压缩减少网络传输（`compression_type: "gzip"`）
- 设置合适的 `retries` 和 `acks` 平衡可靠性和性能

**消费者优化：**
- 调整 `max_poll_records` 控制单次拉取量
- 设置合适的 `session_timeout_ms` 和 `heartbeat_interval_ms`
- 根据处理速度调整 `enable_auto_commit`

### 4. 监控建议

**关键指标：**
- 消息发送成功率
- 任务处理延迟
- 消费者滞后量（lag）
- 死信队列消息数量
- 错误率

**监控代码：**
```python
def get_monitoring_info(mgr):
    """获取监控信息"""
    # 获取消费者滞后
    lag_info = mgr.get_consumer_lag()
    print(f"消费者滞后: {lag_info}")

    # 检查运行状态
    print(f"运行状态: {mgr.is_running}")

    # 检查活跃消费者
    print(f"活跃消费者: {list(mgr.consumers.keys())}")
```

## 🛡️ 错误处理

### 常见错误类型

1. **连接错误**
   - Kafka 集群不可达
   - 网络超时
   - 认证失败

2. **消息错误**
   - 消息格式错误
   - 消息大小超限
   - 序列化错误

3. **处理错误**
   - 处理器未注册
   - 处理器执行异常
   - 超时错误

### 错误处理策略

```python
from kafka.errors import KafkaError, KafkaTimeoutError
import logging

def safe_send_task(mgr: KafkaMessageManager, task: TaskMessage) -> bool:
    """安全发送任务"""
    try:
        return mgr.send_task(task)
    except KafkaTimeoutError:
        logging.error(f"任务发送超时: {task.task_id}")
        return False
    except KafkaError as e:
        logging.error(f"Kafka 错误: {e}")
        return False
    except Exception as e:
        logging.error(f"未知错误: {e}")
        return False
```

## 📚 API 参考

### KafkaMessageManager

#### 方法列表

| 方法 | 描述 | 参数 |
|------|------|------|
| `__init__` | 初始化管理器 | `bootstrap_servers`, `client_id` |
| `start` | 启动管理器 | 无 |
| `stop` | 停止管理器 | 无 |
| `send_task` | 发送任务消息 | `task_message`, `priority` |
| `send_result` | 发送结果消息 | `result_message` |
| `send_to_dead_letter_queue` | 发送死信消息 | `original_message`, `error_reason` |
| `register_task_handler` | 注册任务处理器 | `task_type`, `handler_func` |
| `process_tasks` | 同步处理任务 | `max_tasks` |
| `process_tasks_async` | 异步处理任务 | `max_tasks` |
| `collect_results` | 收集结果消息 | `timeout_ms` |
| `get_consumer_lag` | 获取消费者滞后 | 无 |

#### 上下文管理

```python
# 支持 with 语句
with KafkaMessageManager() as mgr:
    # 使用管理器
    pass
# 自动调用 stop()
```

### TaskMessage

#### 构造函数

```python
TaskMessage(
    task_id: str,           # 任务ID（必填）
    task_type: str,         # 任务类型（必填）
    task_data: Dict,        # 任务数据（必填）
    source: str = "dmlv4-system",  # 来源系统
    priority: int = 1       # 优先级
)
```

#### 序列化方法

```python
# 转为字典
data = task_msg.to_dict()

# 转为 JSON
json_str = task_msg.to_json()

# 从 JSON 创建
task_msg = TaskMessage.from_json(json_str)
```

### ResultMessage

#### 构造函数

```python
ResultMessage(
    task_id: str,                    # 任务ID（必填）
    status: str,                     # 状态（必填）
    result_data: Dict = None,        # 结果数据
    error_message: str = None,       # 错误信息
    executor: str = "unknown"        # 执行器
)
```

#### 状态常量

- `"SUCCESS"` - 任务成功
- `"FAILED"` - 任务失败
- `"RUNNING"` - 任务运行中

## 🔗 相关链接

- [Apache Kafka 官方文档](https://kafka.apache.org/documentation/)
- [Kafka Python 客户端](https://kafka-python.readthedocs.io/)
- [DMLv4 项目文档](https://github.com/dmlv4/project-docs)

## 📝 更新日志

### v1.0.0
- 初始版本
- 实现基础消息管理功能
- 支持任务分发和结果收集
- 集成配置管理
- 支持死信队列

---

**注意：** 本模块是为 DMLv4 系统定制开发的，提供了完整的企业级 Kafka 消息处理解决方案。在生产环境使用前，请根据实际需求调整配置参数。