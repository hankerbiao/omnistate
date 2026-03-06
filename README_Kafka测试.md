# DMLv4 Kafka 集成测试指南

## 🎯 测试目的

验证 DMLv4 系统的任务下发流程是否正确向 Kafka 发送消息。

## 📋 测试流程

### 1. 准备工作

#### 启动后端服务
```bash
# 在 backend 目录下启动
cd backend
python init_mongodb.py              # 初始化数据库
python scripts/init_rbac.py         # 初始化 RBAC
python scripts/create_user.py       # 创建测试用户
python -m app.main                  # 启动后端服务（端口 8000）
```

#### 检查 Kafka 服务
确保 Kafka 服务正常运行（默认地址: 10.17.154.252:9092）

### 2. 运行测试脚本

#### 方式一：完整测试（推荐）
```bash
# 在项目根目录执行
python test_kafka_integration.py
```

#### 方式二：自定义配置
```bash
# 设置环境变量
export BACKEND_URL=http://localhost:8000
export KAFKA_BOOTSTRAP_SERVERS=10.17.154.252:9092
export TEST_TOKEN=your_jwt_token_here

# 运行测试
python test_kafka_integration.py
```

### 3. 测试步骤说明

测试脚本会执行以下步骤：

1. **检查后端服务健康状态** - 验证 FastAPI 服务是否运行
2. **获取认证令牌** - 登录获取 JWT token
3. **启动 Kafka 监控器** - 创建 Kafka 消费者监听消息
4. **创建执行任务** - 通过 API 下发测试任务
5. **监控 Kafka 消息** - 实时查看是否有消息到达
6. **查询任务状态** - 验证任务是否正确创建

## 📊 预期结果

### 成功标志

✅ **后端健康检查通过**
```
✓ 后端服务运行正常
```

✅ **任务创建成功**
```
✓ 任务创建成功
  任务ID: ET-2026-000001
  外部任务ID: EXT-ET-2026-000001
  下发状态: DISPATCHED
  任务状态: QUEUED
  用例数量: 3
```

✅ **Kafka 收到消息**
```
✓✓✓ 找到目标任务消息！
主题: dmlv4.tasks
任务ID: ET-2026-000001
任务类型: execution_task
消息来源: dmlv4-execution-api
优先级: 1

任务数据:
{
  "task_id": "ET-2026-000001",
  "external_task_id": "EXT-ET-2026-000001",
  "framework": "pytest",
  "trigger_source": "api_test",
  "cases": [
    {"case_id": "TC001"},
    {"case_id": "TC002"},
    {"case_id": "TC003"}
  ],
  "created_by": "admin",
  "created_at": "2026-03-06T16:30:00Z"
}
```

### 失败排查

❌ **认证失败**
```
✗ 无法获取认证令牌
```
**解决方案:**
- 运行 `python scripts/create_user.py` 创建测试用户
- 或设置 `TEST_TOKEN` 环境变量

❌ **后端服务不可用**
```
✗ 无法连接到后端服务
```
**解决方案:**
- 检查后端是否启动: `curl http://localhost:8000/health`
- 检查端口是否正确（默认 8000）

❌ **Kafka 连接失败**
```
启动 Kafka 监控器失败
```
**解决方案:**
- 检查 Kafka 服务是否运行
- 验证 Kafka 地址和端口
- 检查网络连通性

❌ **未收到 Kafka 消息**
```
⚠ 在 30 秒内未收到任务消息
```
**可能原因:**
1. Kafka 配置不正确
2. 后端未正确发送消息到 Kafka
3. 消费者组偏移量问题
4. 网络连接问题

**解决方案:**
- 检查后端日志中是否有 Kafka 相关错误
- 验证 Kafka 主题是否存在
- 检查消费者组是否正常

## 🔧 常见问题

### Q: 测试用例 ID 不存在怎么办？
A: 修改 `test_kafka_integration.py` 中的 `TEST_CASES` 变量，使用数据库中实际存在的用例 ID。

### Q: 如何查看 Kafka 主题列表？
A: 使用 Kafka 命令行工具：
```bash
# 连接 Kafka
kafka-topics.sh --bootstrap-server 10.17.154.252:9092 --list

# 查看主题详情
kafka-topics.sh --bootstrap-server 10.17.154.252:9092 --describe --topic dmlv4.tasks
```

### Q: 如何实时查看 Kafka 消息？
A: 使用 Kafka 控制台消费者：
```bash
# 监听任务主题
kafka-console-consumer.sh --bootstrap-server 10.17.154.252:9092 --topic dmlv4.tasks --from-beginning

# 监听结果主题
kafka-console-consumer.sh --bootstrap-server 10.17.154.252:9092 --topic dmlv4.results --from-beginning
```

### Q: 如何检查消息格式是否正确？
A: 运行测试脚本后，Kafka 消息会打印在控制台，格式如下：
```json
{
  "task_id": "ET-2026-000001",
  "task_type": "execution_task",
  "task_data": {
    "task_id": "ET-2026-000001",
    "external_task_id": "EXT-ET-2026-000001",
    "framework": "pytest",
    "cases": [...]
  },
  "source": "dmlv4-execution-api",
  "priority": 1,
  "create_time": "2026-03-06T16:30:00Z"
}
```

## 📝 测试日志

测试脚本会在当前目录生成 `kafka_test.log` 文件，记录详细的测试过程。

查看日志：
```bash
tail -f kafka_test.log
```

## 🚀 进阶测试

### 测试不同框架
修改测试脚本中的 `framework` 参数：
- `"pytest"` - Pytest 框架
- `"jtest"` - JTest 框架
- `"custom"` - 自定义框架

### 测试批量任务
修改 `TEST_CASES` 数组，增加更多用例 ID。

### 测试并发任务
多次运行测试脚本，验证 Kafka 是否能正确处理并发消息。

## 📚 相关文档

- [Kafka 消息管理模块文档](../backend/app/shared/kafka/README.md)
- [执行模块 API 文档](../backend/docs/后端接口说明.md)
- [系统架构说明](../docs/项目架构规范.md)

---

**注意**: 本测试仅验证任务是否正确发送到 Kafka，不代表外部测试框架能够正确消费和处理消息。