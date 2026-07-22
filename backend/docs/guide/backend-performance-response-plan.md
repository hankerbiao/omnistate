# 后端接口响应速度优化方案

## 目标

本方案用于逐步降低 DML V4 后端接口响应时间，并优先建立可观测基线，避免在没有证据的情况下盲目扩容或重构。

建议目标：

- 普通列表/详情接口 P95 <= 300ms
- 创建、修改、状态流转接口 P95 <= 500ms
- 搜索、统计、血缘、AI 等复杂接口 P95 <= 1s
- 5xx 错误率 <= 0.1%
- 所有列表接口设置最大分页数量

## 关键判断

当前后端是 FastAPI + Beanie/MongoDB + Redis + Kafka/RabbitMQ。最常见的响应慢来源通常不是 Python 框架本身，而是：

- MongoDB 慢查询、复合索引不足或索引未同步
- N+1 查询，例如循环内按用户、项目、用例逐条查库
- 接口内串行 I/O，本可并发的独立查询被顺序等待
- 每个请求重复加载用户角色、权限、导航或系统配置
- Dashboard、全局搜索、Lineage、AI 分析等重型同步计算
- 大响应体的 Pydantic 序列化和 DEBUG 日志输出

## 实施优先级

### P0：观测和慢请求追踪

周期：1-2 天。

目标是拿到接口 P50/P95/P99、错误率、慢请求排行、DB 查询耗时和查询次数基线。

已落地的 P0 能力：

- `RequestLoggingMiddleware` 在每个请求完成时记录进程内 HTTP 指标。
- 慢请求超过 `logging.slow_request_threshold_ms` 后输出 `event=http_slow_request` 的 WARNING 结构化日志。
- `/health/metrics` 返回按 `method + 路由模板 + status_class` 聚合的 count、error_count、avg、p50、p95、p99、max。
- 健康检查和指标端点保持静默，避免监控噪音污染慢请求排行。

建议补充的 P0 操作：

- 对高频接口做压测或回放，记录基线。
- 生产环境关闭完整请求/响应体 DEBUG 日志。
- 检查 `SKIP_INDEX_SYNC`，确认 MongoDB 索引确实已创建。
- 针对慢接口用 MongoDB `explain("executionStats")` 检查 `COLLSCAN`、`totalDocsExamined / nReturned` 和内存排序。

## P1：查询和接口层优化

周期：3-5 天。

优先动作：

- 为真实查询模式补复合索引，例如 `project_id + is_deleted + status + updated_at`。
- 消除 N+1 查询，把循环内 DB 读取改成批量 `$in` 查询和内存映射。
- 列表接口只返回页面必要字段，详情接口再返回完整字段。
- 串行独立 I/O 改为受控并发，例如 `asyncio.gather` 或小并发池。
- 权限、角色、导航、工作流配置、系统配置接入 Redis 或进程内短 TTL 缓存。
- 列表接口统一最大分页限制，避免一次请求拉取过多数据。

## P2：重型接口异步化和预计算

周期：1-2 周。

适用模块：Dashboard、全局搜索、Lineage、AI 分析、执行计划统计。

优先动作：

- Dashboard 统计改成预聚合或定时刷新。
- 全局搜索增加查询范围、分页和超时限制，必要时接专用搜索索引。
- Lineage 限制图深度和节点数量，常用关系做缓存。
- AI 分析改为提交任务后异步执行，前端轮询或订阅状态。
- 对跨系统写入使用 Outbox，降低同步链路阻塞。
- 根据实测调优 Uvicorn worker、MongoDB 连接池、Redis 连接池和 Kafka/RabbitMQ 参数。

## 重点观察接口

- 我的任务列表
- 需求列表、测试用例列表
- 执行计划详情和计划项
- 工作流状态流转
- Dashboard
- 全局搜索
- Lineage 图谱
- 用户权限和导航

## 复合索引原则

复合索引必须基于真实查询和 `explain("executionStats")` 决定。若接口过滤条件是 `project_id + is_deleted + status`，并按 `updated_at` 倒序排序，候选索引可以是：

```javascript
{
  project_id: 1,
  is_deleted: 1,
  status: 1,
  updated_at: -1
}
```

重点关注：

- 是否出现 `COLLSCAN`
- `totalDocsExamined / nReturned` 是否过高
- 排序是否触发内存排序
- 索引字段顺序是否匹配过滤和排序模式

## 验收方式

每轮优化都应该记录优化前后：

- P50 / P95 / P99
- 请求量和错误率
- 慢请求日志条数
- 数据库查询次数和最慢查询
- 响应体大小
- 影响的接口和回归测试结果

只有当指标改善且错误率不升高时，才进入下一批优化。
