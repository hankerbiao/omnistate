# ADR: Test Specs 读写依赖拆分

日期：2026-04-02

## 背景

`test_specs` 路由此前直接依赖：

- `RequirementService` / `TestCaseService`
- workflow facade / 兼容 adapter

导致路由层既知道 workflow facade，又直接绑定胖 service，依赖关系过宽。

## 决策

做两项收口：

1. 增加 `RequirementQueryService` / `TestCaseQueryService`，把读侧依赖从胖 service 外提
2. 新增 `WorkflowServicesAdapter` 和 `api/dependencies.py`，路由层统一依赖 workflow query/mutation service，不再直连 workflow facade

同时删除 `TestSpecsWorkflowProjectionHook.after_transition()` 空实现，只保留 delete 相关 side effect。

## 结果

- `test_specs` 路由不再直接依赖 workflow facade
- query / command 依赖更清晰
- workflow projection hook 的语义和实现保持一致

## 放弃方案

- 保留现有 wiring，只在路由里继续 new workflow facade
- 保留空 `after_transition` 作为未来占位符
