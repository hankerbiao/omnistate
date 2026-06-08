# 手工测试执行路线评审

> 评审日期：2026-06-08  
> 范围：TestHub LAB 前端 `TestExecutionPlan` / `MyTasksPage` / `PlanTask` / `ResultBackfillModal` 与后端 execution、workflow 模块关系

## 结论摘要

**推荐：保留主干路线，做模型收敛与后端落地（调整，非推翻）。**

执行计划（Plan）作为「批次编排层」、WorkItem TEST_CASE 作为「资产生命周期层」、ExecutionTask 作为「自动化运行层」的三层分离在领域上是合理的。当前主要问题不是路线选错，而是 **PlanTask/结果尚未入模**、**双入口操作计划**、**手工结果未接入 lineage**，以及 **下发 UI/状态枚举重复**。

## 1. 路线合理性（产品/领域模型）

| 层次 | 职责 | 现状 |
|------|------|------|
| WorkItem `TEST_CASE` | 用例编写/评审（DRAFT→…→DONE） | 有后端 workflow |
| Execution Plan | Sprint 级批次：选人、排期、混合 manual+auto | 前端 Mock |
| `PlanTask` | 计划内单条用例的执行待办 | 前端 Mock |
| `ExecutionTask` | Agent 串行/调度执行 auto case | 有完整后端 |

手工执行本质是 **「人对某次计划内运行负责并回填结果」**，与「用例文档是否评审通过」、与「Agent 跑脚本」是不同关注点。单独走 Plan → PlanTask → ResultBackfill **方向正确**。

缺口：计划激活后应服务端物化 `PlanTask`；手工 `PlanTaskResult` 应映射为 lineage 可消费的 `case_result`（或等价 `ManualRunResult`），否则追溯链断裂。

## 2. 效率评估

### 对测试工程师

- ✅ MyTasks 统一收件箱（工作流 + 计划任务）符合习惯
- ✅ `ResultBackfillModal` 字段完整（结论/环境/实际/缺陷/附件）
- ⚠️ `TestExecutionPlan` 看板可直接改状态，与「执行人回填」双入口易混乱
- ⚠️ `PlanTaskTable` 行点击一律打开回填弹窗（含 auto 行）
- ⚠️ 无 demo 任务时把全员任务改派给当前用户，演示易误导

### 对开发维护

- ⚠️ `TestExecutionPlan` 内联下发弹窗与 `SingleDispatchModal` 重复，且均未接 `api.dispatchTask`
- ⚠️ 状态枚举两套：`pending/running/done/fail` vs `QUEUED/RUNNING/PASSED/FAILED`
- ⚠️ `testPlan.ts` 中 `TestPlanProject/PlanPhase` 与 `TestExecutionPlan` Mock 模型并行，未来易分裂
- ⚠️ 全 Mock 导致 Plan 与 Execution 无法在同一任务列表/血缘图聚合

## 3. 与自动化线、工作流线的关系

```
需求/用例资产 ──WorkItem(TEST_CASE)──► 编写与评审（与执行解耦）
                    │
                    ▼
执行计划 ──PlanTask(manual)──► ResultBackfill ──?──► case_result
         └──PlanTask(auto)───► dispatchTask ──► ExecutionTask ──► case_result
```

- **与自动化线**：auto 分支应对齐 `TaskList` / `dispatchTask` / `execution_task_cases`；当前 MyTasks 下发为 Mock，与 `TestExecutionPlan` 下发 UI 重复。
- **与工作流线**：`MyTasksPage` 已分区展示，概念清晰；但 `TYPE_LABELS.PLAN_TASK` 未走 `listMyWorkItems`，计划待办是第二套数据源。
- **冗余点**：计划页 + 我的任务页均可改状态/下发；应用角色区分（计划负责人 vs 执行人）。

## 4. 风险与反模式

1. **双写状态**：计划看板手改状态 vs 执行人回填，进度与审计不一致  
2. **手工结果孤岛**：`PlanTaskResult` 仅存前端 state，失效分析/血缘/看板无法统计  
3. **无准入校验**：计划可纳入未 DONE 的用例，执行与资产状态脱节  
4. **演示逻辑渗透生产路径**：`displayPlanTasks` fallback 改 assignee  
5. **后端落地时模型漂移**：若 PlanTask 与 ExecutionTask 完全独立建表，报表需双份 JOIN  

## 5. 替代路线对比

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A. 手工走 WorkItem | 在 TEST_CASE 工作流加执行/回填状态 | 复用 workflow、统一 MyTasks API | 混淆资产与运行；一次计划多次执行难表达 |
| B. 手工也生成 ExecutionTask | `execution_mode=manual`，人工作为「执行端」 | 统一任务表与 lineage | 强行走 Agent/事件模型；表单回填与 Kafka 事件不匹配 |
| **C. 当前路线（Plan→PlanTask→回填）** | 编排层 + 轻量执行待办 | 语义清晰、UX 贴合手工 | 需新后端模块 + 结果入血缘 |
| D. 统一 Run 实体 | Plan 下挂 RunInstance(manual\|auto) → 统一 case_result | 长期最利于追溯与报表 | 初期设计成本高 |

**推荐：C 为主干，吸收 D 的结果模型**——Plan 编排不变，手工/自动完成后均写入同一 `case_result`（带来源 `plan_id` / `run_type`）。

## 6. 优化建议（5 条）

1. **计划激活时服务端生成 PlanTask**，`GET /my-tasks` 合并 workflow 与 plan 待办，去掉前端 Mock 与 demo 改派。  
2. **收敛操作入口**：计划页只读/管理视角；执行人仅在 MyTasks 回填或下发；移除看板快捷改状态或限管理员。  
3. **手工结果落库并挂 lineage**：`PlanTaskResult` → `case_result`（`run_type=manual`，关联 `plan_id`、`case_id`）。  
4. **auto 单一路径**：删除 `TestExecutionPlan` 内联下发，统一 `SingleDispatchModal`/`BatchDispatchModal` 调 `api.dispatchTask`，并写 `plan_id` 到 `request_payload`。  
5. **统一类型与状态**：对齐 `testPlan.ts` 与 `TestExecutionPlan`；对外暴露与 execution 模块可映射的状态机，避免两套枚举。
