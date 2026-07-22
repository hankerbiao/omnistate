# 部署运行

## 本地开发部署

后端：

```bash
cd backend
uv sync --extra dev
DML_GATEWAY_UPSTREAMS=http://127.0.0.1:8801 uv run python -m gateway_service
```

前端：

```bash
cd frontend
npm install
npm run dev
```

文档：

```bash
cd docs
npm install
npm run build
```

## Docker Compose

项目根目录已有：

```text
docker-compose.yml
docker-compose.dev.yml
```

部署前请确认 compose 中的端口、上游地址、密钥和持久化卷符合当前环境。

## 生产部署建议

| 项 | 建议 |
| --- | --- |
| 网关进程 | 使用 uvicorn/gunicorn 或容器编排托管 |
| 前端 | 使用 `npm run build` 生成静态资源并由 Nginx/CDN 托管 |
| 文档 | 使用 `docs/.vitepress/dist` 静态部署 |
| 数据库 | 将 SQLite 文件放到持久化卷；更大规模可替换仓储实现 |
| 日志 | 配置标准输出采集或 `DML_GATEWAY_LOG_FILE` |
| 密钥 | 使用环境变量或密钥管理系统注入，不提交仓库 |

## 健康检查

```bash
curl http://127.0.0.1:8820/health
```

建议在部署平台中配置健康检查和重启策略。

## 安全基线

- 生产环境禁止使用默认 `dev-console-token`。
- API Key 明文只在创建时展示一次。
- 上游内部 JWT 密钥必须与 DML 主后端一致，并通过安全渠道配置。
- CORS 只允许可信控制台域名。
- 日志中避免输出完整 API Key。
