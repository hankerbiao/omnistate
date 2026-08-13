# DML V4 Backend
FastAPI 后端，提供测试需求、用例管理、权限控制等统一服务。

## 快速开始

```bash
uv sync
cp config/config.yaml.example config/config.yaml
python -c 'import secrets; print(f"DML_JWT_SECRET={secrets.token_urlsafe(32)}"); print(f"MINIO_ROOT_USER={secrets.token_urlsafe(24)}"); print(f"MINIO_ROOT_PASSWORD={secrets.token_urlsafe(32)}")' > config/.env
set -a; . config/.env; set +a
uv run python scripts/init/sync_indexes.py
uv run python scripts/init/sync_workflow.py
uv run python scripts/init/sync_rbac.py
uv run python scripts/init/create_user.py --help
DML_ENV=dev uv run python -m app.main
```
默认监听 `0.0.0.0:8801`，API 前缀 `/api/v1`。

## 无容器部署

生产环境统一使用 `uv.lock` 和一键部署脚本：

```bash
cd backend
cp config/config.yaml.example config/config.yaml  # 首次部署时执行
python -c 'import secrets; print(f"DML_JWT_SECRET={secrets.token_urlsafe(32)}"); print(f"MINIO_ROOT_USER={secrets.token_urlsafe(24)}"); print(f"MINIO_ROOT_PASSWORD={secrets.token_urlsafe(32)}")' > config/.env
export DML_ADMIN_PASSWORD='replace-with-a-strong-password'
./deploy.sh install
```

Linux systemd 主机默认安装并启动 API、Kafka Worker 两个服务；其他环境使用后台脚本。
后续更新执行 `./deploy.sh update`，部署前检查执行 `./deploy.sh doctor`。详细说明见
[无容器部署指南](docs/guide/deployment.md)。

应用只从一个 YAML 文件读取配置：容器使用挂载的 `/run/dml/config.yaml`，本地运行使用
`backend/config/config.yaml`。`CONFIG_PATH` 可覆盖该路径。配置模型会拒绝未知字段；YAML 中
以 `${VARIABLE_NAME}` 形式出现的完整值会从环境变量读取，缺失时启动失败。

`DML_JWT_SECRET`、`MINIO_ROOT_USER` 和 `MINIO_ROOT_PASSWORD` 是必填的高熵密钥，
不能使用 `CHANGE_ME` 或 `minioadmin` 等默认值。生产环境应由 Secret Manager、容器 secret
或编排平台注入，不应把真实密钥提交到仓库。本地 Docker Compose 会读取
被忽略的 `config/.env`；非容器启动前执行 `set -a; . config/.env; set +a`。

## 项目结构

```text
app/
├── main.py                  # FastAPI 入口
├── modules/                 # 业务模块
└── shared/                  # 基础设施
scripts/                     # 工具脚本
tests/                       # 测试
docs/                        # 文档
```

## 关键文档

| 文档 | 说明 |
|------|------|
| `AGENTS.md` | 开发规范、命令速查 |
| `app/modules/*/README.md` | 各模块详细说明 |
| `docs/test_plan/` | 测试方案与覆盖度报告 |
| `config/config.yaml.example` | 仅含启动配置的生产模板 |

## 命令速查

```bash
uv run pytest              # 测试
uv run ruff check app tests # 代码检查
uv run python -m app.main  # 启动
```
