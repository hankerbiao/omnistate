# Execution 状态与流转

状态常量定义在 `app/modules/execution/application/constants.py`，事件到状态的映射在 `app/modules/execution/domain/status_rules.py`。

## 任务级状态

### schedule_status（调度）

| 值 | 含义 |
|----|------|
| `PENDING` | 定时任务未到 `planned_at` |
| `READY` | 已到点，准备下发 |
| `TRIGGERED` | 已触发过下发流程 |

### dispatch_status（下发）

| 值 | 含义 |
|----|------|
| `PENDING` | 尚未下发 |
| `DISPATCHING` | 下发中（预留） |
| `DISPATCHED` | 当前 case 已成功投递到通道 |
| `DISPATCH_FAILED` | 下发失败 |
| `COMPLETED` | 全部 case 流程结束后的下发态 |

### consume_status（消费）

| 值 | 含义 |
|----|------|
| `PENDING` | 尚未收到执行端事件 |
| `CONSUMED` | 已收到并聚合至少一条事件 |

### overall_status（对外主状态）

| 值 | 含义 |
|----|------|
| `QUEUED` | 已下发，等待执行端开始 |
| `RUNNING` | 执行中（收到 collection/case 相关 phase） |
| `PASSED` | 全部完成且无失败 case |
| `FAILED` | 失败或下发/推进失败 |
| `SKIPPED` / `CANCELLED` / `TIMEOUT` | 其它终态 |

任务在 `task_finish` 或 `finished_cases >= total_cases` 时写入 `finished_at` 并设置 `PASSED`/`FAILED`。

## Case 级状态

| 值 | 含义 |
|----|------|
| `QUEUED` | 已创建，等待执行 |
| `RUNNING` | 收到 `case_start` 或等价事件 |
| `PASSED` / `FAILED` / `SKIPPED` | 终态（`FINAL_CASE_STATUSES`） |

`resolve_case_status()` 根据 `event_type`、`phase`、`event_status`、`failed_cases` 计算。

## 自动推进（核心）

`ExecutionProgressCoordinator.advance_after_case_finish()` 仅在**同时满足**以下条件时推进：

1. `event_type == "progress"` 且 `phase == "case_finish"`
2. `case_doc` 存在且 `resolved_case_status` ∈ `{PASSED, FAILED, SKIPPED}`
3. `event.case_id == task_doc.current_case_id`（防止乱序事件误推进）

分支：

- **最后一条 case**：清空 `current_case_id`，设置 `overall_status`，`dispatch_status` → `COMPLETED`（若未失败）
- **还有下一条**：`build_task_dispatch_command(task_doc, next_index)` → `dispatch_existing_task`

推进失败会将 `overall_status` 置为 `FAILED` 并记录 `dispatch_error`。

## 事件 ingest 主流程

`ExecutionEventIngestService.ingest_event()`：

1. 校验并解析 `TestEvent`
2. 按 `event_id` 查重 → 重复则跳过
3. 查 `ExecutionTaskDoc` → 不存在则归档并返回 false
4. 插入 `ExecutionEventDoc`
5. 更新 `ExecutionTaskCaseDoc`（若存在）
6. 聚合 `ExecutionTaskDoc`
7. 调用 `advance_after_case_finish`

## 典型时间线（单任务 2 条 case）

```
task.create          → 创建 ET-xxx，case_count=2
task.dispatch        → 下发 case[0]
event.ingest         → case_start / assert / case_finish
case.update          → case[0] → PASSED
task.advance         → 决定推进
task.dispatch        → 下发 case[1]
...
task.complete        → 最后一条 case_finish，overall_status=PASSED
```

可在 `execution_biz_logs` 或 `logs/execution.log` 中按 `task_id` 查看上述 `node` 序列。
