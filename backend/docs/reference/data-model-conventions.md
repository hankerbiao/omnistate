# 数据模型约定

## MongoDB / Beanie

- 文档模型统一使用 Beanie
- 常见模型在 `app/modules/*/repository/models`

## 软删除

- 业务文档普遍使用 `is_deleted`
- 查询时需要显式考虑未删除条件

## ID 约定

- 业务 ID 和 Mongo 文档 `_id` 分离
- 对外更多使用业务 ID，如 `req_id`、`case_id`、`task_id`

## 索引

- 索引应跟随文档模型定义
- 不要把索引逻辑散落到运行时代码
