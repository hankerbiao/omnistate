# Shared 层

## 模块职责

`shared` 不是业务模块，而是全局共用基础设施。

它主要包含：

- 统一 API 入口、响应和错误处理
- JWT、密码处理和权限依赖
- Mongo 配置与全局客户端
- 日志
- Kafka / RabbitMQ / MinIO 等基础设施
- 共享 service 与 sequence id

## 关键目录

- `shared/api/`
- `shared/auth/`
- `shared/core/`
- `shared/db/`
- `shared/infrastructure/`
- `shared/kafka/`
- `shared/rabbitmq/`
- `shared/minio/`
- `shared/service/`

## 常见配置项与基础字段

配置结构定义在 `app/shared/config/settings.py`。`backend/config/*.yaml` 只负责应用、MongoDB
和日志启动配置，其余运行配置严格从当前 MongoDB 的 `system_configs` 加载，并通过“系统配置”
页面维护。

### 数据库与服务启动

- `mongodb.uri`
  MongoDB 连接串
- `mongodb.db_name`
  当前数据库名
- `app.debug`
  是否开启调试模式，影响中间件和日志行为
- `app.cors_origins`
  允许跨域访问的来源列表

### 认证

- `jwt.secret_key`
  JWT 签名密钥
- `jwt.expire_minutes`
  token 过期时间
- `jwt.issuer`
  token 签发者
- `jwt.audience`
  token 受众

### Open Platform 内部 JWT

- `open_platform_gateway_jwt.enabled`
  是否允许 Open Platform 网关签发的内部 JWT 访问主后端
- `open_platform_gateway_jwt.secret_key`
  内部 JWT 签名密钥，必须与 Open Platform 的 `DML_GATEWAY_UPSTREAM_AUTH_SECRET` 一致
- `open_platform_gateway_jwt.issuer` / `open_platform_gateway_jwt.audience`
  必须与 Open Platform 的 issuer / audience 配置一致

### 执行

- `execution.scheduler_interval_sec`
  调度器轮询间隔
- `execution.kafka_worker_agent_id`
  Kafka Worker 服务标识
- `execution.kafka_worker_heartbeat_ttl_sec`
  Worker 心跳过期时间

## 什么时候优先看 shared

- 问题横跨多个模块
- 统一响应或异常处理异常
- 鉴权依赖异常
- 启动期基础设施初始化失败
- 序列号生成、Mongo client、日志行为异常
