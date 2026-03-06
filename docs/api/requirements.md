# 测试需求 API

## 概述

测试需求模块提供测试需求的全生命周期管理，包括需求的创建、更新、查询和删除等操作。

**基础路径**: `/api/v1/requirements`

## 注意事项

- 所有接口需要 `requirements:read` 或 `requirements:write` 权限
- 使用JWT Token进行身份认证
- req_id字段必须由后端自动生成，前端不应提供此字段

## 数据模型

### TestRequirementDoc

```typescript
interface TestRequirementDoc {
  req_id: string;          // 需求ID（自动生成）
  title: string;           // 需求标题
  description: string;     // 需求描述
  status: string;          // 需求状态
  priority: string;        // 优先级（HIGH/MEDIUM/LOW）
  tpm_owner_id: string;    // TPM负责人ID
  manual_dev_id?: string;  // 手动开发负责人ID
  auto_dev_id?: string;    // 自动化开发负责人ID
  target_release: string;  // 目标发布版本
  category: string;        // 需求类别
  tags: string[];          // 标签列表
  acceptance_criteria: string; // 验收标准
  dependencies: string[];  // 依赖关系
  created_at: string;      // 创建时间
  updated_at: string;      // 更新时间
  created_by: string;      // 创建人
  updated_by: string;      // 更新人
  is_deleted: boolean;     // 是否删除（软删除）
}
```

## 接口详情

### 创建测试需求

创建一个新的测试需求。

```http
POST /api/v1/requirements
```

**权限要求**: `requirements:write`

**认证**: 需要当前用户信息

**请求体**:
```json
{
  "title": "DDR5内存兼容性测试需求",
  "description": "验证DDR5内存在不同品牌主板上的兼容性和性能表现",
  "status": "DRAFT",
  "priority": "HIGH",
  "tpm_owner_id": "tpm_user_001",
  "manual_dev_id": "dev_user_001",
  "auto_dev_id": "auto_user_001",
  "target_release": "v2.1.0",
  "category": "Compatibility",
  "tags": ["DDR5", "Memory", "Compatibility"],
  "acceptance_criteria": "在10个不同品牌主板上完成兼容性测试，通过率>95%",
  "dependencies": ["REQ-001", "REQ-002"]
}
```

**字段说明**:
- `title` (string, required): 需求标题
- `description` (string, required): 需求描述
- `status` (string, optional): 需求状态，默认"DRAFT"
- `priority` (string, optional): 优先级，默认"MEDIUM"
- `tpm_owner_id` (string, required): TPM负责人ID，如未提供则自动设为当前用户
- `manual_dev_id` (string, optional): 手动开发负责人ID
- `auto_dev_id` (string, optional): 自动化开发负责人ID
- `target_release` (string, required): 目标发布版本
- `category` (string, required): 需求类别
- `tags` (string[], optional): 标签列表
- `acceptance_criteria` (string, required): 验收标准
- `dependencies` (string[], optional): 依赖关系

**响应示例**:
```json
{
  "code": 201,
  "message": "Success",
  "data": {
    "req_id": "REQ-20260303-001",
    "title": "DDR5内存兼容性测试需求",
    "description": "验证DDR5内存在不同品牌主板上的兼容性和性能表现",
    "status": "DRAFT",
    "priority": "HIGH",
    "tpm_owner_id": "tpm_user_001",
    "manual_dev_id": "dev_user_001",
    "auto_dev_id": "auto_user_001",
    "target_release": "v2.1.0",
    "category": "Compatibility",
    "tags": ["DDR5", "Memory", "Compatibility"],
    "acceptance_criteria": "在10个不同品牌主板上完成兼容性测试，通过率>95%",
    "dependencies": ["REQ-001", "REQ-002"],
    "created_at": "2026-03-03T11:42:00Z",
    "updated_at": "2026-03-03T11:42:00Z",
    "created_by": "current_user_id",
    "updated_by": "current_user_id",
    "is_deleted": false
  }
}
```

**重要说明**:
- req_id字段由后端自动生成，即使前端提供也会被忽略并重新生成
- 如果tpm_owner_id为空，会自动设置为当前用户ID

### 获取测试需求详情

根据业务主键req_id查询单条需求。

```http
GET /api/v1/requirements/{req_id}
```

**权限要求**: `requirements:read`

**路径参数**:
- `req_id` (string, required): 需求业务主键

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "req_id": "REQ-20260303-001",
    "title": "DDR5内存兼容性测试需求",
    "description": "验证DDR5内存在不同品牌主板上的兼容性和性能表现",
    "status": "DRAFT",
    "priority": "HIGH",
    "tpm_owner_id": "tpm_user_001",
    "manual_dev_id": "dev_user_001",
    "auto_dev_id": "auto_user_001",
    "target_release": "v2.1.0",
    "category": "Compatibility",
    "tags": ["DDR5", "Memory", "Compatibility"],
    "acceptance_criteria": "在10个不同品牌主板上完成兼容性测试，通过率>95%",
    "dependencies": ["REQ-001", "REQ-002"],
    "created_at": "2026-03-03T11:42:00Z",
    "updated_at": "2026-03-03T11:42:00Z",
    "created_by": "current_user_id",
    "updated_by": "current_user_id",
    "is_deleted": false
  }
}
```

### 查询测试需求列表

分页查询需求，支持多种筛选条件。

```http
GET /api/v1/requirements
```

**权限要求**: `requirements:read`

**查询参数**:
- `status` (string, optional): 按状态筛选
- `tpm_owner_id` (string, optional): 按TPM负责人筛选
- `manual_dev_id` (string, optional): 按手动开发负责人筛选
- `auto_dev_id` (string, optional): 按自动化开发负责人筛选
- `limit` (integer, optional): 返回数量限制 (1-200, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    {
      "req_id": "REQ-20260303-001",
      "title": "DDR5内存兼容性测试需求",
      "status": "DRAFT",
      "priority": "HIGH",
      "tpm_owner_id": "tpm_user_001",
      "target_release": "v2.1.0",
      "category": "Compatibility",
      "created_at": "2026-03-03T11:42:00Z",
      "updated_at": "2026-03-03T11:42:00Z"
    }
  ]
}
```

### 更新测试需求

更新测试需求信息。

```http
PUT /api/v1/requirements/{req_id}
```

**权限要求**: `requirements:write`

**路径参数**:
- `req_id` (string, required): 需求业务主键

**请求体**:
```json
{
  "title": "DDR5内存兼容性测试需求（更新）",
  "description": "更新后的需求描述",
  "status": "IN_PROGRESS",
  "priority": "HIGH",
  "target_release": "v2.1.1"
}
```

**更新说明**:
- 仅更新请求中显式提交的字段
- 未提交的字段保持原值
- req_id字段不可更新

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "req_id": "REQ-20260303-001",
    "title": "DDR5内存兼容性测试需求（更新）",
    "description": "更新后的需求描述",
    "status": "IN_PROGRESS",
    "priority": "HIGH",
    "tpm_owner_id": "tpm_user_001",
    "target_release": "v2.1.1",
    "category": "Compatibility",
    "updated_at": "2026-03-03T11:45:00Z",
    "updated_by": "current_user_id"
  }
}
```

### 删除测试需求

删除测试需求（逻辑删除）。

```http
DELETE /api/v1/requirements/{req_id}
```

**权限要求**: `requirements:write`

**路径参数**:
- `req_id` (string, required): 需求业务主键

**说明**: 执行逻辑删除，设置is_deleted为true，服务层会进行关联校验

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "deleted": true
  }
}
```

## 状态流转

### 需求状态

| 状态 | 说明 |
|------|------|
| DRAFT | 草稿 |
| IN_PROGRESS | 进行中 |
| REVIEW | 审核中 |
| APPROVED | 已审核 |
| REJECTED | 已拒绝 |
| COMPLETED | 已完成 |
| CANCELLED | 已取消 |

### 状态流转规则

需求状态流转通常遵循以下规则：
1. DRAFT → IN_PROGRESS（开始执行）
2. IN_PROGRESS → REVIEW（提交审核）
3. REVIEW → APPROVED/REJECTED（审核结果）
4. APPROVED → COMPLETED（标记完成）
5. 任意状态 → CANCELLED（取消需求）

## 使用示例

### 创建和查询需求

```bash
# 1. 创建测试需求
curl -X POST "http://localhost:8000/api/v1/requirements" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "DDR5内存兼容性测试需求",
    "description": "验证DDR5内存在不同品牌主板上的兼容性",
    "tpm_owner_id": "tpm_user_001",
    "target_release": "v2.1.0",
    "category": "Compatibility",
    "acceptance_criteria": "在10个不同品牌主板上完成兼容性测试"
  }'

# 2. 查询需求列表
curl -X GET "http://localhost:8000/api/v1/requirements?status=DRAFT&limit=10" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 获取需求详情
curl -X GET "http://localhost:8000/api/v1/requirements/REQ-20260303-001" \
  -H "Authorization: Bearer your_jwt_token"

# 4. 更新需求
curl -X PUT "http://localhost:8000/api/v1/requirements/REQ-20260303-001" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_PROGRESS",
    "priority": "HIGH"
  }'

# 5. 删除需求
curl -X DELETE "http://localhost:8000/api/v1/requirements/REQ-20260303-001" \
  -H "Authorization: Bearer your_jwt_token"
```

## 最佳实践

### 需求创建
1. 提供清晰、具体的标题和描述
2. 设置合理的优先级
3. 明确验收标准
4. 合理设置依赖关系

### 状态管理
1. 及时更新需求状态
2. 确保状态流转的合理性
3. 在状态变更时更新负责人信息

### 权限控制
1. TPM负责人可以更新自己的需求
2. 管理员可以更新所有需求
3. 普通用户只能查看有权限的需求