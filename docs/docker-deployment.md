# Docker Compose 部署

当前 Compose 只部署 DML 应用进程：

- `frontend`：Nginx + React 静态资源，对外入口
- `api`：FastAPI，默认仅绑定宿主机 `127.0.0.1:8801`
- `kafka-worker`：独立 Kafka 消费进程
- `runtime-config-migrate`：按需导入完整 MongoDB 运行配置
- `init`：按需同步索引、workflow、RBAC 和管理员

Kafka、Redis、MinIO、RabbitMQ 和 MongoDB 均视为外部服务，Compose 不会创建或修改这些集群。

## 前置条件

1. Docker Engine 及 Docker Compose 可用。
2. Docker 宿主机和容器网络可以解析并访问外部服务域名。
3. MongoDB 支持事务（Replica Set 或 Sharded Cluster）。
4. Redis 提供 Sentinel；当前后端不支持普通 Redis URL 直连。
5. Kafka 的 `advertised.listeners` 返回容器可访问的 broker 地址。
6. MinIO endpoint 可被容器、浏览器及执行 Agent 访问，以保证预签名 URL 有效。

## 准备配置

创建本地 Docker 环境文件和启动配置：

```bash
cp .env.docker.example .env.docker
cp backend/config/config.yaml.example backend/config/config.docker.yaml
```

编辑 `.env.docker`：

```dotenv
DML_BOOTSTRAP_CONFIG=./backend/config/config.docker.yaml
DML_FRONTEND_PORT=8080
```

编辑 `backend/config/config.docker.yaml`，至少设置外部 MongoDB：

```yaml
app:
  debug: false
  host: 0.0.0.0
  port: 8801
  service_name: dmlv4-backend
  cors_origins:
    - https://dml.example.com
  trusted_proxies: []
  dev_bypass_auth: false
  dev_user_id: dev_admin

mongodb:
  uri: mongodb://user:password@mongo-1.example.internal:27017,mongo-2.example.internal:27017/workflow_db?replicaSet=rs0&authSource=admin
  db_name: workflow_db

logging:
  console_level: INFO
  log_dir: logs
  retention: {info_days: 7, error_days: 30, debug_days: 3}
  json_format: true
  enable_compress: true
  trace_enabled: true
  slow_query_threshold_ms: 200
  slow_request_threshold_ms: 800
  module_levels: {}
```

启动配置通过只读 bind mount 注入，不会写入镜像。

## 已有 MongoDB 环境

如果目标数据库已经包含完整的 `system_configs`，先构建镜像并执行幂等初始化：

```bash
docker compose --env-file .env.docker build

export DML_ADMIN_PASSWORD='replace-with-a-strong-password'
docker compose --env-file .env.docker --profile ops run --rm init
unset DML_ADMIN_PASSWORD
```

`init` 会先验证 MongoDB 中运行配置完整，再同步索引、workflow、RBAC；不会覆盖 Kafka、Redis、MinIO 等连接值。

## 全新 MongoDB 环境

复制完整运行配置模板：

```bash
cp backend/config/runtime.full.yaml.example backend/config/runtime.full.yaml
```

把其中 MongoDB、Kafka、Redis Sentinel、MinIO、RabbitMQ、JWT 等地址和凭证全部替换为生产值，然后执行：

```bash
docker compose --env-file .env.docker --profile ops run --rm runtime-config-migrate

export DML_ADMIN_PASSWORD='replace-with-a-strong-password'
docker compose --env-file .env.docker --profile ops run --rm init
unset DML_ADMIN_PASSWORD
```

迁移完成后删除 `backend/config/runtime.full.yaml`。该文件已加入 `.gitignore`，但仍应按敏感文件管理。

## 启动与检查

```bash
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs -f api kafka-worker
```

默认入口：

- 前端：`http://localhost:8080`
- API 就绪检查：`http://127.0.0.1:8801/health/ready`
- Nginx 健康检查：`http://localhost:8080/healthz`

验证：

```bash
curl -fsS http://127.0.0.1:8801/health/ready
curl -fsS http://127.0.0.1:8080/healthz
```

## 外部集群连接

YAML 只保存应用、MongoDB 和日志启动配置。下列连接值保存在目标 MongoDB 的 `system_configs`：

- `kafka.bootstrap_servers`
- `redis.sentinel_hosts`、`redis.master_name`、Redis 凭证
- `minio.endpoint`、MinIO 凭证
- RabbitMQ、JWT、执行与通知配置

容器内的 `localhost` 指向容器自身，因此这些配置必须使用容器可路由的外部 DNS 或 IP。修改运行配置后重启 API 和 Worker：

```bash
docker compose --env-file .env.docker restart api kafka-worker
```

如果外部 Kafka 使用 SASL/TLS，需要先扩展当前 `KafkaConfig`；现有模型只包含 broker、topic 和 producer/consumer 行为参数。

## 更新与停止

```bash
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker down
```

Compose 不管理外部集群数据，因此 `down` 不会删除 MongoDB、Kafka、Redis 或 MinIO 数据。

如果部署环境不能直接访问 Docker Hub，可在 `.env.docker` 中把基础镜像切换到企业镜像仓库：

```dotenv
PYTHON_BASE_IMAGE=registry.example.com/library/python:3.13-slim-bookworm
NODE_BASE_IMAGE=registry.example.com/library/node:22-alpine
NGINX_BASE_IMAGE=registry.example.com/library/nginx:1.28-alpine
```
