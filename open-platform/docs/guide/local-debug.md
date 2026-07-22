# 本地联调

## 推荐启动顺序

1. 启动 DML 主后端，确保 `http://127.0.0.1:8801` 可用。
2. 启动开放平台网关。
3. 启动前端控制台。
4. 使用控制台调试台或 curl 验证开放 API。

## 网关联调命令

```bash
cd backend
DML_GATEWAY_UPSTREAMS=http://127.0.0.1:8801 \
DML_GATEWAY_LOG_LEVEL=DEBUG \
uv run python -m gateway_service
```

## 前端联调配置

可复制 `frontend/.env.example` 为 `.env.local`：

```bash
VITE_OPEN_PLATFORM_API_BASE_URL=http://127.0.0.1:8820
VITE_OPEN_PLATFORM_CONSOLE_TOKEN=dev-console-token
VITE_OPEN_PLATFORM_USE_MOCK=false
```

纯前端演示时启用 Mock：

```bash
VITE_OPEN_PLATFORM_USE_MOCK=true npm run dev
```

## 验证控制台 API

```bash
curl http://127.0.0.1:8820/api/v1/open-platform/overview \
  -H "X-Console-Token: dev-console-token" \
  -H "X-Console-User-Id: user_admin"
```

## 验证开放 API

```bash
curl "http://127.0.0.1:8820/api/v1/open/execution/tasks/my?limit=5" \
  -H "Authorization: Bearer dml_test_demo_local"
```

## 日志与请求 ID

网关会透传或生成 `X-Request-ID`，并将调用记录写入仓储。建议在联调时同时关注：

- 网关控制台输出
- `backend/logs/gateway_service.log`，如果启用了 `DML_GATEWAY_LOG_FILE`
- 控制台调用日志页面
- DML 主后端请求日志
