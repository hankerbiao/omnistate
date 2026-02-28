# DML V4 - 测试需求与用例管理平台

前后端分离的测试管理系统，覆盖测试需求、测试用例、配置驱动工作流、RBAC 鉴权、菜单权限和资产管理。

## 项目概览

- 后端：FastAPI + Beanie + MongoDB
- 前端：React 19 + TypeScript + Vite + Tailwind CSS v4
- 认证鉴权：JWT + RBAC（用户/角色/权限）
- API 返回：统一 Envelope 格式 `code/message/data`

## 核心能力

- 配置驱动工作流（`backend/app/configs/*.json`）
- 测试需求管理（`/api/v1/requirements`）
- 测试用例管理（`/api/v1/test-cases`）
- 用户/角色/权限管理（`/api/v1/auth`）
- 菜单管理（`/api/v1/menus`）
- 资产管理（`/api/v1/assets`）

## 目录结构

```text
dmlv4/
├── backend/
│   ├── app/
│   │   ├── main.py                    # 后端入口
│   │   ├── init_mongodb.py            # 初始化工作流配置 + 默认 RBAC
│   │   ├── configs/                   # 工作流配置文件
│   │   ├── modules/                   # 业务模块
│   │   └── shared/                    # 通用基础设施
│   ├── scripts/                       # 用户、RBAC、模拟数据脚本
│   └── tests/                         # 单测/集成测试
├── frontend/
│   ├── src/components/views/          # 登录/需求/用例/用户管理页面
│   ├── src/services/api/              # API 客户端封装
│   └── src/constants/                 # 前端配置常量
└── docs/                              # 设计与接口文档
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- MongoDB 6.0+

### 2. 安装依赖

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

### 3. 配置后端

创建 `backend/.env`：

```env
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB_NAME=workflow_db
CORS_ORIGINS=["http://localhost:3000"]

JWT_SECRET_KEY=PLEASE_CHANGE_ME
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
JWT_ISSUER=tcm-backend
JWT_AUDIENCE=tcm-frontend
```

### 4. 初始化数据库与基础数据

在 `backend` 目录执行：

```bash
cd backend

# 初始化工作流配置 + 默认权限/角色
python app/init_mongodb.py

# 可选：单独初始化 RBAC（幂等）
python scripts/init_rbac.py
```

创建演示用户（用于登录页快速体验按钮）：

```bash
python scripts/create_user.py --user-id admin001 --username "系统管理员" --password 'Admin@123' --roles ADMIN --email admin@example.com --upsert
python scripts/create_user.py --user-id tpm001 --username "张三（TPM）" --password 'TPM@123' --roles TPM --email tpm@example.com --upsert
python scripts/create_user.py --user-id tester001 --username "李四（测试工程师）" --password 'Test@123' --roles TESTER --email tester@example.com --upsert
python scripts/create_user.py --user-id auto001 --username "王五（自动化工程师）" --password 'Auto@123' --roles AUTOMATION --email automation@example.com --upsert
```

可选：注入模拟测试需求/用例数据。

```bash
python scripts/seed_test_data.py
python scripts/verify_test_data.py
```

### 5. 启动后端

在 `backend` 目录执行：

```bash
python -m app.main
```

启动后可访问：

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

### 6. 启动前端

创建 `frontend/.env`：

```env
VITE_BACKEND_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT_MS=15000
```

启动前端：

```bash
cd frontend
npm run dev
```

默认地址：`http://localhost:3000`

## 登录与演示账号

登录页提供 4 个快速登录按钮，对应账号如下（需提前执行 `create_user.py`）：

| 角色 | user_id | password |
|---|---|---|
| 管理员 | `admin001` | `Admin@123` |
| TPM | `tpm001` | `TPM@123` |
| 测试工程师 | `tester001` | `Test@123` |
| 自动化工程师 | `auto001` | `Auto@123` |

说明：

- 若未配置 `VITE_BACKEND_API_BASE_URL`，前端会进入无后端模式（仅本地数据演示）。
- 登录页“快速体验演示账户”主要面向后端联调场景。

## API 概览

统一业务前缀：`/api/v1`

- 工作流：`/work-items`
- 测试需求：`/requirements`
- 测试用例：`/test-cases`
- 认证与 RBAC：`/auth`
- 菜单：`/menus`
- 资产：`/assets`

健康检查路由：

- `GET /health`
- `GET /health/ready`
- `GET /health/live`

响应格式示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## 默认角色

`backend/scripts/init_rbac.py` 会初始化以下角色：

- `ADMIN`：全量权限
- `TPM`：需求读写、测试用例读取、工作项读取/流转
- `TESTER`：需求读取、测试用例读写、工作项读取/流转
- `AUTOMATION`：测试用例读写、资产读取、工作项读取

## 测试

在项目根目录执行：

```bash
pytest backend/tests -q
```

## 常见问题

### 1. 登录失败 / 401

- 确认后端已启动：`curl http://localhost:8000/health`
- 确认前端 `VITE_BACKEND_API_BASE_URL` 正确
- 确认账号已通过 `create_user.py` 创建
- 确认 `JWT_SECRET_KEY/JWT_ISSUER/JWT_AUDIENCE` 配置一致

### 2. 前端跨域失败

- 检查 `backend/.env` 的 `CORS_ORIGINS`
- 开发环境建议：`["http://localhost:3000"]`

### 3. MongoDB 初始化失败

- 检查 `MONGO_URI`、`MONGO_DB_NAME`
- 确认 MongoDB 实例可连接
- 检查 `backend/app/configs/*.json` 配置语法

## 文档索引

- 架构规范：`docs/项目架构规范.md`
- 后端接口说明：`docs/后端接口说明.md`
- 认证与登录指南：`docs/认证与登录指南.md`
- 测试字段文档总览：`docs/测试字段文档总览.md`
- 测试设计与 BOM 关联方案：`docs/测试设计与BOM关联方案.md`
- 脚本说明：`backend/scripts/README.md`
