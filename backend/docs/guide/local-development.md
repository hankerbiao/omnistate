# 本地开发

## 依赖与运行环境

- Python 3.10+
- MongoDB
- 后端依赖来自 `pyproject.toml`（使用 uv 管理）

## 安装依赖

```bash
cd backend
uv sync
```

## 初始化基础数据

```bash
cd backend
python scripts/init/init_mongodb.py
python scripts/init/init_rbac.py
python scripts/init/create_user.py
```

用途分别是：

- `scripts/init/init_mongodb.py`
  初始化 workflow 类型、状态和流转配置
- `scripts/init/init_rbac.py`
  初始化角色、权限、导航等 RBAC 基础数据
- `scripts/init/create_user.py`
  创建初始管理员

## 启动服务

```bash
cd backend
python -m app.main
```

默认端口是 `8000`。

## 常用检查命令

### pytest

```bash
cd backend
pytest
pytest tests/unit/workflow/ -v
pytest tests/unit/architecture/ -v
pytest --cov=app
```

### flake8

```bash
cd backend
flake8
flake8 app/modules/execution/
flake8 --select=E,W,F
```

## 配置来源

关键运行配置主要来自：

- `config/config.yaml`
- `app/shared/config/settings.py`

重点关注：

- `mongodb.uri`
- `mongodb.db_name`
- `app.cors_origins`
- Kafka/RabbitMQ 相关配置
- JWT 相关配置

### 关键配置项说明

- `mongodb.uri`
  MongoDB 连接串；服务启动时会先用它做 `ping` 检查
- `mongodb.db_name`
  当前后端使用的数据库名；Beanie 初始化和 workflow 配置校验都依赖它
- `app.cors_origins`
  允许跨域访问的前端来源列表；本地开发常需要放开给 `localhost`
- `jwt.secret_key`
  JWT 签名密钥；修改后旧 token 会全部失效
- `jwt.expire_minutes`
  登录 token 的有效期，单位分钟
- `jwt.issuer`
  token 签发者校验值
- `jwt.audience`
  token 受众校验值
- `execution.scheduler_interval_sec`
  调度器扫描待触发任务的时间间隔
- `open_platform_gateway_jwt.*`
  Open Platform 网关调用主后端时使用的内部 JWT 校验配置

## 本地开发时优先检查什么

- 服务起不来：先看 `app/main.py` 的初始化链路
- workflow 校验失败：先检查 `app/configs/*.json` 和 Mongo 初始化数据
- 鉴权失败：先看 `app/shared/auth` 与 `app/modules/auth`
- 执行任务异常：先看 `execution` 模块和消息通道配置
