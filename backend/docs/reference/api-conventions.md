# API 约定

## 统一前缀

所有业务 API 统一挂在 `/api/v1`。

## 统一响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## 路由层职责

- 接收参数
- 解析依赖
- 调用 application/service
- 把业务异常转换为 HTTP 错误

## 鉴权

- 认证依赖 JWT
- 授权依赖 RBAC 权限码
- 常见依赖在 `app/shared/auth` 和 `app/modules/*/api/dependencies.py`
