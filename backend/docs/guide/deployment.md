# 无容器部署

这份文档描述在不使用容器的前提下，如何用 `uv` 安装、初始化和运行 DML V4 后端。
部署入口统一为 `backend/deploy.sh`，它会根据当前主机环境自动选择 `systemd` 或脚本模式。

## 部署形态

默认推荐的运行方式是：

1. `uv sync --frozen --no-dev` 创建并锁定 `.venv`
2. `deploy.sh` 初始化 MongoDB、RBAC 和管理员账号
3. API 进程和 Kafka Worker 以 `systemd` 或后台脚本方式常驻
4. YAML 只提供启动配置，运行配置从目标 MongoDB 的 `system_configs` 严格加载

### 运行模式

- `systemd`
  适合 Linux 服务器，支持开机自启、自动重启和 `journalctl` 查看日志。
- `script`
  适合 macOS、WSL 或没有 systemd 的环境，使用 PID 文件和 `nohup` 常驻。

## 前置条件

部署前请确认：

- Python 3.11+
- `uv` 可用，或允许脚本自动安装
- 可以访问 MongoDB、RabbitMQ、Kafka、Redis 和 MinIO
- 部署目录有写权限
- `system_configs` 中的基础设施地址、密钥和账号已经准备好

如果这是第一次部署，先把模板复制成正式配置：

```bash
cd backend
cp config/config.yaml.example config/config.yaml
```

然后只修改其中的应用监听、MongoDB 和日志配置。RabbitMQ、Kafka、Redis、MinIO、JWT、
执行、通知和 Open Platform JWT 不允许写回该文件。

### 新数据库配置

应用不会自动创建或补齐运行配置。首次使用一个全新的数据库时，必须准备一份一次性的完整
YAML，其中显式包含全部运行字段，然后执行：

```bash
uv run python scripts/migrations/migrate_runtime_config_to_db.py \
  --base /secure/path/full-production-config.yaml \
  --environment production
```

迁移脚本会严格检查字段完整性，任何缺项或未知项都会失败，不会采用代码默认值。迁移成功并
确认目标数据库已有 72 个后端运行项后，删除一次性 YAML。精简后的
`config/config.yaml` 只能用于 `--metadata-only`，不能再次作为普通迁移源：

```bash
uv run python scripts/migrations/migrate_runtime_config_to_db.py \
  --base config/config.yaml \
  --environment production \
  --metadata-only
```

已有环境也可以先复制一套经审核的 `system_configs` 集合到新数据库，再通过“系统配置”页面
修改环境差异并重启后端。无论采用哪种方式，缺少任意运行项都会阻断启动。

## 首次部署

最常见的路径是直接执行安装：

```bash
cd backend
export DML_ADMIN_PASSWORD='replace-with-a-strong-password'
./deploy.sh install
unset DML_ADMIN_PASSWORD
```

这个命令会依次完成：

1. 检查 `uv`
2. 使用 `uv.lock` 同步生产依赖
3. 校验 YAML 启动配置和 MongoDB 中全部运行配置
4. 为全部已注册 Beanie 模型同步 MongoDB 索引
5. 以 upsert 方式同步 workflow 基础数据（默认不删除既有记录）
6. 同步 RBAC 角色
7. 如设置了 `DML_ADMIN_PASSWORD`，创建或更新管理员账号
8. 安装并启动 API 和 Kafka Worker
9. 检查 `/health/ready`

`config/config.yaml` 和 `system_configs` 的值不会被部署脚本覆盖。workflow、索引和 RBAC
初始化脚本是幂等的，可以重复执行。

## 升级发布

后续升级建议使用：

```bash
./deploy.sh update
```

它会重新同步锁定依赖，重新初始化数据，并重启托管进程。适合代码更新后做小版本发布。

如果你只想更新依赖，不想启动服务：

```bash
./deploy.sh install --no-start
```

如果你只想跳过数据初始化：

```bash
./deploy.sh install --skip-init
```

正常发布不会删除 workflow 数据。只有确认配置已下线、存量事项已完成迁移时，才执行：

```bash
./deploy.sh init --prune-workflow
```

该参数会删除配置源中不存在的事项类型和流转规则。

如果这台机器只运行 API，不运行 Kafka Worker：

```bash
./deploy.sh install --without-worker
```

## 常用命令

```bash
./deploy.sh doctor     # 检查 uv、配置和进程管理方式
./deploy.sh status     # 查看托管进程状态
./deploy.sh restart    # 重启 API 和 Worker
./deploy.sh stop       # 停止 API 和 Worker
./deploy.sh start      # 启动 API 和 Worker
```

如果你需要显式选择进程管理方式：

```bash
./deploy.sh install --manager systemd
./deploy.sh install --manager script
```

## systemd 部署

在 Linux 且 systemd 可用的主机上，`deploy.sh install` 会自动安装两个服务：

- `dmlv4-backend.service`
- `dmlv4-kafka-worker.service`

常用排障命令：

```bash
systemctl status dmlv4-backend dmlv4-kafka-worker
journalctl -u dmlv4-backend -f
journalctl -u dmlv4-kafka-worker -f
```

systemd 模式下，服务会自动重启，日志进入 systemd journal。

## 脚本部署

如果主机没有 systemd，脚本会回退到项目内的管理脚本：

- `server.sh`
- `kafka_worker.sh`

日志文件位于：

- `backend/logs/server.log`
- `backend/logs/kafka_worker.log`

PID 文件位于：

- `backend/.server.pid`
- `backend/.kafka_worker.pid`

你也可以直接调用：

```bash
./server.sh start
./server.sh stop
./server.sh status
./kafka_worker.sh start
./kafka_worker.sh stop
./kafka_worker.sh status
```

## 环境变量

这些变量最常用：

- `CONFIG_PATH`
  指定配置文件路径，默认是 `backend/config/config.yaml`
- `DML_ENV`
  环境标识，生产默认 `production`，开发建议 `dev`
- `DML_ADMIN_PASSWORD`
  创建或更新管理员账号时使用的密码
- `DML_ADMIN_USER_ID`
  管理员用户 ID，默认 `admin`
- `DML_ADMIN_USERNAME`
  管理员显示名，默认 `系统管理员`
- `DML_ADMIN_EMAIL`
  管理员邮箱，可选
- `DML_WITH_WORKER`
  记录是否托管 Kafka Worker，`1` 或 `0`

生产环境使用 `DML_ENV=production`，加载 `config/config.yaml` 并连接其中指定的生产数据库。
开发环境使用 `DML_ENV=dev`，强制加载 `config/config_dev.yaml` 并连接开发数据库。开发覆盖
文件缺失时进程直接失败，不会回退到生产配置。两个数据库各自维护独立的 `system_configs`，
所以切换环境只需要切换 `DML_ENV` 并重启对应进程。

```bash
DML_ENV=dev uv run python -m app.main
DML_ENV=production uv run python -m app.main
```

`deploy.sh` 面向生产部署，会显式设置 `DML_ENV=production`。

## 初始化脚本边界

生产部署只调用 `scripts/init/` 下的索引、workflow、RBAC 和单用户工具。以下脚本不属于发布流程：

- `DML_ENV=dev uv run python scripts/dev/seed_test_users.py`：创建开发测试账号，生产环境会拒绝执行
- `uv run python scripts/migrations/backfill_default_project.py`：一次性回填历史项目数据，需单独评审后执行

索引、workflow 与 RBAC 也可以单独运行：

```bash
uv run python scripts/init/sync_indexes.py
uv run python scripts/init/sync_workflow.py
uv run python scripts/init/sync_rbac.py
```

## 验证

部署后建议做三步检查：

```bash
curl -fsS http://127.0.0.1:8801/health/live
curl -fsS http://127.0.0.1:8801/health/ready
./deploy.sh status
```

如果只想先检查环境而不触发安装：

```bash
./deploy.sh doctor
```

## 常见问题

### `uv` 不存在

`deploy.sh install` 会尝试安装 `uv`。如果当前用户没有联网能力，先手工安装 `uv` 再执行部署。

### 配置文件不存在

第一次执行 `./deploy.sh install` 时，如果 `config/config.yaml` 不存在，脚本会先生成模板并退出。
这是为了避免在未确认应用与 MongoDB 启动配置的情况下误启动。补好 YAML 后，还必须先将完整
运行配置显式写入目标数据库。

### MongoDB 运行配置不完整

`./deploy.sh doctor`、`install`、API 和 Kafka Worker 都会报告缺少的配置键并失败。先执行显式
迁移或修复目标数据库中的 `system_configs`，不要把运行项临时放回 YAML；YAML 不会被读取为
运行配置源。

### API 已启动但健康检查失败

优先检查：

1. `config/config.yaml` 的 MongoDB 地址
2. 目标数据库的 72 个运行项是否完整、有效
3. `system_configs` 中 RabbitMQ、Kafka、Redis、MinIO 地址是否可达
4. `./deploy.sh doctor` 的输出
5. `backend/logs/server.log` 或 systemd journal

### 更新后服务没起来

先看：

```bash
./deploy.sh status
./deploy.sh doctor
```

如果是 systemd 模式，再看：

```bash
journalctl -u dmlv4-backend -n 100 --no-pager
journalctl -u dmlv4-kafka-worker -n 100 --no-pager
```

## 推荐发布顺序

如果你要做一次完整发布，可以按这个顺序：

```bash
cd backend
./deploy.sh doctor
./deploy.sh update
curl -fsS http://127.0.0.1:8801/health/ready
```

这套流程比较适合手工运维，也适合写进发布检查单。
