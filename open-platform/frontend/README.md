# DML V4 开放平台 · 前端

开放平台前端（Vite + React + TypeScript），包含运行概览、API 密钥、开放能力目录、API 调试台、调用日志、用户权限与 MCP 接入页面。

默认数据源是本地开放平台网关 `http://127.0.0.1:8820`；只有显式设置 `VITE_OPEN_PLATFORM_USE_MOCK=true` 时才使用前端 Mock 数据。

## 开发命令

```bash
npm install        # 安装依赖
npm run dev        # 启动开发服务器，默认 http://0.0.0.0:8808
npm run build      # 类型检查 + 生产构建（输出 dist/）
npm run preview    # 预览生产构建，默认 http://0.0.0.0:8808
```

## 网关联调

先启动后端网关：

```bash
cd ../backend
python -m gateway_service
```

前端默认会请求：

```bash
VITE_OPEN_PLATFORM_API_BASE_URL=http://127.0.0.1:8820
VITE_OPEN_PLATFORM_CONSOLE_TOKEN=dev-console-token
VITE_OPEN_PLATFORM_USE_MOCK=false
```

可复制 `.env.example` 为 `.env.local` 后按需调整。

## Mock 模式

仅做纯前端演示时开启：

```bash
VITE_OPEN_PLATFORM_USE_MOCK=true npm run dev
```

> 端口说明：dev / preview 固定使用 **8808**。
> MCP 后端地址默认是 `http://127.0.0.1:8810/mcp`，详见 `../backend`。
