# 测试执行编排

本文档采用“双层结构”：

- 工程文档：严格描述当前代码实现、字段、状态和流程
- 演示说明：给出时序图、请求示例和联调场景，方便开发和排障

本文只描述当前仓库已经实现的 `execution` 模块能力。

## 1. 目标与范围

`execution` 模块当前采用“平台主导、单任务串行单 case 下发”的执行模型。

当前范围内的真实行为：

- 一个任务只执行一次
- 一个任务可包含多条自动化用例
- 平台每次只向执行端下发当前 1 条 case
- 当前 case 完成后，由平台决定是否自动推进下一条
- 平台只维护任务当前态和任务内每条 case 的当前态
- 不再提供历史轮次、`run_no`、`/runs` 查询和任务重试接口

## 2. 组件与职责

### 2.1 运行组件

当前执行链路由 3 类进程组成：

1. 主服务 `python -m app.main`
   负责提供 HTTP API、创建任务、查询任务、管理 agent
2. Kafka worker `python -m app.workers.kafka_worker_main`
   负责消费 `test-events`、更新任务状态、在串行模式下自动推进下一条 case
3. 执行代理 / 测试框架
   负责接收平台下发、执行 case，并向 Kafka `test-events` 回报事件

### 2.2 `kafka_worker_main.py` 的作用

`backend/app/workers/kafka_worker_main.py` 不是辅助脚本，而是执行主链路的一部分。

它当前负责：

- 初始化 MongoDB 和 Beanie 文档模型
- 校验 workflow 基础配置
- 初始化 Kafka producer，供后续自动推进下一条 case 使用
- 注册 execution Kafka topic handler
- 消费 `test-events` 和结果 topic
- 将 Kafka worker 自身注册为系统 agent，并持续发送心跳
- 在关闭时将 worker 标记为 `OFFLINE`

它不负责：

- 提供业务 HTTP API
- 替代 `app.main` 暴露前端调用入口
- 直接执行测试用例

### 2.3 启动约束

当 `EXECUTION_DISPATCH_MODE=kafka` 时：

- 主服务启动前必须先有 Kafka worker 在线
- 主服务会在启动前检查 worker 心跳
- worker 不在线时，主服务拒绝启动

说明：

- HTTP 下发只影响“任务如何送到 agent”
- 任务状态回报和串行推进仍然依赖 Kafka `test-events`

### 2.4 推荐启动顺序

Kafka 模式下建议固定按以下顺序启动：

1. MongoDB
2. Kafka
3. `python -m app.workers.kafka_worker_main`
4. `python -m app.main`
5. 执行代理或 `python scripts/mock_test_framework.py`

## 3. 数据模型

### 3.1 当前态模型

- `ExecutionTaskDoc`
  任务主表，保存任务身份、调度状态、下发状态、消费状态、整体状态、当前游标和聚合统计
- `ExecutionTaskCaseDoc`
  任务内 case 当前态表，保存顺序、当前状态、进度、断言结果、失败信息、最近事件和结果数据
- `ExecutionEventDoc`
  原始事件归档表，用于事件幂等和审计

### 3.2 已移除的历史能力

以下对象和对外接口已从当前实现移除：

- `ExecutionTaskRunDoc`
- `ExecutionTaskRunCaseDoc`
- `run_no`
- `/api/v1/execution/tasks/{task_id}/runs`
- `/api/v1/execution/tasks/{task_id}/runs/{run_no}`

## 4. 对外接口

### 4.1 Agent 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/execution/agents/register` | 无 | 注册或刷新执行代理 |
| POST | `/api/v1/execution/agents/{agent_id}/heartbeat` | 无 | 上报代理心跳 |
| GET | `/api/v1/execution/agents` | `execution_agents:read` | 查询代理列表 |
| GET | `/api/v1/execution/agents/{agent_id}` | `execution_agents:read` | 查询代理详情 |

HTTP 下发时，平台真正使用的是：

`agent.base_url + EXECUTION_AGENT_DISPATCH_PATH`

### 4.2 任务接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/execution/tasks/dispatch` | `execution_tasks:write` | 创建并下发任务 |
| DELETE | `/api/v1/execution/tasks/{task_id}` | `execution_tasks:write` | 逻辑删除任务 |
| POST | `/api/v1/execution/tasks/{task_id}/cancel` | `execution_tasks:write` | 取消未触发的定时任务 |
| POST | `/api/v1/execution/tasks/{task_id}/stop` | `execution_tasks:write` | 当前 case 完成后停止 |
| GET | `/api/v1/execution/tasks` | `execution_tasks:read` | 查询任务列表 |
| GET | `/api/v1/execution/tasks/{task_id}/status` | `execution_tasks:read` | 查询任务当前状态 |

### 4.3 已移除的旧接口

- `POST /api/v1/execution/tasks/{task_id}/consume-ack`
- `PUT /api/v1/execution/tasks/{task_id}/schedule`
- `POST /api/v1/execution/tasks/{task_id}/retry`
- 所有 `/runs` 相关接口
- 所有“执行端直接 HTTP 回调任务状态”的接口

## 5. 下发请求

### 5.1 字段责任划分

#### 前端必须提供

| 字段 | 层级 | 说明 |
|------|------|------|
| `framework` | 顶层 | 执行框架标识，例如 `pytest` |
| `dispatch_channel` | 顶层 | 下发通道，只允许 `KAFKA` 或 `HTTP` |
| `cases[].auto_case_id` | case | 自动化用例业务 ID，后端依赖它解析平台 `case_id` |
| `cases[].case_path` | case | 执行端识别的脚本路径 |
| `cases[].case_name` | case | 执行端展示名称 |

补充：

- 当 `dispatch_channel=HTTP` 时，`agent_id` 也属于前端必须提供字段
- 若前端要让用户填写动态配置，则 `cases[].config` 和 `cases[].parameters` 也应一并提交

#### 前端可提供，后端会校准或透传

| 字段 | 层级 | 当前规则 |
|------|------|----------|
| `agent_id` | 顶层 | HTTP 时必填；Kafka 时可选 |
| `trigger_source` | 顶层 | 前端可传，如 `web_ui` |
| `schedule_type` | 顶层 | 前端可选 `IMMEDIATE` 或 `SCHEDULED` |
| `planned_at` | 顶层 | 定时任务时由前端提供 |
| `category` | 顶层 | 前端可传，例如 `bmc` |
| `project_tag` | 顶层 | 前端可传，例如 `universal` |
| `common_parameters` | 顶层 | 前端可传任务公共参数 |
| `pytest_options` | 顶层 | 前端可传自定义 pytest 参数，后端会叠加默认值 |
| `timeout` | 顶层 | 前端可传任务超时时间 |
| `dut` | 顶层 | 前端可传被测对象快照 |
| `cases[].script_entity_id` | case | 前端可透传，但后端仍会按自动化用例重新解析和校准 |
| `cases[].config` | case | 前端根据 `param_spec` 收集用户填写值 |
| `cases[].parameters` | case | 前端可直接传执行参数；后端按当前值透传到 agent |

#### 后端默认补齐

| 字段 | 层级 | 默认值 / 规则 |
|------|------|---------------|
| `task_id` | 最终下发 payload | 后端生成，例如 `ET-2026-000022` |
| `external_task_id` | 平台内部任务记录 | 后端生成，例如 `EXT-ET-2026-000022` |
| `repo_url` | 顶层/最终下发 payload | `http://10.17.55.151:6600/litaiqing/bmc-case.git` |
| `branch` | 顶层/最终下发 payload | `master` |
| `pytest_options.log_debug` | 最终下发 payload | `false` |
| `pytest_options.kafka_servers` | 最终下发 payload | `10.17.154.252:9092` |
| `pytest_options.kafka_topic` | 最终下发 payload | `test-events` |
| `pytest_options.report_kafka` | 最终下发 payload | `true` |
| `pytest_options.maxfail` | 最终下发 payload | `"3"` |
| `pytest_options.task_id` | 最终下发 payload | 平台生成的 `task_id` |
| `created_at` | 最终下发 payload | 后端生成的 UTC 时间 |
| `cases[].case_id` | 最终下发 payload | 后端根据 `auto_case_id` 解析的平台手工测试用例编号 |

### 5.2 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `framework` | string | 是 | 执行框架标识，例如 `pytest` |
| `dispatch_channel` | string | 是 | `KAFKA` 或 `HTTP` |
| `agent_id` | string | HTTP 时必填 | 目标代理 ID |
| `trigger_source` | string | 否 | 触发来源，例如 `web_ui` |
| `schedule_type` | string | 否 | `IMMEDIATE` 或 `SCHEDULED` |
| `planned_at` | datetime | 否 | 定时任务计划时间 |
| `callback_url` | string | 否 | 预留字段，当前执行状态不依赖它 |
| `category` | string | 否 | 任务分类，例如 `bmc` |
| `project_tag` | string | 否 | 项目标识，例如 `universal` |
| `repo_url` | string | 否 | 仓库地址 |
| `branch` | string | 否 | 分支名 |
| `common_parameters` | object | 否 | 任务公共参数 |
| `pytest_options` | object | 否 | pytest 扩展参数 |
| `timeout` | int | 否 | 任务超时秒数 |
| `dut` | object | 否 | 被测对象快照 |
| `cases` | object[] | 是 | 按顺序执行的用例列表 |

### 5.3 `cases[]` 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `auto_case_id` | string | 是 | 自动化用例业务 ID |
| `script_entity_id` | string | 否 | 前端可透传；后端会按自动化用例重新校准 |
| `config` | object | 否 | 当前 case 的用户回填配置 |
| `case_path` | string | 是 | 执行端识别的 case 路径 |
| `case_name` | string | 是 | 执行端展示名称 |
| `parameters` | object | 否 | 当前 case 实际执行参数 |

说明：

- 前端会根据自动化用例 `param_spec` 动态渲染配置表单，用户填写后进入 `cases[].config`
- 后端会根据 `auto_case_id` 解析平台手工用例 `case_id`，并将其组装进真正下发给 agent 的 payload
- `script_entity_id` 不是前端必填字段，平台始终以后端解析结果为准

## 6. 演示说明：前端请求与最终下发

### 6.1 前端提交示例

```json
{
  "framework": "pytest",
  "dispatch_channel": "HTTP",
  "agent_id": "localhost.localdomain-12.28-93f8c286",
  "trigger_source": "web_ui",
  "schedule_type": "IMMEDIATE",
  "category": "bmc",
  "project_tag": "universal",
  "repo_url": "",
  "branch": "",
  "common_parameters": {},
  "pytest_options": {},
  "timeout": 300,
  "cases": [
    {
      "auto_case_id": "ATC-2026-00001",
      "script_entity_id": "tests/universal/suite/fan/001_basic_check/test_fan_basic.py",
      "config": {
        "target_ip": "10.10.10.100",
        "bmc_username": "admin",
        "bmc_password": "admin"
      },
      "case_path": "tests/universal/suite/fan/001_basic_check/test_fan_basic.py",
      "case_name": "suite-fan-001",
      "parameters": {
        "target_ip": "10.10.10.100",
        "bmc_username": "admin",
        "bmc_password": "admin"
      }
    }
  ]
}
```

### 6.2 最终发给 agent 的结构

无论选 Kafka 还是 HTTP，业务 payload 结构相同；差别只在发送通道。

```json
{
  "task_id": "ET-2026-000022",
  "category": "bmc",
  "project_tag": "universal",
  "repo_url": "http://10.17.55.151:6600/litaiqing/bmc-case.git",
  "branch": "master",
  "cases": [
    {
      "case_id": "TC-2026-00004",
      "case_path": "tests/universal/suite/fan/001_basic_check/test_fan_basic.py",
      "case_name": "suite-fan-001",
      "parameters": {
        "target_ip": "10.10.10.100",
        "bmc_username": "admin",
        "bmc_password": "admin"
      }
    }
  ],
  "common_parameters": {},
  "pytest_options": {
    "log_debug": false,
    "kafka_servers": "10.17.154.252:9092",
    "kafka_topic": "test-events",
    "report_kafka": true,
    "maxfail": "3",
    "task_id": "ET-2026-000022"
  },
  "timeout": 300,
  "created_at": "2026-03-20T08:11:50.129763+00:00"
}
```

说明：

- `case_id` 是平台手工测试用例编号，由后端根据 `auto_case_id` 解析得到
- `cases` 在最终外发结构里永远只包含当前这 1 条

### 6.3 字段对照表

| 最终下发字段 | 来源 |
|-------------|------|
| `task_id` | 后端生成 |
| `category` | 前端传入；未传则后端补空字符串 |
| `project_tag` | 前端传入；未传则后端补空字符串 |
| `repo_url` | 前端传入；为空时后端补默认仓库地址 |
| `branch` | 前端传入；为空时后端补 `master` |
| `cases[0].case_id` | 后端根据 `auto_case_id` 解析 |
| `cases[0].case_path` | 前端传入 |
| `cases[0].case_name` | 前端传入 |
| `cases[0].parameters` | 前端传入 |
| `common_parameters` | 前端传入；未传则后端补空对象 |
| `pytest_options.*` | 后端默认值 + 前端覆盖值 合并结果 |
| `timeout` | 前端传入；未传则后端补 `0` |
| `created_at` | 后端生成 |

## 7. Kafka 与 HTTP 通道

### 7.1 Kafka 下发

- 平台将标准化后的任务 payload 发送到 Kafka task topic
- 首条 case 由主服务发出
- 后续 case 通常由 Kafka worker 在消费到 `case_finish` 后继续发出

### 7.2 HTTP 下发

- 平台根据 `agent_id` 查询 `ExecutionAgentDoc`
- 目标地址为：`agent.base_url + EXECUTION_AGENT_DISPATCH_PATH`
- agent 必须满足：
  - 已注册
  - `status=ONLINE`
  - `base_url` 不为空

### 7.3 两种通道的共同点

| 特性 | 说明 |
|------|------|
| 发送的业务 payload 结构 | 一致 |
| 串行推进逻辑 | 一致 |
| 任务状态聚合逻辑 | 一致 |
| 执行结果回报 | 都仍然依赖 Kafka `test-events` |

### 7.4 为什么 HTTP 下发仍然需要 Kafka worker

即使任务选择 HTTP 下发，Kafka worker 仍然必须存在，因为它负责：

- 消费 `test-events`
- 串行推进下一条 case
- 最终收口任务状态

## 8. 串行业务全流程

### 8.1 工程流程

#### 阶段 1：创建任务

1. 前端调用 `POST /api/v1/execution/tasks/dispatch`
2. 后端在 `routes.py` 中生成：
   - `task_id`
   - `external_task_id`
3. 后端根据 `cases[].auto_case_id` 解析：
   - 平台手工测试用例 `case_id`
   - 自动化脚本定位信息
4. 后端构造 `DispatchExecutionTaskCommand`
5. 后端计算 `dedup_key`，检查是否存在未完成的重复任务
6. 后端创建：
   - `ExecutionTaskDoc`
   - 本任务下所有 `ExecutionTaskCaseDoc`

此时任务已经有完整的任务快照和 case 快照，但还没有开始执行全部 case。

#### 阶段 2：下发首条 case

1. 若任务是 `IMMEDIATE`，后端立即构建第 1 条 case 的下发命令
2. `ExecutionTaskDispatchMixin._dispatch_existing_task()` 负责真正下发
3. 平台只会把第 1 条 case 发给执行端，不会一次性把整批 case 全发出去
4. 下发成功后：
   - `ExecutionTaskDoc.current_case_id = 第 1 条 case_id`
   - `ExecutionTaskDoc.current_case_index = 0`
   - `ExecutionTaskDoc.dispatch_status = DISPATCHED`
   - `ExecutionTaskDoc.overall_status = QUEUED`
   - 对应 `ExecutionTaskCaseDoc.dispatch_status = DISPATCHED`

如果首条下发失败：

- 任务会直接进入失败态
- 当前不会继续尝试下一条 case

#### 阶段 3：执行端执行当前 case

1. 执行代理或 mock 测试框架收到单 case payload
2. 执行端开始执行当前 case
3. 执行端向 Kafka `test-events` 持续发送事件，典型顺序为：
   - `progress + phase=case_start`
   - 若干 `assert`
   - `progress + phase=case_finish`
   - 最后一条 case 结束后还可能发送 `progress + phase=task_finish`

注意：

- 平台当前真正依赖的是 `test-events`
- 结果 topic 只做日志记录，不驱动状态流转

#### 阶段 4：Kafka worker 消费事件并更新当前态

1. `kafka_worker_main.py` 消费 `test-events`
2. 进入 `ExecutionEventIngestService.ingest_event()`
3. 服务先按 `event_id` 做幂等检查
4. 然后归档原始事件到 `ExecutionEventDoc`
5. 若事件带 `case_id`，更新对应 `ExecutionTaskCaseDoc`
6. 同时调用 `_apply_task_aggregate()` 更新 `ExecutionTaskDoc` 当前聚合状态

这一阶段会更新的典型字段包括：

- 任务级：
  - `last_event_id`
  - `last_event_at`
  - `last_event_type`
  - `last_event_phase`
  - `consume_status`
  - `started_case_count`
  - `finished_case_count`
  - `failed_case_count`
  - `reported_case_count`
  - `progress_percent`
  - `overall_status`
- case 级：
  - `status`
  - `progress_percent`
  - `event_count`
  - `started_at`
  - `finished_at`
  - `failure_message`
  - `result_data`

#### 阶段 5：收到当前 case 完成事件后，自动决定是否推进下一条

平台不是收到任意事件都推进，而是只在满足下面条件时推进：

1. 当前事件是：
   - `event_type = progress`
   - `phase = case_finish`
2. 事件中的 `case_id` 必须等于任务当前游标指向的 `current_case_id`
3. 当前 case 必须已经进入终态
4. 任务本身不能已经是终态

命中后会进入 `_advance_task_after_case_finish()`，分 3 种情况：

##### 情况 A：还有下一条 case，且没有请求停止

1. Kafka worker 计算下一条 `dispatch_case_index`
2. 根据任务快照重建下一条 case 的 `DispatchExecutionTaskCommand`
3. 再次调用 `_dispatch_existing_task()`
4. 下一条 case 被下发到 Kafka 或 HTTP agent
5. 任务游标推进到下一条：
   - `current_case_id = 下一条 case_id`
   - `current_case_index = 下一条索引`

##### 情况 B：当前是最后一条 case

不会继续下发下一条，而是直接收口任务：

- 若整体没有失败：任务置为 `PASSED`
- 若存在失败：任务置为 `FAILED`
- `finished_at` 被写入
- `current_case_id` 清空
- `dispatch_status` 通常收口为 `COMPLETED`

##### 情况 C：用户请求“当前 case 后停止”

若任务 `stop_mode = STOP_AFTER_CURRENT_CASE`，则当前 case 完成后：

- 不再继续下一条
- 任务收口为 `STOPPED`
- `finished_at` 被写入
- `current_case_id` 清空
- 若当前 `dispatch_status` 不是 `DISPATCH_FAILED`，则收口为 `COMPLETED`

### 8.2 演示时序图

```text
前端/调用方
    |
    | POST /api/v1/execution/tasks/dispatch
    v
app.main / execution API
    |
    | 解析 auto_case_id -> case_id
    | 创建 ExecutionTaskDoc / ExecutionTaskCaseDoc
    | 下发第 1 条 case
    v
Kafka 或 HTTP
    |
    v
执行代理 / mock_test_framework
    |
    | 执行当前 case
    | 发送 case_start / case_finish / task_finish
    v
Kafka topic: test-events
    |
    v
kafka_worker_main.py
    |
    | ExecutionEventIngestService
    | 更新 ExecutionEventDoc
    | 更新 ExecutionTaskDoc / ExecutionTaskCaseDoc
    | 若还有下一条 case，则继续下发
    v
Kafka 或 HTTP
    |
    v
执行代理继续执行下一条
```

## 9. 状态说明

### 9.1 四类状态字段的职责

| 字段 | 作用 | 典型值 | 说明 |
|------|------|--------|------|
| `schedule_status` | 描述调度是否到触发阶段 | `PENDING`、`TRIGGERED`、`CANCELLED` | 只描述调度，不表达执行结果 |
| `dispatch_status` | 描述任务下发是否成功、是否已结束 | `PENDING`、`DISPATCHED`、`DISPATCH_FAILED`、`COMPLETED` | 关注“是否成功交给执行端” |
| `consume_status` | 描述是否已被事件链路消费 | `PENDING`、`CONSUMED` | 当前由 Kafka 事件消费侧推进 |
| `overall_status` | 描述任务整体执行状态 | `QUEUED`、`RUNNING`、`PASSED`、`FAILED`、`STOPPED`、`CANCELLED` | 这是前端最应关注的业务状态 |

### 9.2 任务整体状态流转

| 当前状态 | 触发条件 | 下一状态 | 说明 |
|------|------|------|------|
| `QUEUED` | 首条 case 已成功下发，尚未收到有效执行进度事件 | `RUNNING` | 任务已进入执行队列 |
| `QUEUED` | 首条下发失败 | `FAILED` | 下发失败时任务直接失败 |
| `RUNNING` | 收到当前 case 的 `case_start` 或执行中事件 | `RUNNING` | 保持运行中 |
| `RUNNING` | 当前 case 完成，且还有下一条 case | `RUNNING` | 平台自动推进下一条 |
| `RUNNING` | 最后一条 case 完成，且整体无失败 | `PASSED` | 正常收口 |
| `RUNNING` | 最后一条 case 完成，且存在失败 | `FAILED` | 失败收口 |
| `RUNNING` | 用户已请求 `STOP_AFTER_CURRENT_CASE`，且当前 case 完成 | `STOPPED` | 不再推进下一条 |

### 9.3 任务下发状态流转

| 当前状态 | 触发条件 | 下一状态 | 说明 |
|------|------|------|------|
| `PENDING` | 定时任务尚未触发 | `PENDING` | 任务已创建但还没开始下发 |
| `DISPATCHING` | 创建立即执行任务，准备下发首条 case | `DISPATCHED` | 首条下发成功 |
| `DISPATCHING` | 创建立即执行任务，但首条下发失败 | `DISPATCH_FAILED` | 首条下发失败 |
| `DISPATCHED` | 当前 case 完成且自动推进下一条成功 | `DISPATCHED` | 继续维持已下发状态 |
| `DISPATCHED` | 当前 case 完成，下一条下发失败 | `DISPATCH_FAILED` | 自动推进失败 |
| `DISPATCHED` | 最后一条 case 完成或 stop 收口 | `COMPLETED` | 整个任务的下发阶段结束 |

### 9.4 case 执行状态流转

| 当前状态 | 触发条件 | 下一状态 | 说明 |
|------|------|------|------|
| `QUEUED` | case 已被平台下发，尚未收到 `case_start` | `QUEUED` | 等待执行端真正开始 |
| `QUEUED` | 收到 `progress + phase=case_start` | `RUNNING` | 当前 case 开始执行 |
| `RUNNING` | 收到 `assert` 等中间事件 | `RUNNING` | 持续累计断言和进度 |
| `RUNNING` | 收到 `progress + phase=case_finish` 且结果成功 | `PASSED` | 当前 case 正常完成 |
| `RUNNING` | 收到 `progress + phase=case_finish` 且结果失败 | `FAILED` | 当前 case 失败 |
| `QUEUED` / `RUNNING` | 下发失败或执行失败 | `FAILED` | 当前 case 未成功交付或执行失败 |

### 9.5 case 下发状态流转

| 当前状态 | 触发条件 | 下一状态 | 说明 |
|------|------|------|------|
| `PENDING` | case 还未轮到当前游标 | `PENDING` | 只是任务内待执行项 |
| `PENDING` | 平台成功下发当前 case | `DISPATCHED` | 当前 case 已交给执行端 |
| `PENDING` | 平台尝试下发但失败 | `DISPATCH_FAILED` | 当前 case 未成功交付 |
| `DISPATCHED` | 当前 case 执行结束 | `DISPATCHED` | 当前实现保留最后一次成功下发状态 |

## 10. 查询与前端展示

### 10.1 任务列表接口

`GET /api/v1/execution/tasks` 返回任务列表，并包含 `cases` 当前执行摘要。

每条 case 当前态至少包含：

- `case_id`
- `auto_case_id`
- `title`
- `status`
- `progress_percent`
- `dispatch_status`
- `dispatch_attempts`
- `event_count`
- `failure_message`
- `started_at`
- `finished_at`
- `last_event_id`
- `last_event_at`
- `result_data`

### 10.2 前端当前展示

前端任务看板已支持展示：

- 任务当前状态和下发通道
- 每个 case 的当前执行状态、进度、下发状态、事件数
- `result_data` 中的断言、错误、数据摘要

## 11. 联调建议

### 11.1 Mock 框架

开发环境可使用：

```bash
cd backend
python scripts/mock_test_framework.py
```

该脚本当前支持：

- 注册 agent
- 定时发送 agent 心跳
- 消费 Kafka 任务
- 提供 HTTP 下发接收接口
- 按真实 `cases` 载荷串行执行 mock case
- 向 `test-events` 回报 `case_start / case_finish / task_finish`
- 打印详细调试日志

### 11.2 排查最常见问题

1. 前端选了 HTTP，但实际走 Kafka
   先看 `dispatch_channel` 请求体，再看后端 `task_dispatcher.py` 日志
2. 首条 case 执行完不继续下一条
   先确认 Kafka worker 是否在线，再确认 `test-events` 是否真的到达
3. 任务列表里看不到 case 细节
   先确认任务创建后是否已经生成 `ExecutionTaskCaseDoc`

## 12. 代码入口

- 任务创建与控制：`backend/app/modules/execution/application/execution_service.py`
- 任务快照与 case 解析：`backend/app/modules/execution/application/task_case_mixin.py`
- 下发命令重建与串行推进：`backend/app/modules/execution/application/task_dispatch_mixin.py`
- 任务查询：`backend/app/modules/execution/application/task_query_mixin.py`
- 事件消费与状态聚合：`backend/app/modules/execution/application/event_ingest_service.py`
- Kafka / HTTP 通道实现：`backend/app/modules/execution/service/task_dispatcher.py`
- Kafka worker 入口：`backend/app/workers/kafka_worker_main.py`
