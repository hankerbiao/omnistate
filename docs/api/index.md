# API 接口概览

## 系统架构

DMLV4 采用前后端分离架构，后端基于 FastAPI + MongoDB 构建，提供 RESTful API 服务。

## 基础信息

- **API 基础地址**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Token (Bearer Token)
- **数据格式**: JSON
- **字符编码**: UTF-8

## 接口分类

### 核心业务模块

| 模块 | 前缀 | 说明 |
|------|------|------|
| **工作流管理** | `/work-items` | 业务事项的状态流转和流程管理 |
| **测试需求** | `/requirements` | 测试需求的全生命周期管理 |
| **测试用例** | `/test-cases` | 测试用例的创建和维护 |
| **测试执行** | `/execution` | 外部测试框架集成和任务下发 |

### 支撑服务模块

| 模块 | 前缀 | 说明 |
|------|------|------|
| **资产管理** | `/assets` | 硬件部件库和DUT设备管理 |
| **认证授权** | `/auth` | 用户、角色、权限和导航管理 |
| **系统健康** | `/health` | 系统健康检查和状态监控 |

## 通用响应格式

所有API接口均采用统一的响应格式：

```json
{
  "code": 200,
  "message": "Success",
  "data": {},
  "timestamp": "2026-03-03T11:42:00Z"
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 响应状态码，200表示成功 |
| `message` | string | 响应消息 |
| `data` | object/array/null | 响应数据主体 |
| `timestamp` | string | 响应时间戳 |

## 错误处理

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或Token无效 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 数据验证失败 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "code": 400,
  "message": "参数验证失败",
  "errors": [
    {
      "field": "title",
      "message": "标题不能为空"
    }
  ],
  "timestamp": "2026-03-03T11:42:00Z"
}
```

## 分页和查询

### 分页参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `limit` | integer | 返回数量限制 | 20 |
| `offset` | integer | 分页偏移量 | 0 |

### 查询参数

大部分列表接口支持以下查询参数：
- `status`: 状态筛选
- `owner_id`: 负责人筛选
- `creator_id`: 创建人筛选
- `type_code`: 类型筛选（工作流模块）

## 认证流程

1. 使用用户名密码登录获取Token
2. 在后续请求中携带Token进行认证
3. Token有效期由系统配置决定

```bash
# 登录获取Token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your_username",
    "password": "your_password"
  }'

# 使用Token访问接口
curl -X GET "http://localhost:8000/api/v1/work-items" \
  -H "Authorization: Bearer your_jwt_token"
```

## 快速开始

1. [认证授权接口](./auth.md) - 了解如何获取和使用认证Token
2. [工作流管理](./workflow.md) - 学习业务事项的状态流转
3. [测试需求](./requirements.md) - 掌握测试需求的CRUD操作
4. [测试用例](./test-cases.md) - 了解测试用例的管理方式
5. [测试执行](./execution.md) - 学习外部测试框架集成
6. [资产管理](./assets.md) - 掌握硬件资产的管理
7. [系统健康](./health.md) - 监控系统状态