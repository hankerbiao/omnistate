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

### 数据库与服务启动

- `MONGO_URI`
  MongoDB 连接串
- `MONGO_DB_NAME`
  当前数据库名
- `APP_DEBUG`
  是否开启调试模式，影响中间件和日志行为
- `CORS_ORIGINS`
  允许跨域访问的来源列表

### 认证

- `JWT_SECRET_KEY`
  JWT 签名密钥
- `JWT_EXPIRE_MINUTES`
  token 过期时间
- `JWT_ISSUER`
  token 签发者
- `JWT_AUDIENCE`
  token 受众

### 执行与终端

- `EXECUTION_DISPATCH_MODE`
  执行任务分发模式
- `EXECUTION_HTTP_TIMEOUT_SEC`
  HTTP 分发超时
- `EXECUTION_SCHEDULER_INTERVAL_SEC`
  调度器轮询间隔
- `TERMINAL_SHELL`
  远程终端 shell
- `TERMINAL_IDLE_TIMEOUT_SEC`
  终端空闲超时

## 什么时候优先看 shared

- 问题横跨多个模块
- 统一响应或异常处理异常
- 鉴权依赖异常
- 启动期基础设施初始化失败
- 序列号生成、Mongo client、日志行为异常
