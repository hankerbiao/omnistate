# 发件箱模式 (Outbox Pattern) - DML V4 集成模块

## 📋 概述

发件箱模式是 DML V4 系统中 Phase 5 的核心架构改进，用于解决**外部副作用耦合**问题。该模式通过本地事务与外部系统解耦，确保数据一致性和可靠的事件传递。

**核心价值：**
- ✅ 提供可靠的重试机制和错误恢复
- ✅ 解耦业务逻辑与外部系统依赖
- ✅ 支持异步处理和批量优化
- ⚠️ **实际实现为分步执行，依赖最终一致性保证**

## ⚠️ 重要说明：理论与实际实现的差异

**理论设计（理想状态）：**
- 业务数据和Outbox事件在同一MongoDB事务中创建
- 确保原子性：要么都成功，要么都失败

**实际实现（DML V4 当前状态）：**
- 业务数据和Outbox事件分步创建，**无事务保证**
- 依赖最终一致性：通过OutboxWorker异步处理
- 假设Outbox事件创建失败概率极低
- 需要完善的监控和告警机制

**风险说明：**
- 极小概率出现业务数据创建成功但Outbox事件创建失败的情况
- 需要监控Outbox事件积压，及时发现异常
- 建议在生产环境中完善MongoDB事务实现

---

## 🎯 解决的问题

### 传统分布式系统的数据一致性问题

```
❌ 问题场景：
1. 业务操作成功写入数据库
2. 外部系统(Kafka)消息发送失败
3. 导致数据不一致：数据库有记录，但外部未收到事件

✅ Outbox模式解决方案：
1. 业务操作和Outbox事件在同一事务中创建
2. 异步Worker可靠处理Outbox事件
3. 确保最终一致性：数据库和外部系统状态一致
```

### 核心问题对比

| 问题类型 | 传统方式 | Outbox模式 |
|---------|---------|-----------|
| **数据一致性** | ❌ 无法保证原子性 | ✅ 本地事务保证 |
| **外部依赖** | ❌ 强依赖外部系统 | ✅ 解耦外部依赖 |
| **失败处理** | ❌ 难以恢复 | ✅ 自动重试机制 |
| **监控能力** | ❌ 难以追踪 | ✅ 完整状态跟踪 |

---

## 🏗️ 架构设计

### 组件架构图

```
┌─────────────────┐    同步事务    ┌─────────────────┐    异步处理    ┌─────────────────┐
│   业务逻辑层     │ ───────────→ │  OutboxEventDoc │ ───────────→ │  外部系统      │
│ (Command Service) │             │   (本地DB)      │             │   (Kafka)      │
└─────────────────┘             └─────────────────┘             └─────────────────┘
         │                              │                              │
         │                              │                              │
    业务数据更新                  事件持久化                    可靠消息传递
    (ExecutionTask等)            (PENDING状态)                 (SENT状态)
```

### 核心组件

**1. 数据模型层 (`OutboxEventDoc`)**
- 发件箱事件文档模型
- 存储需要发布到外部系统的事件
- 支持状态管理和重试机制

**2. 服务层 (`OutboxService`)**
- 发件箱事件管理服务
- 提供创建、查询、更新操作
- 支持事务性操作

**3. 工作器层 (`OutboxWorker`)**
- 异步事件处理工作器
- 批量处理待发布事件
- 实现重试策略和错误处理

**4. 集成层 (`KafkaTaskPublisher`)**
- 外部系统集成适配器
- 负责实际的事件发布
- 支持多种外部系统

---

## 💾 数据模型

### OutboxEventDoc 字段说明

```python
class OutboxEventDoc(Document):
    # 事件标识
    event_id: str                    # 事件唯一标识（UUID）
    aggregate_type: str              # 聚合类型（ExecutionTask、TestCase等）
    aggregate_id: str                # 聚合ID（task_id、case_id等）

    # 事件内容
    event_type: str                  # 事件类型（如'execution_task_dispatched'）
    payload: Dict[str, Any]          # 事件负载数据

    # 发布状态
    status: str = "PENDING"          # 状态：PENDING、SENT、FAILED、PERMANENTLY_FAILED
    retry_count: int = 0             # 重试次数
    next_retry_at: Optional[datetime] # 下次重试时间

    # 错误信息
    last_error: Optional[str]        # 最后一次错误信息
    error_history: List[str]         # 错误历史（最多5条）

    # 时间戳
    created_at: datetime             # 事件创建时间
    updated_at: datetime             # 事件更新时间
    sent_at: Optional[datetime]      # 成功发布时间
```

### 状态流转

```
PENDING ──→ SENT (成功发布)
    │
    ├──→ FAILED (发布失败)
    │        │
    │        └──→ PENDING (重试后再次处理)
    │                │
    │                └──→ ... (最多重试5次)
    │                        │
    └──→ PERMANENTLY_FAILED (达到最大重试次数)
```

---

## 🚀 使用指南

### 1. 创建发件箱事件

在业务操作中创建业务数据和发件箱事件（实际实现）：

```python
# 注意：这是示例代码，实际实现请参考 ExecutionCommandService.dispatch_execution_task
from app.modules.execution.application.execution_command_service import ExecutionCommandService
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.test_specs.repository.models import TestCaseDoc
from app.modules.execution.repository.models import ExecutionTaskDoc, ExecutionTaskCaseDoc
from app.shared.integration.outbox_service import OutboxService

# 模拟的异步函数示例
async def dispatch_execution_task_example(command: DispatchExecutionTaskCommand, actor_id: str):
    """分发执行任务 - 使用Outbox模式确保一致性
    
    注意：实际实现中没有使用MongoDB事务，而是分步执行
    业务数据和Outbox事件分别创建，但OutboxWorker确保最终一致性
    """
    # 步骤1: 验证命令
    validation_errors = command.validate()
    if validation_errors:
        raise ValueError(f"Command validation failed: {', '.join(validation_errors)}")

    # 步骤2: 验证测试用例存在
    case_ids = command.case_ids
    docs = await TestCaseDoc.find({
        "case_id": {"$in": case_ids},
        "is_deleted": False
    }).to_list()

    # 步骤3: 创建ExecutionTaskDoc（业务数据）
    task_doc = ExecutionTaskDoc(
        task_id=command.task_id,
        external_task_id=command.external_task_id,
        framework=command.framework,
        dispatch_status="DISPATCHING",
        overall_status="QUEUED",
        request_payload=command.kafka_task_data,
        created_by=command.created_by,
        case_count=len(case_ids),
    )
    await task_doc.insert()

    # 步骤4: 创建Outbox事件（分别创建，无事务）
    outbox_service = OutboxService()  # 实际代码中通过类属性 self.outbox_service 访问
    outbox_event = await outbox_service.create_execution_task_event(
        task_id=command.task_id,
        external_task_id=command.external_task_id,
        kafka_task_data=command.kafka_task_data,
        created_by=command.created_by
    )

    # 步骤5: 为每个用例创建快照记录
    for cid in case_ids:
        await ExecutionTaskCaseDoc(
            task_id=command.task_id,
            case_id=cid,
            status="QUEUED",
        ).insert()

    # 步骤6: 更新任务状态
    task_doc.dispatch_status = "CREATED"
    task_doc.dispatch_response = {
        "accepted": True,
        "message": "Task created successfully, pending Kafka dispatch",
        "outbox_event_id": outbox_event.event_id,
    }
    await task_doc.save()

    return {
        "task_id": task_doc.task_id,
        "outbox_event_id": outbox_event.event_id,
        "message": "Task created and queued for Kafka dispatch"
    }
```

**重要说明：**
- 实际实现中**没有使用MongoDB事务**，而是分步执行
- 业务数据和Outbox事件分别创建，不在同一事务中
- 通过OutboxWorker的异步处理确保最终一致性
- 这种设计假设：创建Outbox事件极少失败，且失败时业务数据已存在

### 2. 事件类型定义

支持的事件类型：

| 事件类型 | 聚合类型 | 描述 |
|---------|---------|------|
| `execution_task_dispatched` | ExecutionTask | 执行任务已分发 |
| `execution_completed` | ExecutionTask | 执行任务已完成 |
| `test_case_updated` | TestCase | 测试用例已更新 |
| `requirement_status_changed` | TestRequirement | 需求状态已变更 |

### 3. 事件负载格式

```python
# 执行任务分发事件负载示例
{
    "task_id": "ET-2026-000001",
    "external_task_id": "EXT-ET-2026-000001",
    "task_type": "自动化测试",
    "target_environment": "生产环境",
    "priority": 1,
    "payload": {
        "test_cases": ["TC-001", "TC-002"],
        "execution_config": {
            "timeout": 3600,
            "retry_count": 3
        }
    },
    "dispatched_at": "2026-03-09T05:03:00Z",
    "dispatcher": "system"
}
```

---

## ⚙️ 配置说明

### MongoDB 集合配置

Outbox 事件存储在 MongoDB 的 `integration_outbox` 集合中。

**集合索引：**
```python
indexes = [
    IndexModel("status"),                                    # 状态查询
    IndexModel("aggregate_type"),                           # 聚合类型查询
    IndexModel("aggregate_id"),                             # 聚合ID查询
    IndexModel("event_type"),                               # 事件类型查询
    IndexModel("created_at"),                               # 创建时间排序
    IndexModel("next_retry_at"),                            # 重试时间查询
    IndexModel([("status", ASCENDING), ("created_at", ASCENDING)])  # 批量处理优化
]
```

### 环境配置

```bash
# .env 文件配置
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=dmlv4

# Kafka配置（外部系统）
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CLIENT_ID=dmlv4-outbox-worker
KAFKA_TOPIC_PREFIX=dmlv4.

# Outbox工作器配置
OUTBOX_BATCH_SIZE=50
OUTBOX_WORKER_INTERVAL=5  # 秒
OUTBOX_MAX_RETRIES=5
OUTBOX_RETRY_BASE_DELAY=2  # 秒
```

### 应用启动配置

在 `app/main.py` 中确保 OutboxEventDoc 已注册：

```python
await init_beanie(
    database=client[settings.MONGO_DB_NAME],
    document_models=[
        # ... 其他模型 ...
        OutboxEventDoc,  # 必须包含
        # ...
    ]
)
```

---

## 🔄 工作流程

### 完整事件生命周期

```
1. 业务操作触发
   ↓
2. 验证命令和业务逻辑
   ↓
3. 执行业务操作（更新业务数据）
   ↓
4. 创建Outbox事件（分步执行，无事务）
   ↓
5. 创建其他相关记录（用例快照等）
   ↓
6. 更新业务数据状态
   ↓
7. OutboxWorker异步处理：
   a) 扫描PENDING事件
   b) 获取外部系统连接
   c) 发布事件到外部系统
   d) 更新事件状态（SENT/FAILED）
   ↓
8. 失败重试机制（如需要）
```

**实际执行流程分析：**
- **无事务保证**：业务数据和Outbox事件分步创建，可能出现业务数据创建成功但Outbox事件创建失败的情况
- **最终一致性**：通过OutboxWorker的重试机制，确保Outbox事件最终能够被处理
- **风险控制**：假设Outbox事件创建操作极其可靠，失败概率极低
- **监控重要性**：需要监控Outbox事件积压，及时发现异常情况

### OutboxWorker 处理流程

```python
async def _process_batch(self):
    """批量处理Outbox事件"""
    try:
        # 1. 获取待处理事件
        events = await self._get_outbox_service().get_pending_events(self.batch_size)

        for event in events:
            try:
                # 2. 发布到外部系统
                await self._publish_to_external_system(event)

                # 3. 标记为已发送
                await self._mark_event_as_sent(event)

            except Exception as e:
                # 4. 处理失败情况
                await self._handle_event_failure(event, str(e))

    except Exception as e:
        # 5. 批处理异常处理
        await self._handle_batch_error(e)
```

---

## 🔧 重试机制

### 重试策略

**指数退避算法：**
- 第1次重试：2秒后
- 第2次重试：4秒后
- 第3次重试：8秒后
- 第4次重试：16秒后
- 第5次重试：32秒后
- 最大延迟：300秒（5分钟）

### 失败处理

```python
def mark_as_failed(self, error_message: str) -> None:
    """标记为失败并增加重试计数"""
    self.retry_count += 1
    self.last_error = error_message
    self.error_history.append(f"{datetime.now(timezone.utc).isoformat()}: {error_message}")

    # 保持错误历史最多5条
    if len(self.error_history) > 5:
        self.error_history = self.error_history[-5:]

    # 设置状态
    if self.retry_count >= 5:  # 最多重试5次
        self.status = "PERMANENTLY_FAILED"
    else:
        self.status = "FAILED"
        # 指数退避重试策略
        retry_delay_seconds = min(2 ** self.retry_count, 300)  # 最多5分钟
        self.next_retry_at = datetime.now(timezone.utc).timestamp() + retry_delay_seconds
```

---

## 📊 监控和运维

### 监控指标

**关键性能指标：**

| 指标 | 说明 | 告警阈值 |
|-----|------|----------|
| `outbox_pending_count` | 待处理事件数量 | > 1000 |
| `outbox_failed_count` | 失败事件数量 | > 100 |
| `outbox_processing_latency` | 处理延迟 | > 30秒 |
| `outbox_success_rate` | 成功率 | < 95% |

### 健康检查

```python
# 注意：这些方法名称可能需要根据实际OutboxService的实现调整
async def check_outbox_health() -> Dict[str, Any]:
    """Outbox模块健康检查"""
    from app.shared.integration.outbox_service import OutboxService
    from app.shared.integration.outbox_models import OutboxEventDoc
    
    outbox_service = OutboxService()

    # 检查待处理事件数量 (实际方法名可能不同)
    pending_count = await OutboxEventDoc.find({"status": "PENDING"}).count()

    # 检查失败事件数量
    failed_count = await OutboxEventDoc.find({"status": {"$in": ["FAILED", "PERMANENTLY_FAILED"]}}).count()

    # 检查最近处理时间 (可能需要通过聚合查询实现)
    recent_events = await OutboxEventDoc.find(
        {"status": {"$in": ["SENT", "FAILED", "PERMANENTLY_FAILED"]}}
    ).sort("-updated_at").limit(1).to_list()
    
    last_processed = recent_events[0].updated_at if recent_events else None

    return {
        "status": "healthy" if pending_count < 1000 else "warning",
        "pending_events": pending_count,
        "failed_events": failed_count,
        "last_processed": last_processed
    }
```

### 运维工具

**1. 清理永久失败事件：**
```python
# 清理超过7天的永久失败事件
from app.shared.integration.outbox_models import OutboxEventDoc
from datetime import datetime, timedelta, timezone

cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
result = await OutboxEventDoc.find({
    "status": "PERMANENTLY_FAILED",
    "updated_at": {"$lt": cutoff_date}
}).delete()

print(f"清理了 {result.deleted_count} 个永久失败的旧事件")
```

**2. 手动重试失败事件：**
```python
# 手动重试特定失败事件（通过更新状态实现）
from app.shared.integration.outbox_models import OutboxEventDoc

event = await OutboxEventDoc.find_one({"event_id": event_id})
if event and event.status == "FAILED":
    event.status = "PENDING"
    event.next_retry_at = None
    event.retry_count = 0  # 重置重试次数
    await event.save()
    print(f"已重置事件 {event_id} 的状态，可以重试")
```

**3. 批量重试：**
```python
# 批量重试最近1小时的失败事件
from datetime import timedelta
from app.shared.integration.outbox_models import OutboxEventDoc

one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
failed_events = await OutboxEventDoc.find({
    "status": "FAILED",
    "updated_at": {"$gte": one_hour_ago}
}).to_list()

for event in failed_events:
    event.status = "PENDING"
    event.next_retry_at = None
    await event.save()

print(f"批量重置了 {len(failed_events)} 个失败事件的状态")
```

---

## 🛠️ 最佳实践

### 1. 事件设计原则

**幂等性 (Idempotency)：**
```python
# 使用唯一的事件ID确保幂等性
event_id = f"{aggregate_type}_{aggregate_id}_{int(time.time())}"
```

**事件内容最小化：**
```python
# 只包含必要的信息，避免大 payload
payload = {
    "task_id": task.task_id,
    "status": "dispatched",
    "dispatched_at": datetime.now(timezone.utc).isoformat()
}
```

### 2. 性能优化

**批量处理：**
```python
# 配置合理的批量大小
OUTBOX_BATCH_SIZE = 50  # 根据系统负载调整
```

**并发控制：**
```python
# 限制并发处理数量
MAX_CONCURRENT_WORKERS = 5
```

**数据库优化：**
```python
# 确保合适的索引
IndexModel([("status", ASCENDING), ("created_at", ASCENDING)])
```

**分步执行优化（DML V4特定）：**
```python
# 在创建Outbox事件前添加额外的验证
async def create_business_data_and_outbox():
    from app.modules.execution.repository.models import ExecutionTaskDoc
    from app.shared.integration.outbox_service import OutboxService
    
    outbox_service = OutboxService()
    task_data = {}  # 实际使用时传入真实的任务数据
    
    try:
        # 1. 创建业务数据 (Beanie使用构造函数然后insert)
        task_doc = ExecutionTaskDoc(**task_data)
        await task_doc.insert()
        
        # 2. 验证业务数据创建成功
        verify_task = await ExecutionTaskDoc.find_one({"task_id": task_doc.task_id})
        if not verify_task:
            raise Exception("Business data creation failed")
        
        # 3. 创建Outbox事件
        outbox_event = await outbox_service.create_execution_task_event(...)
        
        # 4. 验证Outbox事件创建成功
        if not outbox_event:
            # 记录缺失的Outbox事件以便后续处理
            print(f"⚠️  Task {task_doc.task_id} missing outbox event!")
            raise Exception("Outbox event creation failed")
            
    except Exception as e:
        # 清理已创建的业务数据（如需要）
        if 'task_doc' in locals():
            await task_doc.delete()
        raise
```

### 3. 错误处理

**外部系统异常处理：**
```python
async def _publish_to_external_system(self, event):
    try:
        # 发布逻辑
        await kafka_publisher.publish(event.topic, event.payload)
    except KafkaConnectionError:
        # 网络错误，可以重试
        raise
    except KafkaMessageTooLargeError:
        # 消息过大，标记为永久失败
        await self._mark_permanently_failed(event, "Message too large")
```

### 4. 测试策略

**单元测试：**
```python
@pytest.mark.asyncio
async def test_outbox_event_creation():
    """测试Outbox事件创建"""
    from app.shared.integration.outbox_service import OutboxService
    from app.shared.integration.outbox_models import OutboxEventDoc
    
    outbox_service = OutboxService()
    
    # 模拟创建执行任务事件
    event = await outbox_service.create_execution_task_event(
        task_id="TEST-001",
        external_task_id="EXT-TEST-001", 
        kafka_task_data={"test": "data"},
        created_by="test_user"
    )
    
    # 验证事件创建成功
    assert event.status == "PENDING"
    assert event.retry_count == 0
    assert event.event_type == "execution_task_dispatched"
```

**集成测试：**
```python
@pytest.mark.asyncio
async def test_outbox_workflow():
    """测试完整的Outbox工作流"""
    # 1. 创建业务数据和Outbox事件
    # 2. 验证事务一致性
    # 3. 验证Worker处理
    # 4. 验证外部系统接收
```

---

## 🔍 故障排查

### 常见问题

**1. OutboxWorker不启动**
```bash
# 检查基础设施初始化
python -c "from app.shared.infrastructure import get_infrastructure_registry; print('OK')"
```

**2. 事件处理积压**
```bash
# 检查待处理事件数量
python -c "
import asyncio
from app.shared.integration.outbox_models import OutboxEventDoc

async def main():
    count = await OutboxEventDoc.find({'status': 'PENDING'}).count()
    print(f'Pending events: {count}')
asyncio.run(main())
"
```

**3. 外部系统连接失败**
```bash
# 检查Kafka连接 (方法名可能需要根据实际实现调整)
python -c "
from app.shared.infrastructure import get_infrastructure_registry
registry = get_infrastructure_registry()
try:
    manager = registry.get_kafka_manager()
    print('Kafka manager:', type(manager).__name__)
    # 实际检查可能需要调用特定方法
except Exception as e:
    print(f'Kafka manager error: {e}')
"
```

**4. 数据一致性异常（DML V4特定问题）**
```bash
# 检查业务数据与Outbox事件不匹配的情况
python -c "
import asyncio
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.shared.integration.outbox_models import OutboxEventDoc
from app.shared.integration.outbox_service import OutboxService

async def check_consistency():
    # 查找存在业务数据但缺少Outbox事件的任务
    tasks = await ExecutionTaskDoc.find({'dispatch_status': 'CREATED'}).to_list()
    
    for task in tasks:
        event_count = await OutboxEventDoc.find({
            'aggregate_id': task.task_id,
            'aggregate_type': 'ExecutionTask'
        }).count()
        
        if event_count == 0:
            print(f'⚠️  Task {task.task_id} missing outbox event!')
            # 手动创建缺失的Outbox事件的代码示例：
            # outbox_service = OutboxService()
            # await outbox_service.create_execution_task_event(
            #     task_id=task.task_id,
            #     external_task_id=task.external_task_id,
            #     kafka_task_data=task.request_payload,
            #     created_by=task.created_by
            # )

asyncio.run(check_consistency())
"
```

**5. 事务性异常排查**
由于当前实现为分步执行，需要特别关注：
- 业务数据创建成功但Outbox事件创建失败的情况
- MongoDB连接异常导致的操作中断
- 并发操作导致的数据竞争问题

### 日志分析

**关键日志模式：**
```
# 成功处理
INFO: OutboxWorker: Processed 25 events, 24 successful, 1 failed

# 失败处理
WARNING: OutboxWorker: Event evt_123 failed, retry 2/5, next retry in 4s

# 重试成功
INFO: OutboxWorker: Event evt_123 succeeded after 2 retries

# 永久失败
ERROR: OutboxWorker: Event evt_123 permanently failed after 5 retries
```

---

## 📚 相关文档

- [Phase 5 最终报告](../../../../PHASE5_FINAL_REPORT.md) - 发件箱模式实现详情
- [DML V4 重构最终报告](../../../../DMLV4_BACKEND_REFACTOR_FINAL_REPORT.md) - 完整重构报告
- [AI 重构计划](../../../../AI_REFACTOR_PLAN.md) - 重构计划文档

---

## ⚠️ 生产环境特别注意事项（DML V4当前实现）

### 数据一致性风险

**当前分步实现的问题：**
- 业务数据和Outbox事件分步创建，**无事务保证**
- 极小概率出现：业务数据创建成功，但Outbox事件创建失败
- 需要依赖最终一致性和完善的监控机制

**风险场景示例：**
```python
# 问题场景：
1. ExecutionTaskDoc创建成功 ✓
2. OutboxEventDoc创建失败 ✗
3. 结果：业务系统显示任务已创建，但Kafka未收到消息
```

### 必要的监控措施

**1. 数据一致性检查脚本：**
```python
# 检查业务数据与Outbox事件匹配情况
async def check_data_consistency():
    tasks = await ExecutionTaskDoc.find({'dispatch_status': 'CREATED'}).to_list()
    
    for task in tasks:
        event_count = await OutboxEventDoc.find({
            'aggregate_id': task.task_id,
            'aggregate_type': 'ExecutionTask'
        }).count()
        
        if event_count == 0:
            print(f'⚠️  Task {task.task_id} missing outbox event!')
            # 建议：手动创建缺失的Outbox事件
```

**2. 积压监控：**
```python
# 设置合理的告警阈值
PENDING_EVENTS_ALERT_THRESHOLD = 100  # 待处理事件超过100个告警
FAILED_EVENTS_ALERT_THRESHOLD = 50   # 失败事件超过50个告警
```

### 建议的改进路径

**阶段1：完善监控（立即实施）**
- 实现业务数据与Outbox事件的匹配检查
- 设置积压告警和自动恢复机制
- 增加详细的日志记录

**阶段2：实现MongoDB事务（中期规划）**
```python
# 目标：实现真正的原子性操作
async def transactional_implementation():
    from pymongo import AsyncMongoClient
    from app.modules.execution.repository.models import ExecutionTaskDoc
    from app.shared.integration.outbox_service import OutboxService
    
    client = AsyncMongoClient()  # 或使用现有的客户端
    outbox_service = OutboxService()
    data = {}  # 实际使用时传入真实数据
    
    async with client.start_session() as session:
        async with session.start_transaction():
            # 业务数据创建 (Beanie风格)
            task = ExecutionTaskDoc(**data)
            await task.insert(session=session)
            
            # Outbox事件创建（同一事务）
            # 注意：OutboxService的方法可能需要添加session参数
            event = await outbox_service.create_execution_task_event(
                task_id=task.task_id,
                external_task_id=task.external_task_id,
                kafka_task_data=task.request_payload,
                created_by=task.created_by,
                session=session  # 如果OutboxService支持的话
            )
            
            # 提交事务
            await session.commit_transaction()
```

**阶段3：渐进式迁移策略**
- 先添加事务性包装（可选操作）
- 灰度发布和A/B测试
- 监控数据一致性指标
- 最终移除分步实现

### 生产部署建议

**1. 监控告警配置：**
- Outbox事件积压 > 1000：告警
- 失败事件占比 > 10%：告警  
- 处理延迟 > 5分钟：告警

**2. 自动恢复机制：**
- 定期执行数据一致性检查
- 自动创建缺失的Outbox事件
- 批量重试失败的事件

**3. 运维流程：**
- 每日执行一致性检查
- 及时处理积压事件
- 定期分析失败原因

---

## 🤝 贡献指南

**添加新事件类型：**
1. 在相应业务模块定义事件类型常量
2. 更新事件负载格式文档
3. 添加相应的测试用例
4. 更新监控配置

**性能优化建议：**
1. 分析批量处理效率
2. 优化数据库查询
3. 改进重试策略
4. 增加监控指标

---

*最后更新：2026-03-09*