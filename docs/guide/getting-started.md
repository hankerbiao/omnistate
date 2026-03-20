# 后端快速开始

## 1. 适用范围

本文档只描述 DMLV4 当前仓库中的后端启动方式，不包含 `frontend/`。

## 2. 环境要求

- Python 3.10+
- MongoDB

可选依赖：

- Kafka，若执行分发模式使用 `kafka`

## 3. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

## 4. 初始化基础数据

### 4.1 初始化工作流配置

```bash
cd backend
python app/init_mongodb.py
```

该脚本会：

- 读取 `app/configs/*.json`
- 初始化事项类型、状态、流转配置
- 初始化部分 RBAC 基础数据和默认导航页定义
- 以幂等方式写入 MongoDB

### 4.2 初始化 RBAC

```bash
cd backend
python scripts/init_rbac.py
```

该脚本会初始化默认权限和默认角色。

注意：

- 当前脚本中的默认角色包含对 `assets:read` 的引用，但仓库中没有对应后端模块实现；这不影响已实现模块的启动和使用，但说明 RBAC 默认数据仍有待进一步清理。

### 4.3 创建管理员用户

`scripts/create_user.py` 不是无参脚本，必须带参数执行。

示例：

```bash
cd backend
python scripts/create_user.py \
  --user-id admin \
  --username 管理员 \
  --password 'admin123' \
  --roles ADMIN \
  --email admin@example.com
```

如需覆盖已有用户，追加 `--upsert`。

## 5. 启动服务

若 `backend/.env` 中 `EXECUTION_DISPATCH_MODE=kafka`，请先启动 Kafka worker：

```bash
cd backend
python -m app.workers.kafka_worker_main
```

`kafka_worker_main` 的作用：

- 消费 `test-events`
- 更新任务和 case 当前状态
- 在串行任务中继续推进下一条 case
- 维护 execution Kafka worker 在线心跳

然后再启动主服务：

```bash
cd backend
python -m app.main
```

默认监听：

- `0.0.0.0:8000`

## 6. 启动时会发生什么

服务启动时会自动：

1. 连接 MongoDB。
2. 注册 Beanie 文档模型。
3. 校验 workflow 配置一致性。
4. 若当前使用 Kafka 分发，校验 execution Kafka worker 是否在线。
5. 初始化应用级基础设施。
6. 挂载 `/health` 和 `/api/v1/*` 路由。

补充说明：

- 当 `EXECUTION_DISPATCH_MODE=kafka` 且 worker 未启动时，主服务会拒绝启动。
- worker 负责消费 `test-events` 并推进串行任务；只启动主服务并不能完成完整执行链路。

推荐完整启动顺序：

1. MongoDB
2. Kafka
3. `python -m app.workers.kafka_worker_main`
4. `python -m app.main`
5. 执行代理或 mock 测试框架

## 7. 关键配置

配置定义在 `backend/app/shared/db/config.py`，主要通过 `backend/.env` 覆盖。

常用项：

- `MONGO_URI`
- `MONGO_DB_NAME`
- `CORS_ORIGINS`
- `JWT_SECRET_KEY`
- `JWT_EXPIRE_MINUTES`
- `EXECUTION_DISPATCH_MODE`
- `EXECUTION_AGENT_DISPATCH_PATH`
- `EXECUTION_HTTP_TIMEOUT_SEC`
- `EXECUTION_KAFKA_WORKER_AGENT_ID`

## 8. 验证服务

建议至少做以下验证：

```bash
curl http://localhost:8000/health
```

然后再验证业务接口，例如登录或查询权限接口。

## 9. 下一步

- 阅读 [后端架构说明](/architecture)
- 阅读 [认证与授权](/guide/authentication)
- 阅读 [需求与用例管理](/guide/test-requirements-cases)
- 阅读 [执行编排](/guide/test-execution)
