# DML V4 Backend

FastAPI 后端，提供测试需求、用例管理、执行编排、权限控制等统一服务。

## 快速开始

```bash
uv sync
uv run python scripts/init/init_mongodb.py
uv run python scripts/init/init_rbac.py
uv run python scripts/init/create_user.py
DML_ENV=dev uv run python -m app.main
```

默认监听 `0.0.0.0:8801`，API 前缀 `/api/v1`。

## 无容器部署

生产环境统一使用 `uv.lock` 和一键部署脚本：

```bash
cd backend
cp config/config.yaml.example config/config.yaml  # 首次部署时执行
# 修改 config.yaml 中的基础设施地址与密钥
export DML_ADMIN_PASSWORD='replace-with-a-strong-password'
./deploy.sh install
```

Linux systemd 主机默认安装并启动 API、Kafka Worker 两个服务；其他环境自动回退到后台脚本。
后续更新执行 `./deploy.sh update`，部署前检查执行 `./deploy.sh doctor`。详细说明见
[无容器部署指南](docs/guide/deployment.md)。

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
| `config/config.yaml.example` | 配置模板 |

## 命令速查

```bash
uv run pytest              # 测试
uv run ruff check app tests # 代码检查
uv run python -m app.main  # 启动
```
