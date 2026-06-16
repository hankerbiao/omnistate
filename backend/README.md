# DML V4 Backend

FastAPI 后端，提供测试需求、用例管理、执行编排、权限控制等统一服务。

## 快速开始

```bash
uv sync
python app/init_mongodb.py
python scripts/init/init_rbac.py
python scripts/init/create_user.py
python -m app.main
```

默认监听 `0.0.0.0:8000`，API 前缀 `/api/v1`。

## 项目结构

```text
app/
├── main.py                  # 入口
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
| `config.yaml.example` | 配置模板 |

## 命令速查

```bash
pytest                     # 测试
flake8                     # 代码检查
python -m app.main         # 启动
```
