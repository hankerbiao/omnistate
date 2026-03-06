# 测试用例 API

## 概述

测试用例模块提供测试用例的创建、维护和管理功能，支持与测试需求的关联，以及自动化测试用例的集成。

**基础路径**: `/api/v1/test-cases`

## 注意事项

- 所有接口需要 `test_cases:read` 或 `test_cases:write` 权限
- 使用JWT Token进行身份认证
- owner_id字段如果未提供，将自动设置为当前用户ID

## 手动测试用例

### 数据模型

```typescript
interface TestCaseDoc {
  case_id: string;              // 用例ID（自动生成）
  title: string;               // 用例标题
  description: string;         // 用例描述
  ref_req_id: string;          // 关联需求ID
  status: string;              // 用例状态
  priority: string;            // 优先级（HIGH/MEDIUM/LOW）
  owner_id: string;            // 负责人ID
  reviewer_id?: string;        // 审核人ID
  category: string;            // 用例类别
  test_type: string;           // 测试类型（Manual/Auto）
  preconditions: string[];     // 前置条件
  test_steps: TestStep[];      // 测试步骤
  expected_results: string[];  // 期望结果
  tags: string[];              // 标签
  estimated_duration: number;  // 预估时长（分钟）
  is_active: boolean;          // 是否激活
  created_at: string;          // 创建时间
  updated_at: string;          // 更新时间
  created_by: string;          // 创建人
  updated_by: string;          // 更新人
  is_deleted: boolean;         // 是否删除
}

interface TestStep {
  step_number: number;         // 步骤序号
  action: string;              // 测试动作
  expected_result: string;     // 期望结果
  remarks?: string;            // 备注
}
```

### 创建测试用例

创建一个新的测试用例。

```http
POST /api/v1/test-cases
```

**权限要求**: `test_cases:write`

**认证**: 需要当前用户信息

**请求体**:
```json
{
  "title": "DDR5内存兼容性基础功能测试",
  "description": "验证DDR5内存在主板上的基础读写功能",
  "ref_req_id": "REQ-20260303-001",
  "status": "DRAFT",
  "priority": "HIGH",
  "owner_id": "tester_001",
  "category": "Functional",
  "test_type": "Manual",
  "preconditions": ["已安装DDR5内存", "主板支持DDR5"],
  "test_steps": [
    {
      "step_number": 1,
      "action": "插入DDR5内存到主板插槽",
      "expected_result": "内存卡扣正常扣合"
    },
    {
      "step_number": 2,
      "action": "开机进入BIOS",
      "expected_result": "BIOS能正确识别内存容量和频率"
    },
    {
      "step_number": 3,
      "action": "运行内存测试工具",
      "expected_result": "无内存错误报告"
    }
  ],
  "expected_results": ["内存正常工作", "无错误日志"],
  "tags": ["DDR5", "Memory", "Compatibility"],
  "estimated_duration": 30,
  "is_active": true
}
```

**字段说明**:
- `title` (string, required): 用例标题
- `description` (string, required): 用例描述
- `ref_req_id` (string, required): 关联需求ID
- `status` (string, optional): 用例状态，默认"DRAFT"
- `priority` (string, optional): 优先级，默认"MEDIUM"
- `owner_id` (string, optional): 负责人ID，如未提供则自动设为当前用户
- `reviewer_id` (string, optional): 审核人ID
- `category` (string, required): 用例类别
- `test_type` (string, required): 测试类型
- `preconditions` (string[], optional): 前置条件
- `test_steps` (TestStep[], required): 测试步骤数组
- `expected_results` (string[], required): 期望结果数组
- `tags` (string[], optional): 标签数组
- `estimated_duration` (number, optional): 预估时长（分钟）
- `is_active` (boolean, optional): 是否激活，默认true

**响应示例**:
```json
{
  "code": 201,
  "message": "Success",
  "data": {
    "case_id": "TC-20260303-001",
    "title": "DDR5内存兼容性基础功能测试",
    "description": "验证DDR5内存在主板上的基础读写功能",
    "ref_req_id": "REQ-20260303-001",
    "status": "DRAFT",
    "priority": "HIGH",
    "owner_id": "tester_001",
    "category": "Functional",
    "test_type": "Manual",
    "preconditions": ["已安装DDR5内存", "主板支持DDR5"],
    "test_steps": [
      {
        "step_number": 1,
        "action": "插入DDR5内存到主板插槽",
        "expected_result": "内存卡扣正常扣合"
      }
    ],
    "expected_results": ["内存正常工作", "无错误日志"],
    "tags": ["DDR5", "Memory", "Compatibility"],
    "estimated_duration": 30,
    "is_active": true,
    "created_at": "2026-03-03T11:42:00Z",
    "updated_at": "2026-03-03T11:42:00Z",
    "created_by": "current_user_id",
    "updated_by": "current_user_id",
    "is_deleted": false
  }
}
```

### 获取测试用例详情

根据业务主键case_id查询单条用例。

```http
GET /api/v1/test-cases/{case_id}
```

**权限要求**: `test_cases:read`

**路径参数**:
- `case_id` (string, required): 用例业务主键

### 查询测试用例列表

分页查询用例，支持多种筛选条件。

```http
GET /api/v1/test-cases
```

**权限要求**: `test_cases:read`

**查询参数**:
- `ref_req_id` (string, optional): 按关联需求筛选
- `status` (string, optional): 按状态筛选
- `owner_id` (string, optional): 按负责人筛选
- `reviewer_id` (string, optional): 按审核人筛选
- `priority` (string, optional): 按优先级筛选
- `is_active` (boolean, optional): 按激活状态筛选
- `limit` (integer, optional): 返回数量限制 (1-200, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)

### 更新测试用例

更新测试用例信息。

```http
PUT /api/v1/test-cases/{case_id}
```

**权限要求**: `test_cases:write`

**路径参数**:
- `case_id` (string, required): 用例业务主键

### 删除测试用例

删除测试用例（逻辑删除）。

```http
DELETE /api/v1/test-cases/{case_id}
```

**权限要求**: `test_cases:write`

**路径参数**:
- `case_id` (string, required): 用例业务主键

### 关联自动化测试用例

将手动测试用例与自动化测试用例关联。

```http
POST /api/v1/test-cases/{case_id}/automation-link
```

**权限要求**: `test_cases:write`

**路径参数**:
- `case_id` (string, required): 手动测试用例ID

**请求体**:
```json
{
  "auto_case_id": "AUTO-TC-20260303-001",
  "version": "v1.2.0"
}
```

**字段说明**:
- `auto_case_id` (string, required): 自动化测试用例ID
- `version` (string, optional): 自动化用例版本

### 解绑自动化测试用例

解除手动测试用例与自动化测试用例的关联。

```http
DELETE /api/v1/test-cases/{case_id}/automation-link
```

**权限要求**: `test_cases:write`

**路径参数**:
- `case_id` (string, required): 手动测试用例ID

## 自动化测试用例

### 数据模型

```typescript
interface AutomationTestCaseDoc {
  auto_case_id: string;        // 自动化用例ID
  version: string;             // 版本号
  title: string;              // 用例标题
  description: string;        // 用例描述
  framework: string;          // 测试框架（Pytest/Jest/Cypress等）
  status: string;             // 脚本状态
  script_content: string;     // 脚本内容
  script_entity_id: string;   // 脚本实体ID
  tag: string;                // 标签
  maintainer_id: string;      // 维护人ID
  dependencies: string[];     // 依赖关系
  timeout: number;            // 超时时间（秒）
  retry_count: number;        // 重试次数
  created_at: string;         // 创建时间
  updated_at: string;         // 更新时间
  is_deleted: boolean;        // 是否删除
}
```

### 创建自动化测试用例

创建一个新的自动化测试用例。

```http
POST /api/v1/automation-test-cases
```

**权限要求**: `test_cases:write`

**请求体**:
```json
{
  "title": "DDR5内存自动化兼容性测试",
  "description": "自动化测试DDR5内存在各品牌主板上的兼容性",
  "framework": "Pytest",
  "status": "DRAFT",
  "script_content": "import pytest\ndef test_ddr5_compatibility():\n    # 自动化测试逻辑\n    pass",
  "script_entity_id": "SCRIPT-001",
  "tag": "ddr5_memory",
  "maintainer_id": "auto_tester_001",
  "dependencies": ["pytest", "memory_test_lib"],
  "timeout": 300,
  "retry_count": 2
}
```

### 获取自动化测试用例详情

```http
GET /api/v1/automation-test-cases/{auto_case_id}
```

**权限要求**: `test_cases:read`

**路径参数**:
- `auto_case_id` (string, required): 自动化测试用例ID

**查询参数**:
- `version` (string, optional): 自动化用例版本，为空时返回最新版本

### 查询自动化测试用例列表

```http
GET /api/v1/automation-test-cases
```

**权限要求**: `test_cases:read`

**查询参数**:
- `framework` (string, optional): 按测试框架筛选
- `status` (string, optional): 按脚本状态筛选
- `tag` (string, optional): 按标签筛选
- `maintainer_id` (string, optional): 按维护人筛选
- `script_entity_id` (string, optional): 按脚本实体ID筛选
- `limit` (integer, optional): 返回数量限制 (1-200, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)

### 更新自动化测试用例

```http
PUT /api/v1/automation-test-cases/{auto_case_id}
```

**权限要求**: `test_cases:write`

**路径参数**:
- `auto_case_id` (string, required): 自动化测试用例ID

**查询参数**:
- `version` (string, optional): 自动化用例版本，为空时更新最新版本

### 删除自动化测试用例

```http
DELETE /api/v1/automation-test-cases/{auto_case_id}
```

**权限要求**: `test_cases:write`

**路径参数**:
- `auto_case_id` (string, required): 自动化测试用例ID

**查询参数**:
- `version` (string, optional): 自动化用例版本，为空时删除最新版本

## 测试用例状态

### 手动测试用例状态

| 状态 | 说明 |
|------|------|
| DRAFT | 草稿 |
| IN_REVIEW | 审核中 |
| APPROVED | 已审核 |
| REJECTED | 已拒绝 |
| ACTIVE | 激活 |
| INACTIVE | 未激活 |
| DEPRECATED | 已废弃 |

### 自动化测试用例状态

| 状态 | 说明 |
|------|------|
| DRAFT | 草稿 |
| DEVELOPMENT | 开发中 |
| TESTING | 测试中 |
| ACTIVE | 激活 |
| MAINTENANCE | 维护中 |
| DEPRECATED | 已废弃 |

## 用例优先级

| 优先级 | 说明 | 建议执行时机 |
|--------|------|-------------|
| HIGH | 高优先级 | 每次发布必执行 |
| MEDIUM | 中优先级 | 重要功能执行 |
| LOW | 低优先级 | 时间充裕时执行 |

## 使用示例

### 手动测试用例管理

```bash
# 1. 创建测试用例
curl -X POST "http://localhost:8000/api/v1/test-cases" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "DDR5内存兼容性测试",
    "description": "测试DDR5内存基础功能",
    "ref_req_id": "REQ-20260303-001",
    "category": "Functional",
    "test_type": "Manual",
    "test_steps": [
      {
        "step_number": 1,
        "action": "插入内存",
        "expected_result": "内存识别成功"
      }
    ],
    "expected_results": ["无错误"],
    "estimated_duration": 30
  }'

# 2. 查询用例列表
curl -X GET "http://localhost:8000/api/v1/test-cases?ref_req_id=REQ-20260303-001&limit=10" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 关联自动化用例
curl -X POST "http://localhost:8000/api/v1/test-cases/TC-20260303-001/automation-link" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_case_id": "AUTO-TC-001",
    "version": "v1.0.0"
  }'
```

### 自动化测试用例管理

```bash
# 1. 创建自动化用例
curl -X POST "http://localhost:8000/api/v1/automation-test-cases" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "DDR5自动化测试",
    "description": "DDR5内存自动化测试脚本",
    "framework": "Pytest",
    "script_content": "def test_ddr5():\n    pass",
    "tag": "ddr5",
    "maintainer_id": "auto_user_001"
  }'

# 2. 查询自动化用例
curl -X GET "http://localhost:8000/api/v1/automation-test-cases?framework=Pytest" \
  -H "Authorization: Bearer your_jwt_token"
```

## 最佳实践

### 用例设计
1. 用例标题要清晰、具体
2. 测试步骤要详细、可执行
3. 期望结果要明确、可验证
4. 合理设置预估时长

### 关联管理
1. 手动用例与自动化用例要一一对应
2. 定期同步用例版本
3. 及时更新依赖关系

### 状态维护
1. 定期审核用例状态
2. 及时更新过期的用例
3. 废弃不用的用例