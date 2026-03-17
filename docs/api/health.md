# 系统健康检查 API

## 概述

当前健康检查接口只提供基础可用性信号，不提供详细组件诊断信息。

**基础路径**：`/health`

## 当前已实现接口

### `GET /health`

- 用途：基础健康检查
- 认证：无需认证

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "healthy",
    "message": "Service is running"
  }
}
```

### `GET /health/ready`

- 用途：就绪检查
- 认证：无需认证

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "ready",
    "message": "Service is ready to accept requests"
  }
}
```

### `GET /health/live`

- 用途：存活检查
- 认证：无需认证

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "alive",
    "message": "Service is alive"
  }
}
```

## 说明

- 当前未实现 `/api/v1/health/detailed`、`/api/v1/health/components` 等扩展接口。
- 如果后续新增数据库、缓存、依赖服务探测，应新增专门章节，并与实际代码同步。
