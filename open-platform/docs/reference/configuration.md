# 配置参考

## 网关环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DML_GATEWAY_HOST` | `127.0.0.1` | 监听地址 |
| `DML_GATEWAY_PORT` | `8820` | 监听端口 |
| `DML_GATEWAY_UPSTREAMS` | `http://127.0.0.1:8801` | 上游 DML 主后端地址，逗号分隔 |
| `DML_GATEWAY_REQUEST_TIMEOUT` | `15` | 请求总超时秒数 |
| `DML_GATEWAY_CONNECT_TIMEOUT` | `3` | 连接超时秒数 |
| `DML_GATEWAY_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:8808,http://127.0.0.1:8808,http://localhost:8809,http://127.0.0.1:8809` | CORS 允许来源 |
| `DML_GATEWAY_CONSOLE_TOKEN` | `dev-console-token` | 控制台 API Token |
| `DML_GATEWAY_LOG_LEVEL` | `INFO` | 日志级别 |
| `DML_GATEWAY_LOG_FILE` | 空 | 日志文件路径 |
| `DML_GATEWAY_DB_PATH` | `gateway_service/gateway.db` | SQLite 数据库路径 |
| `DML_GATEWAY_UPSTREAM_AUTH_SECRET` | `dev-open-platform-gateway-secret-change-me` | 内部 JWT 签名密钥 |
| `DML_GATEWAY_UPSTREAM_AUTH_ALGORITHM` | `HS256` | 内部 JWT 算法 |
| `DML_GATEWAY_UPSTREAM_AUTH_ISSUER` | `dml-open-platform` | 内部 JWT issuer |
| `DML_GATEWAY_UPSTREAM_AUTH_AUDIENCE` | `dml-backend` | 内部 JWT audience |
| `DML_GATEWAY_UPSTREAM_AUTH_TTL_SECONDS` | `300` | 内部 JWT 有效期 |

## 前端环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_OPEN_PLATFORM_API_BASE_URL` | `http://127.0.0.1:8820` | 网关地址 |
| `VITE_OPEN_PLATFORM_CONSOLE_TOKEN` | `dev-console-token` | 控制台 Token |
| `VITE_OPEN_PLATFORM_USE_MOCK` | `false` | 是否启用 Mock |

## 文档站配置

文档站位于 `docs/`：

| 文件 | 说明 |
| --- | --- |
| `package.json` | VitePress 脚本和依赖 |
| `.vitepress/config.ts` | 站点标题、导航、侧边栏、搜索 |
| `.vitepress/theme.css` | 品牌色覆盖 |

命令：

```bash
npm run dev
npm run build
npm run preview
```

## 生产建议

- 修改 `DML_GATEWAY_CONSOLE_TOKEN`，不要使用默认值。
- 修改 `DML_GATEWAY_UPSTREAM_AUTH_SECRET`，并与 DML 主后端配置保持一致。
- 将 `DML_GATEWAY_DB_PATH` 指向持久化卷。
- 配置 `DML_GATEWAY_LOG_FILE` 或接入统一日志采集。
- 只允许可信前端来源出现在 `DML_GATEWAY_CORS_ORIGINS`。
