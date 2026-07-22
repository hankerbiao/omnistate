# 快速开始

本页用于在本机启动开放平台网关与前端控制台。默认端口：

| 服务 | 默认地址 |
| --- | --- |
| DML 主后端 | `http://127.0.0.1:8801` |
| 开放平台网关 | `http://127.0.0.1:8820` |
| 开放平台前端 | `http://0.0.0.0:8808` |
| 文档站 | `http://0.0.0.0:8818` |

## 1. 启动 DML 主后端

开放平台网关需要将请求转发到 DML 主后端。请先确保主后端可访问，默认约定地址是：

```bash
http://127.0.0.1:8801
```

如果主后端使用其他地址，启动网关时通过 `DML_GATEWAY_UPSTREAMS` 指定。

## 2. 启动开放平台网关

```bash
cd backend
uv sync --extra dev
DML_GATEWAY_UPSTREAMS=http://127.0.0.1:8801 uv run python -m gateway_service
```

健康检查：

```bash
curl http://127.0.0.1:8820/health
```

Swagger 文档：

```text
http://127.0.0.1:8820/docs
```

## 3. 启动前端控制台

```bash
cd frontend
npm install
npm run dev
```

前端默认请求：

```bash
VITE_OPEN_PLATFORM_API_BASE_URL=http://127.0.0.1:8820
VITE_OPEN_PLATFORM_CONSOLE_TOKEN=dev-console-token
VITE_OPEN_PLATFORM_USE_MOCK=false
```

访问：

```text
http://127.0.0.1:8808
```

## 4. 启动文档站

```bash
cd docs
npm install
npm run dev
```

访问：

```text
http://127.0.0.1:8818
```

## 5. 调用开放 API

内置测试 API Key 可用于本地联调：

```bash
curl "http://127.0.0.1:8820/api/v1/open/execution/tasks/my?limit=5" \
  -H "Authorization: Bearer dml_test_demo_local"
```

开放 API 的稳定入口是 `/api/v1/open/...`。网关会完成能力匹配、API Key 认证、Scope 校验、上游选择、转发和审计记录。

## 常见问题

### 前端提示网关不可用

确认 `gateway_service` 已启动，并且 `.env.local` 或环境变量中的 `VITE_OPEN_PLATFORM_API_BASE_URL` 指向 `http://127.0.0.1:8820`。

### 开放 API 返回 401

确认请求头为：

```text
Authorization: Bearer <API Key>
```

本地可先使用 `dml_test_demo_local` 或在控制台创建新的测试密钥。

### 网关返回 503

通常表示上游 DML 主后端不可达。检查 `DML_GATEWAY_UPSTREAMS` 和主后端健康状态。
