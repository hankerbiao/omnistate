# DML V4 开放平台

本目录包含 DML V4 开放平台的网关服务、MCP 服务、开放平台控制台和 VitePress 文档站点。MCP 服务与开放 API 网关复用同一套能力目录、API Key 鉴权、SQLite 仓储、上游转发和调用日志。

## 目录结构

```text
open-platform/
├── backend/
│   ├── gateway_service/   # 开放 API 网关
│   ├── mcp_server/        # MCP Server，复用 gateway_service 核心代码
│   ├── tests/             # 后端单测
│   ├── Dockerfile         # gateway 与 mcp 共用镜像
│   ├── pyproject.toml
│   └── README.md
├── frontend/              # 开放平台控制台，Vite + React + TypeScript
├── docs/                  # VitePress 文档站点
├── docker-compose.yml     # gateway + mcp
├── docker-compose.dev.yml # 开发模式 gateway reload + frontend dev
└── README.md
```

## 端口约定

| 服务 | 默认端口 | 说明 |
| --- | ---: | --- |
| DML 主后端 | 8801 | 开放平台网关的上游服务 |
| Open Platform Gateway | 8820 | 控制台 API 与开放 API 网关 |
| MCP Server | 8810 | Streamable HTTP MCP，默认路径 `/mcp` |
| Frontend | 8808 | 开放平台控制台 dev / preview |
| Docs | 8818 | VitePress 文档 dev / preview |

## 环境准备

本地需要安装 Python 3.11+、uv、Node.js 22+、npm 和 Docker。

```bash
# 检查版本
python --version
uv --version
node --version
npm --version
docker --version
docker compose version
```

如未安装 `uv`：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 本地开发构建

### 后端依赖

```bash
cd backend
uv sync --extra dev
```

### 启动开放 API 网关

```bash
cd backend
DML_GATEWAY_UPSTREAMS=http://127.0.0.1:8801 \
uv run python -m gateway_service
```

启动后访问：

```bash
curl http://127.0.0.1:8820/health
```

### 启动 MCP Server

stdio 模式：

```bash
cd backend
DML_MCP_API_KEY=dml_test_demo_local \
uv run python -m mcp_server.server
```

HTTP 模式：

```bash
cd backend
DML_MCP_TRANSPORT=streamable-http \
DML_MCP_API_KEY=dml_test_demo_local \
DML_GATEWAY_UPSTREAMS=http://127.0.0.1:8801 \
uv run python -m mcp_server.server
```

默认 HTTP 地址为 `http://127.0.0.1:8810/mcp`。

### 构建前端

```bash
cd frontend
npm install
npm run lint
npm run test:run
npm run build
```

本地开发启动：

```bash
cd frontend
VITE_OPEN_PLATFORM_API_BASE_URL=http://127.0.0.1:8820 \
VITE_OPEN_PLATFORM_CONSOLE_TOKEN=dev-console-token \
npm run dev
```

访问 `http://127.0.0.1:8808`。

### 构建文档站点

```bash
cd docs
npm install
npm run build
```

本地文档预览：

```bash
cd docs
npm run dev
```

访问 `http://127.0.0.1:8818`。

## 后端质量检查

```bash
cd backend
uv run ruff check gateway_service mcp_server tests
uv run pytest tests -v
```

## Docker Compose 构建

### 常规构建

```bash
docker compose build open-platform-gateway open-platform-mcp
```

### 使用代理构建

如果宿主机代理为 `127.0.0.1:7897`，先导出宿主机代理变量：

```bash
export https_proxy=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export all_proxy=socks5://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897
export HTTP_PROXY=http://127.0.0.1:7897
export ALL_PROXY=socks5://127.0.0.1:7897
```

Docker 构建阶段需要通过 `host.docker.internal` 访问宿主机代理：

```bash
docker compose build \
  --build-arg HTTP_PROXY=http://host.docker.internal:7897 \
  --build-arg HTTPS_PROXY=http://host.docker.internal:7897 \
  --build-arg ALL_PROXY=socks5://host.docker.internal:7897 \
  open-platform-gateway open-platform-mcp
```

如果后台构建卡住，可手动停止：

```bash
pkill -f 'docker compose build'
```

## Docker Compose 启动

启动网关和 MCP：

```bash
docker compose up -d open-platform-gateway open-platform-mcp
```

开发模式同时启动前端：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

查看状态和日志：

```bash
docker compose ps
docker logs -f dml-open-platform-gateway
docker logs -f dml-open-platform-mcp
docker logs -f dml-open-platform-frontend
```

停止服务：

```bash
docker compose down
```

## 发布到内网服务器

以下示例以服务器 `10.2.48.65` 为目标，MCP 使用内网 HTTP 地址 `http://10.2.48.65:8810/mcp`。

### 1. 本机完成镜像构建

```bash
docker compose build open-platform-gateway open-platform-mcp
```

如需代理，使用上一节的代理构建命令。

### 2. 导出镜像

```bash
docker save dml-open-platform-gateway:local -o dml-open-platform-gateway-local.tar
```

### 3. 上传发布文件

```bash
scp dml-open-platform-gateway-local.tar docker-compose.yml docker-compose.dev.yml user@10.2.48.65:/opt/dml-open-platform/
```

### 4. 服务器导入镜像

```bash
ssh user@10.2.48.65
cd /opt/dml-open-platform
docker load -i dml-open-platform-gateway-local.tar
```

### 5. 配置生产环境变量

```bash
cat > .env <<'EOF'
DML_GATEWAY_UPSTREAMS=http://10.2.48.65:8801
DML_GATEWAY_CONSOLE_TOKEN=请替换为强随机控制台Token
DML_GATEWAY_UPSTREAM_AUTH_SECRET=请替换为与DML主后端一致的JWT密钥
DML_GATEWAY_UPSTREAM_AUTH_ISSUER=dml-open-platform
DML_GATEWAY_UPSTREAM_AUTH_AUDIENCE=dml-backend
DML_MCP_API_KEY=dml_test_demo_local
EOF
```

生产环境请不要继续使用默认的 `dev-console-token` 和默认内部 JWT 密钥。

### 6. 启动服务

```bash
docker compose up -d open-platform-gateway open-platform-mcp
docker compose ps
```

### 7. 验证服务

网关健康检查：

```bash
curl http://10.2.48.65:8820/health
```

查看当前用户可用能力：

```bash
curl http://10.2.48.65:8820/api/v1/open-platform/me/capabilities \
  -H "X-Console-Token: <你的控制台Token>" \
  -H "X-Console-User-Id: user_developer"
```

使用内置联调 API Key 调开放 API：

```bash
curl "http://10.2.48.65:8820/api/v1/open/execution/tasks/my?limit=5" \
  -H "Authorization: Bearer dml_test_demo_local"
```

MCP Server 地址：

```text
http://10.2.48.65:8810/mcp
```

## MCP 客户端安装配置

内部 HTTP 部署可以直接使用 IP 地址。客户端需要支持 Streamable HTTP MCP，并在请求头中带上开放平台 API Key。

示例配置：

```json
{
  "mcpServers": {
    "dml-open-platform": {
      "type": "streamable-http",
      "url": "http://10.2.48.65:8810/mcp",
      "headers": {
        "Authorization": "Bearer dml_test_demo_local"
      }
    }
  }
}
```

如果客户端不支持自定义请求头，也可以在服务端通过 `DML_MCP_API_KEY` 配置默认 API Key。生产环境建议为不同团队或客户端创建独立 API Key，便于权限控制、配额统计和审计。

## 常用配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DML_GATEWAY_HOST` | `127.0.0.1` | 网关监听地址 |
| `DML_GATEWAY_PORT` | `8820` | 网关监听端口 |
| `DML_GATEWAY_UPSTREAMS` | `http://127.0.0.1:8801` | DML 主后端地址，逗号分隔 |
| `DML_GATEWAY_DB_PATH` | `gateway_service/gateway.db` | SQLite 数据库路径 |
| `DML_GATEWAY_CONSOLE_TOKEN` | `dev-console-token` | 控制台 API Token |
| `DML_GATEWAY_UPSTREAM_AUTH_SECRET` | `dev-open-platform-gateway-secret-change-me` | 调用 DML 主后端的内部 JWT 密钥 |
| `DML_GATEWAY_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:8808,http://127.0.0.1:8808,http://localhost:8809,http://127.0.0.1:8809` | CORS 白名单 |
| `DML_MCP_TRANSPORT` | `stdio` | `stdio` 或 `streamable-http` |
| `DML_MCP_API_KEY` | 空 | MCP 默认开放平台 API Key |
| `DML_MCP_HOST` | `127.0.0.1` | MCP HTTP 监听地址 |
| `DML_MCP_PORT` | `8810` | MCP HTTP 监听端口 |
| `DML_MCP_PATH` | `/mcp` | MCP HTTP 路径 |
| `VITE_OPEN_PLATFORM_API_BASE_URL` | `http://127.0.0.1:8820` | 前端访问的网关地址 |
| `VITE_OPEN_PLATFORM_CONSOLE_TOKEN` | `dev-console-token` | 前端控制台 Token |
| `VITE_OPEN_PLATFORM_USE_MOCK` | `false` | 是否启用前端 Mock |

更多细节见：

- [backend/README.md](./backend/README.md)
- [frontend/README.md](./frontend/README.md)
- [docs/README.md](./docs/README.md)
