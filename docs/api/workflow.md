# 工作流管理 API

## 概述

工作流管理模块提供基于配置的业务事项状态流转功能，支持JSON配置的流程定义和灵活的状态机。

**基础路径**: `/api/v1/work-items`

## 注意事项

- 所有接口需要 `work_items:read` 或 `work_items:write` 权限
- 支持状态流转的接口需要 `work_items:transition` 权限
- 使用JWT Token进行身份认证

## 流程状态管理

### 获取事项类型列表

获取系统中定义的所有业务事项类型。

```http
GET /api/v1/work-items/types
```

**权限要求**: `work_items:read`

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    {
      "code": "REQUIREMENT",
      "name": "需求"
    },
    {
      "code": "TEST_CASE",
      "name": "测试用例"
    }
  ]
}
```

### 获取流程状态列表

获取系统中定义的所有流程状态。

```http
GET /api/v1/work-items/states
```

**权限要求**: `work_items:read`

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    {
      "code": "DRAFT",
      "name": "草稿",
      "is_end": false
    },
    {
      "code": "PENDING_REVIEW",
      "name": "待审核",
      "is_end": false
    },
    {
      "code": "APPROVED",
      "name": "已审核",
      "is_end": true
    }
  ]
}
```

### 获取流转配置

获取指定类型的所有流转配置规则。

```http
GET /api/v1/work-items/configs?type_code=REQUIREMENT
```

**权限要求**: `work_items:read`

**查询参数**:
- `type_code` (string, required): 事项类型编码

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    {
      "type_code": "REQUIREMENT",
      "from_state": "DRAFT",
      "action": "SUBMIT",
      "to_state": "PENDING_REVIEW",
      "target_owner_strategy": "TO_SPECIFIC_USER",
      "required_fields": ["priority", "target_owner_id"]
    }
  ]
}
```

## 事项 CRUD 操作

### 创建业务事项

创建一个新的业务事项。

```http
POST /api/v1/work-items
```

**权限要求**: `work_items:write`

**请求体**:
```json
{
  "type_code": "REQUIREMENT",
  "title": "DDR5内存兼容性测试需求",
  "content": "测试DDR5内存在不同主板上的兼容性",
  "creator_id": "user123",
  "parent_item_id": null
}
```

**字段说明**:
- `type_code` (string, required): 事项类型，如"REQUIREMENT"、"TEST_CASE"
- `title` (string, required): 事项标题
- `content` (string, optional): 事项内容
- `creator_id` (string, required): 创建人ID
- `parent_item_id` (string, optional): 父事项ID，支持层级关系

**响应示例**:
```json
{
  "code": 201,
  "message": "Success",
  "data": {
    "id": "507f1f77bcf86cd799439011",
    "type_code": "REQUIREMENT",
    "title": "DDR5内存兼容性测试需求",
    "content": "测试DDR5内存在不同主板上的兼容性",
    "current_state": "DRAFT",
    "current_owner_id": "user123",
    "creator_id": "user123",
    "created_at": "2026-03-03T11:42:00Z",
    "updated_at": "2026-03-03T11:42:00Z"
  }
}
```

### 获取事项列表

查询业务事项列表，支持多种筛选条件。

```http
GET /api/v1/work-items
```

**权限要求**: `work_items:read`

**查询参数**:
- `type_code` (string, optional): 按类型筛选
- `state` (string, optional): 按状态筛选
- `owner_id` (string, optional): 按当前处理人筛选
- `creator_id` (string, optional): 按创建人筛选
- `limit` (integer, optional): 返回数量限制 (1-100, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)

**过滤逻辑**: 若同时传入 `owner_id` 和 `creator_id`，使用OR逻辑（当前处理人是owner_id OR 创建人是creator_id）

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    {
      "id": "507f1f77bcf86cd799439011",
      "type_code": "REQUIREMENT",
      "title": "DDR5内存兼容性测试需求",
      "current_state": "PENDING_REVIEW",
      "current_owner_id": "reviewer456",
      "creator_id": "user123",
      "created_at": "2026-03-03T11:42:00Z",
      "updated_at": "2026-03-03T11:42:00Z"
    }
  ]
}
```

### 获取排序后的事项列表

获取排序后的事项列表。

```http
GET /api/v1/work-items/sorted
```

**权限要求**: `work_items:read`

**查询参数**:
- `type_code` (string, optional): 按类型筛选
- `state` (string, optional): 按状态筛选
- `owner_id` (string, optional): 按当前处理人筛选
- `creator_id` (string, optional): 按创建人筛选
- `limit` (integer, optional): 返回数量限制 (1-100, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)
- `order_by` (string, optional): 排序字段 (created_at/updated_at/title, 默认created_at)
- `direction` (string, optional): 排序方向 (asc/desc, 默认desc)

### 模糊搜索事项

按关键字搜索业务事项。

```http
GET /api/v1/work-items/search?keyword=DDR5
```

**权限要求**: `work_items:read`

**查询参数**:
- `keyword` (string, required): 关键词，搜索标题和内容 (2-100字符)
- `type_code` (string, optional): 按类型筛选
- `state` (string, optional): 按状态筛选
- `owner_id` (string, optional): 按当前处理人筛选
- `creator_id` (string, optional): 按创建人筛选
- `limit` (integer, optional): 返回数量限制 (1-100, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)

**说明**: keyword同时在标题和内容上做模糊匹配（不区分大小写）

### 获取事项详情

根据ID获取业务事项详情。

```http
GET /api/v1/work-items/{item_id}
```

**权限要求**: `work_items:read`

**路径参数**:
- `item_id` (string, required): 事项ID

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "id": "507f1f77bcf86cd799439011",
    "type_code": "REQUIREMENT",
    "title": "DDR5内存兼容性测试需求",
    "content": "测试DDR5内存在不同主板上的兼容性",
    "current_state": "PENDING_REVIEW",
    "current_owner_id": "reviewer456",
    "creator_id": "user123",
    "created_at": "2026-03-03T11:42:00Z",
    "updated_at": "2026-03-03T11:42:00Z"
  }
}
```

### 获取某个需求下的测试用例列表

根据需求ID获取其关联的所有测试用例。

```http
GET /api/v1/work-items/{item_id}/test-cases
```

**权限要求**: `work_items:read`

**路径参数**:
- `item_id` (string, required): 需求ID

**说明**: 若对应的需求不存在或类型不是REQUIREMENT，则返回404

### 获取测试用例所属的需求

根据测试用例ID查找其所属需求。

```http
GET /api/v1/work-items/{item_id}/requirement
```

**权限要求**: `work_items:read`

**路径参数**:
- `item_id` (string, required): 测试用例ID

**说明**: 若事项不是测试用例或不存在，内部会返回None（不抛404）

### 删除事项

删除业务事项（逻辑删除）。

```http
DELETE /api/v1/work-items/{item_id}
```

**权限要求**: `work_items:write`

**路径参数**:
- `item_id` (string, required): 事项ID

**说明**: 底层实现为将is_deleted标记为True，同时写入一条DELETE类型的流转日志

## 状态流转操作

### 执行状态流转

执行单条事项的状态流转。

```http
POST /api/v1/work-items/{item_id}/transition
```

**权限要求**: `work_items:transition`

**路径参数**:
- `item_id` (string, required): 事项ID

**请求体**:
```json
{
  "action": "SUBMIT",
  "operator_id": "user123",
  "form_data": {
    "priority": "HIGH",
    "target_owner_id": "reviewer456"
  }
}
```

**字段说明**:
- `action` (string, required): 流转动作，如"SUBMIT"、"APPROVE"、"REJECT"
- `operator_id` (string, required): 操作人ID
- `form_data` (object, optional): 表单数据，用于满足流转配置中的必填字段要求

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "item_id": "507f1f77bcf86cd799439011",
    "from_state": "DRAFT",
    "to_state": "PENDING_REVIEW",
    "action": "SUBMIT",
    "operator_id": "user123",
    "transition_time": "2026-03-03T11:42:00Z",
    "form_data": {
      "priority": "HIGH",
      "target_owner_id": "reviewer456"
    }
  }
}
```

### 改派任务

改派任务给其他处理人（不改变状态）。

```http
POST /api/v1/work-items/{item_id}/reassign
```

**权限要求**: `work_items:write`

**路径参数**:
- `item_id` (string, required): 事项ID

**查询参数**:
- `operator_id` (string, required): 操作人ID
- `target_owner_id` (string, required): 目标处理人ID
- `remark` (string, optional): 备注信息

### 获取流转历史

获取指定事项的所有流转日志（按时间倒序）。

```http
GET /api/v1/work-items/{item_id}/logs
```

**权限要求**: `work_items:read`

**路径参数**:
- `item_id` (string, required): 事项ID

**查询参数**:
- `limit` (integer, optional): 返回数量限制 (1-200, 默认50)

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    {
      "log_id": "507f1f77bcf86cd799439012",
      "item_id": "507f1f77bcf86cd799439011",
      "from_state": "DRAFT",
      "to_state": "PENDING_REVIEW",
      "action": "SUBMIT",
      "operator_id": "user123",
      "transition_time": "2026-03-03T11:42:00Z",
      "remark": null
    }
  ]
}
```

### 批量获取事项流转日志

批量获取多个事项的流转日志。

```http
GET /api/v1/work-items/logs/batch
```

**权限要求**: `work_items:read`

**查询参数**:
- `item_ids` (string, required): 事项ID列表，逗号分隔，如: id1,id2,id3
- `limit` (integer, optional): 每个事项最多返回的日志数量 (1-100, 默认20)

**用途**: 在列表或看板视图中，一次性加载多个任务的流转历史

### 获取可用的下一步流转

获取指定事项在当前状态下可以执行的所有流转动作。

```http
GET /api/v1/work-items/{item_id}/transitions
```

**权限要求**: `work_items:read`

**路径参数**:
- `item_id` (string, required): 事项ID

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "item_id": "507f1f77bcf86cd799439011",
    "current_state": "DRAFT",
    "available_transitions": [
      {
        "action": "SUBMIT",
        "to_state": "PENDING_REVIEW",
        "required_fields": ["priority", "target_owner_id"],
        "description": "提交审核"
      }
    ]
  }
}
```

## 错误处理

### 常见错误码

| 状态码 | 说明 | 示例 |
|--------|------|------|
| 400 | 请求参数错误 | 缺少必填字段、参数格式错误 |
| 404 | 事项不存在 | item_id对应的事项不存在 |
| 409 | 流转配置冲突 | 指定的action在当前状态下不可执行 |
| 422 | 必填字段缺失 | 流转所需的表单字段未提供 |

### 错误响应示例

```json
{
  "code": 400,
  "message": "流转失败: MissingRequiredFieldError: priority字段为必填项",
  "errors": [
    {
      "field": "form_data.priority",
      "message": "优先级为必填项"
    }
  ],
  "timestamp": "2026-03-03T11:42:00Z"
}
```

## 使用示例

### 完整的流程示例

```bash
# 1. 创建需求
curl -X POST "http://localhost:8000/api/v1/work-items" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "type_code": "REQUIREMENT",
    "title": "DDR5内存兼容性测试需求",
    "content": "测试DDR5内存在不同主板上的兼容性",
    "creator_id": "user123"
  }'

# 2. 获取可用的流转动作
curl -X GET "http://localhost:8000/api/v1/work-items/{item_id}/transitions" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 执行状态流转
curl -X POST "http://localhost:8000/api/v1/work-items/{item_id}/transition" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "SUBMIT",
    "operator_id": "user123",
    "form_data": {
      "priority": "HIGH",
      "target_owner_id": "reviewer456"
    }
  }'

# 4. 查看流转历史
curl -X GET "http://localhost:8000/api/v1/work-items/{item_id}/logs" \
  -H "Authorization: Bearer your_jwt_token"
```