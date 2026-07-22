# 无容器部署

后端以 `uv` 管理 Python 与依赖，不需要预先创建虚拟环境，也不使用容器。部署入口统一为
`backend/deploy.sh`。

## 部署结果

`./deploy.sh install` 会按顺序执行：

1. 检查 `uv`，缺失时使用 Astral 官方安装脚本安装。
2. 运行 `uv sync --frozen --no-dev`，严格按照 `uv.lock` 创建 `.venv`。
3. 校验生产配置，不输出连接密码或密钥。
4. 同步 MongoDB 索引、workflow 配置和 RBAC 角色。
5. 可选创建或更新管理员。
6. Linux systemd 主机安装 API 与 Kafka Worker 服务并设置开机启动。
7. 非 systemd 环境使用 `server.sh` 和 `kafka_worker.sh` 后台运行。
8. 等待 `/health/ready` 返回成功，并确认托管进程仍处于运行状态。

所有步骤均可重复执行。已有 `config/config.yaml` 不会被覆盖，初始化脚本使用幂等 upsert。

## 首次部署

要求部署机可以访问 MongoDB、RabbitMQ、Kafka、Redis 和 MinIO，并且当前用户拥有代码目录写权限。

```bash
cd backend

# 第一次运行会生成配置模板并退出，也可以提前手工复制。
./deploy.sh install

# 修改生成的 config/config.yaml 后重新执行。
export DML_ADMIN_PASSWORD='replace-with-a-strong-password'
export DML_ADMIN_USER_ID='admin'
export DML_ADMIN_USERNAME='系统管理员'
./deploy.sh install
unset DML_ADMIN_PASSWORD
```

生产配置文件会被设置为 `0600`。管理员密码通过环境变量传给初始化脚本，不会出现在进程命令行中。

使用其他配置路径：

```bash
./deploy.sh install --config /etc/dmlv4/config.yaml
```

## 进程管理

脚本默认使用 `--manager auto`：

- Linux 且 systemd 正在运行：安装 `dmlv4-backend.service` 和
  `dmlv4-kafka-worker.service`，需要 root 或 sudo。
- macOS、WSL 或精简 Linux：使用项目内的 PID 和 nohup 脚本。

可以显式选择：

```bash
./deploy.sh install --manager systemd
./deploy.sh install --manager script
```

systemd 常用排障命令：

```bash
systemctl status dmlv4-backend dmlv4-kafka-worker
journalctl -u dmlv4-backend -f
journalctl -u dmlv4-kafka-worker -f
```

脚本模式日志位于 `backend/logs/server.log` 和 `backend/logs/kafka_worker.log`。

## 更新与运维

```bash
./deploy.sh update       # 同步锁定依赖、初始化数据、重启并检查健康状态
./deploy.sh doctor       # 只检查环境，不修改数据库或启动服务
./deploy.sh status
./deploy.sh restart
./deploy.sh stop
./deploy.sh start
```

只准备依赖，不初始化数据或启动服务：

```bash
./deploy.sh install --skip-init --no-start
```

不部署 Kafka Worker：

```bash
./deploy.sh install --without-worker
```

## 环境选择

- 生产环境默认 `DML_ENV=production`，只加载 `config/config.yaml`。
- 本地开发设置 `DML_ENV=dev`，额外加载 `config/config_dev.yaml`。
- `CONFIG_PATH` 或 `--config` 可以指定完整配置文件路径。
- `DML_APP_PORT` 可以临时覆盖监听端口。

生产进程不启用 Uvicorn 热重载。API 内含任务调度循环，因此当前保持单 API 进程；需要横向扩容时，
应先将调度器拆为独立进程或确认数据库租约策略满足部署规模。

## 发布建议

在 CI 或发布工作区执行测试：

```bash
uv run pytest tests/unit/architecture/ -q
```

在部署机执行环境检查（不会重新安装开发依赖）：

```bash
./deploy.sh doctor
```

发布后检查：

```bash
curl -fsS http://127.0.0.1:8801/health/live
curl -fsS http://127.0.0.1:8801/health/ready
./deploy.sh status
```
