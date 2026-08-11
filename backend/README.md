# DML V4 Backend

FastAPI 后端，提供测试需求、用例管理、执行编排、权限控制等统一服务。

## 快速开始

```bash
uv sync
# 首次创建数据库时，先显式迁移完整运行配置（见下文）
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
# YAML 只填写 app、mongodb、logging；其余配置必须已存在于目标 MongoDB
export DML_ADMIN_PASSWORD='replace-with-a-strong-password'
./deploy.sh install
```

Linux systemd 主机默认安装并启动 API、Kafka Worker 两个服务；其他环境使用后台脚本。
后续更新执行 `./deploy.sh update`，部署前检查执行 `./deploy.sh doctor`。详细说明见
[无容器部署指南](docs/guide/deployment.md)。

运行配置分环境保存在各自 MongoDB 的 `system_configs` 集合中。新数据库必须先用包含全部
运行项的一次性 YAML 显式迁移，迁移成功后立即删除该文件：

```bash
uv run python scripts/migrations/migrate_runtime_config_to_db.py \
  --base /secure/path/full-production-config.yaml \
  --environment production
```

应用不会从精简 YAML、模型默认值或其他环境补齐缺失项；数据库配置不完整时启动直接失败。
开发与生产切换分别使用 `DML_ENV=dev` 和 `DML_ENV=production`。

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
