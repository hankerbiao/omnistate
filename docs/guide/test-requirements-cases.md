# 测试需求与测试用例管理

## 1. 概述

测试需求（Requirement）和测试用例（TestCase）是 DMLV4 系统的核心业务对象。两者存在关联关系：

- **多对一关系**：多个测试用例可以关联同一个测试需求
- **组件一致性**：测试用例的 `target_components` 必须是需求 `target_components` 的子集
- **优先级规则**：测试用例的优先级不应超过对应需求的优先级级别

## 2. 测试需求（Requirement）

### 2.1 接口列表

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/requirements` | `requirements:write` | 创建测试需求 |
| GET | `/api/v1/requirements` | `requirements:read` | 查询测试需求列表 |
| GET | `/api/v1/requirements/{req_id}` | `requirements:read` | 获取测试需求详情 |
| PUT | `/api/v1/requirements/{req_id}` | `requirements:write` | 更新测试需求 |
| DELETE | `/api/v1/requirements/{req_id}` | `requirements:write` | 删除测试需求 |

### 2.2 字段说明

#### CreateRequirementRequest（创建请求）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 需求简述 |
| description | string | 否 | 需求详细描述，包括业务场景和具体要求 |
| technical_spec | string | 否 | 技术规格说明，包含技术细节和实现要求 |
| target_components | string[] | 否 | 目标组件列表，指定需求涉及的系统组件 |
| firmware_version | string | 否 | 目标固件版本号 |
| priority | string | 否 | 需求优先级，默认 P1，可选值：P0/P1/P2/P3 |
| key_parameters | object[] | 否 | 关键参数列表，包含名称和值 |
| risk_points | string | 否 | 风险点和注意事项说明 |
| tpm_owner_id | string | 否 | 需求创建人/项目经理 ID（为空时默认当前登录用户） |
| manual_dev_id | string | 否 | 手动测试开发人员 ID |
| auto_dev_id | string | 否 | 自动化测试开发人员 ID |
| attachments | object[] | 否 | 附件列表，包含文件名和文件内容等 |

#### RequirementResponse（响应）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 需求唯一标识 ID（MongoDB ObjectId） |
| req_id | string | 需求业务编号（系统生成） |
| workflow_item_id | string | 工作流项目 ID |
| title | string | 需求简述 |
| description | string | 需求详细描述 |
| technical_spec | string | 技术规格说明 |
| target_components | string[] | 目标组件列表 |
| firmware_version | string | 目标固件版本号 |
| priority | string | 需求优先级 |
| key_parameters | object[] | 关键参数列表 |
| risk_points | string | 风险点和注意事项 |
| tpm_owner_id | string | 需求创建人/项目经理 ID |
| manual_dev_id | string | 手动测试开发人员 ID |
| auto_dev_id | string | 自动化测试开发人员 ID |
| status | string | 需求状态 |
| attachments | object[] | 附件列表 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 2.3 请求示例

**创建测试需求**

```http
POST /api/v1/requirements
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "DDR5 内存兼容性测试",
  "description": "验证服务器主板对 DDR5 内存的兼容性",
  "technical_spec": "支持 DDR5-4800 到 DDR5-5600 规格",
  "target_components": [" motherboard", "memory_module", "bios"],
  "firmware_version": "2.3.1",
  "priority": "P0",
  "key_parameters": [
    {"name": "memory_type", "value": "DDR5"},
    {"name": "max_capacity", "value": "256GB"}
  ],
  "risk_points": "需考虑不同厂商内存条的兼容性",
  "tpm_owner_id": "user001"
}
```

**响应**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439011",
    "req_id": "REQ-20240317-0001",
    "workflow_item_id": "WI-20240317-0001",
    "title": "DDR5 内存兼容性测试",
    "description": "验证服务器主板对 DDR5 内存的兼容性",
    "technical_spec": "支持 DDR5-4800 到 DDR5-5600 规格",
    "target_components": ["motherboard", "memory_module", "bios"],
    "firmware_version": "2.3.1",
    "priority": "P0",
    "key_parameters": [
      {"name": "memory_type", "value": "DDR5"},
      {"name": "max_capacity", "value": "256GB"}
    ],
    "risk_points": "需考虑不同厂商内存条的兼容性",
    "tpm_owner_id": "user001",
    "manual_dev_id": null,
    "auto_dev_id": null,
    "status": "DRAFT",
    "attachments": [],
    "created_at": "2024-03-17T10:00:00Z",
    "updated_at": "2024-03-17T10:00:00Z"
  }
}
```

### 2.4 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | 按状态过滤 |
| tpm_owner_id | string | 按项目经理 ID 过滤 |
| manual_dev_id | string | 按手动测试开发人员 ID 过滤 |
| auto_dev_id | string | 按自动化测试开发人员 ID 过滤 |
| limit | int | 返回数量限制，默认 20，最大 200 |
| offset | int | 偏移量，默认 0 |

## 3. 测试用例（TestCase）

### 3.1 接口列表

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/test-cases` | `test_cases:write` | 创建测试用例 |
| GET | `/api/v1/test-cases` | `test_cases:read` | 查询测试用例列表 |
| GET | `/api/v1/test-cases/{case_id}` | `test_cases:read` | 获取测试用例详情 |
| PUT | `/api/v1/test-cases/{case_id}` | `test_cases:write` | 更新测试用例 |
| DELETE | `/api/v1/test-cases/{case_id}` | `test_cases:write` | 删除测试用例 |
| POST | `/api/v1/test-cases/{case_id}/automation-link` | `test_cases:write` | 关联自动化测试用例 |

### 3.2 字段说明

#### 测试步骤（TestCaseStepSchema）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| step_id | string | 是 | 步骤 ID |
| name | string | 是 | 步骤名称 |
| action | string | 是 | 执行动作 |
| expected | string | 是 | 预期结果 |

#### 自动化用例引用（AutomationCaseRefSchema）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| auto_case_id | string | 是 | 自动化用例库 ID |
| version | string | 否 | 自动化用例版本 |

#### CreateTestCaseRequest（创建请求）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ref_req_id | string | 是 | 关联需求 req_id（外键引用） |
| title | string | 是 | 用例名称 |
| version | int | 否 | 用例版本号，默认 1 |
| is_active | bool | 否 | 用例是否激活状态，默认 true |
| change_log | string | 否 | 用例变更日志 |
| owner_id | string | 否 | 用例负责人 ID |
| reviewer_id | string | 否 | 用例审核人 ID |
| auto_dev_id | string | 否 | 自动化开发人员 ID |
| priority | string | 否 | 用例优先级 |
| estimated_duration_sec | int | 否 | 预估执行时间（秒） |
| target_components | string[] | 否 | 目标组件列表 |
| required_env | object | 否 | 所需测试环境配置 |
| tags | string[] | 否 | 用例标签列表 |
| test_category | string | 否 | 测试分类 |
| tooling_req | string[] | 否 | 测试工具需求列表 |
| is_destructive | bool | 否 | 是否为破坏性测试，默认 false |
| pre_condition | string | 否 | 前置条件 |
| post_condition | string | 否 | 后置条件 |
| cleanup_steps | object[] | 否 | 清理步骤列表 |
| steps | object[] | 否 | 测试执行步骤列表 |
| is_need_auto | bool | 否 | 是否需要自动化，默认 false |
| is_automated | bool | 否 | 是否已实现自动化，默认 false |
| automation_type | string | 否 | 自动化类型 |
| script_entity_id | string | 否 | 脚本实体 ID |
| automation_case_ref | object | 否 | 自动化用例引用 |
| risk_level | string | 否 | 风险等级 |
| failure_analysis | string | 否 | 失败分析 |
| confidentiality | string | 否 | 保密等级 |
| visibility_scope | string | 否 | 可见范围 |
| attachments | object[] | 否 | 附件列表 |
| custom_fields | object | 否 | 自定义字段 |
| deprecation_reason | string | 否 | 弃用原因 |
| approval_history | object[] | 否 | 审批历史 |

#### TestCaseResponse（响应）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 用例唯一标识 ID |
| case_id | string | 用例业务编号 |
| ref_req_id | string | 关联需求 req_id |
| workflow_item_id | string | 工作流项目 ID |
| title | string | 用例名称 |
| version | int | 用例版本号 |
| is_active | bool | 用例是否激活状态 |
| change_log | string | 用例变更日志 |
| status | string | 用例状态 |
| owner_id | string | 用例负责人 ID |
| reviewer_id | string | 用例审核人 ID |
| auto_dev_id | string | 自动化开发人员 ID |
| priority | string | 用例优先级 |
| estimated_duration_sec | int | 预估执行时间（秒） |
| target_components | string[] | 目标组件列表 |
| required_env | object | 所需测试环境配置 |
| tags | string[] | 用例标签列表 |
| test_category | string | 测试分类 |
| tooling_req | string[] | 测试工具需求列表 |
| is_destructive | bool | 是否为破坏性测试 |
| pre_condition | string | 前置条件 |
| post_condition | string | 后置条件 |
| cleanup_steps | object[] | 清理步骤列表 |
| steps | object[] | 测试执行步骤列表 |
| is_need_auto | bool | 是否需要自动化 |
| is_automated | bool | 是否已实现自动化 |
| automation_type | string | 自动化类型 |
| script_entity_id | string | 脚本实体 ID |
| automation_case_ref | object | 自动化用例引用 |
| risk_level | string | 风险等级 |
| failure_analysis | string | 失败分析 |
| confidentiality | string | 保密等级 |
| visibility_scope | string | 可见范围 |
| attachments | object[] | 附件列表 |
| custom_fields | object | 自定义字段 |
| deprecation_reason | string | 弃用原因 |
| approval_history | object[] | 审批历史 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 3.3 请求示例

**创建测试用例**

```http
POST /api/v1/test-cases
Authorization: Bearer <token>
Content-Type: application/json

{
  "ref_req_id": "REQ-20240317-0001",
  "title": "DDR5 内存容量识别测试",
  "version": 1,
  "owner_id": "user002",
  "reviewer_id": "user003",
  "priority": "P1",
  "estimated_duration_sec": 600,
  "target_components": ["motherboard", "memory_module"],
  "tags": ["DDR5", "容量测试", "基础验证"],
  "test_category": "功能测试",
  "is_destructive": false,
  "pre_condition": "服务器断电，安装 DDR5 内存模块",
  "post_condition": "恢复原始配置",
  "steps": [
    {
      "step_id": "step_001",
      "name": "安装内存",
      "action": "将 DDR5 内存模块安装到主板 DIMM 槽位",
      "expected": "内存模块牢固安装到位"
    },
    {
      "step_id": "step_002",
      "name": "开机检查",
      "action": "启动服务器，进入 BIOS",
      "expected": "BIOS 中正确识别内存容量"
    }
  ],
  "is_need_auto": true,
  "is_automated": false
}
```

**响应**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439012",
    "case_id": "TC-20240317-0001",
    "ref_req_id": "REQ-20240317-0001",
    "title": "DDR5 内存容量识别测试",
    "version": 1,
    "is_active": true,
    "status": "DRAFT",
    "owner_id": "user002",
    "reviewer_id": "user003",
    "auto_dev_id": null,
    "priority": "P1",
    "estimated_duration_sec": 600,
    "target_components": ["motherboard", "memory_module"],
    "required_env": {},
    "tags": ["DDR5", "容量测试", "基础验证"],
    "test_category": "功能测试",
    "tooling_req": [],
    "is_destructive": false,
    "pre_condition": "服务器断电，安装 DDR5 内存模块",
    "post_condition": "恢复原始配置",
    "cleanup_steps": [],
    "steps": [
      {
        "step_id": "step_001",
        "name": "安装内存",
        "action": "将 DDR5 内存模块安装到主板 DIMM 槽位",
        "expected": "内存模块牢固安装到位"
      },
      {
        "step_id": "step_002",
        "name": "开机检查",
        "action": "启动服务器，进入 BIOS",
        "expected": "BIOS 中正确识别内存容量"
      }
    ],
    "is_need_auto": true,
    "is_automated": false,
    "created_at": "2024-03-17T10:00:00Z",
    "updated_at": "2024-03-17T10:00:00Z"
  }
}
```

### 3.4 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| ref_req_id | string | 按关联需求过滤 |
| status | string | 按状态过滤 |
| owner_id | string | 按负责人 ID 过滤 |
| reviewer_id | string | 按审核人 ID 过滤 |
| priority | string | 按优先级过滤 |
| is_active | boolean | 按激活状态过滤 |
| limit | int | 返回数量限制，默认 20，最大 200 |
| offset | int | 偏移量，默认 0 |

### 3.5 关联自动化测试用例

**请求**

```http
POST /api/v1/test-cases/TC-20240317-0001/automation-link
Authorization: Bearer <token>
Content-Type: application/json

{
  "auto_case_id": "AUTO-001",
  "version": "1.2.0"
}
```

## 4. 自动化测试用例（AutomationTestCase）

自动化测试用例是独立于手动测试用例的自动化脚本库，用于存储自动化测试脚本的元数据信息。

### 4.1 接口列表

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/automation-test-cases` | `test_cases:write` | 创建自动化测试用例 |
| GET | `/api/v1/automation-test-cases` | `test_cases:read` | 查询自动化测试用例列表 |
| GET | `/api/v1/automation-test-cases/{auto_case_id}` | `test_cases:read` | 获取自动化测试用例详情 |

### 4.2 字段说明

#### CreateAutomationTestCaseRequest（创建请求）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 自动化用例名称 |
| auto_case_id | string | 否 | 自动化用例业务编号（可选，默认由后端生成） |
| version | string | 否 | 自动化用例版本，默认 1.0.0 |
| status | string | 否 | 状态，默认 ACTIVE，可选值：ACTIVE/DEPRECATED |
| framework | string | 否 | 自动化框架（如 pytest、robot 等） |
| automation_type | string | 否 | 自动化类型 |
| repo_url | string | 否 | 脚本仓库地址 |
| repo_branch | string | 否 | 默认分支 |
| script_entity_id | string | 否 | 脚本实体 ID |
| entry_command | string | 否 | 执行入口命令 |
| runtime_env | object | 否 | 运行环境信息 |
| tags | string[] | 否 | 标签列表 |
| maintainer_id | string | 否 | 维护人 ID |
| reviewer_id | string | 否 | 评审人 ID |
| description | string | 否 | 描述 |

#### AutomationTestCaseResponse（响应）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 自动化用例唯一标识 ID |
| auto_case_id | string | 自动化用例业务编号 |
| name | string | 自动化用例名称 |
| version | string | 自动化用例版本 |
| status | string | 状态 |
| framework | string | 自动化框架 |
| automation_type | string | 自动化类型 |
| repo_url | string | 脚本仓库地址 |
| repo_branch | string | 默认分支 |
| script_entity_id | string | 脚本实体 ID |
| entry_command | string | 执行入口命令 |
| runtime_env | object | 运行环境信息 |
| tags | string[] | 标签列表 |
| maintainer_id | string | 维护人 ID |
| reviewer_id | string | 评审人 ID |
| description | string | 描述 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 4.3 请求示例

**创建自动化测试用例**

```http
POST /api/v1/automation-test-cases
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "DDR5 内存容量自动化测试",
  "version": "1.2.0",
  "status": "ACTIVE",
  "framework": "pytest",
  "automation_type": "功能测试",
  "repo_url": "https://gitlab.example.com/auto-tests/ddr5-tests",
  "repo_branch": "main",
  "script_entity_id": "script-001",
  "entry_command": "pytest tests/ddr5_capacity.py -v",
  "runtime_env": {
    "python_version": "3.10",
    "dependencies": ["pytest", "psutil"]
  },
  "tags": ["DDR5", "自动化", "容量测试"],
  "maintainer_id": "user002",
  "description": "DDR5 内存容量识别自动化测试脚本"
}
```

**响应**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439013",
    "auto_case_id": "AUTO-20240317-0001",
    "name": "DDR5 内存容量自动化测试",
    "version": "1.2.0",
    "status": "ACTIVE",
    "framework": "pytest",
    "automation_type": "功能测试",
    "repo_url": "https://gitlab.example.com/auto-tests/ddr5-tests",
    "repo_branch": "main",
    "script_entity_id": "script-001",
    "entry_command": "pytest tests/ddr5_capacity.py -v",
    "runtime_env": {
      "python_version": "3.10",
      "dependencies": ["pytest", "psutil"]
    },
    "tags": ["DDR5", "自动化", "容量测试"],
    "maintainer_id": "user002",
    "reviewer_id": null,
    "description": "DDR5 内存容量识别自动化测试脚本",
    "created_at": "2024-03-17T10:00:00Z",
    "updated_at": "2024-03-17T10:00:00Z"
  }
}
```

### 4.4 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| framework | string | 按自动化框架过滤 |
| automation_type | string | 按自动化类型过滤 |
| status | string | 按状态过滤（ACTIVE/DEPRECATED） |
| maintainer_id | string | 按维护人 ID 过滤 |
| limit | int | 返回数量限制，默认 20，最大 200 |
| offset | int | 偏移量，默认 0 |

## 5. 字段关联说明

### 5.1 需求与用例的关联字段

| 需求字段 | 用例字段 | 关联规则 |
|----------|----------|----------|
| req_id | ref_req_id | 外键引用，一个需求可关联多个用例 |
| target_components | target_components | 用例必须是需求的子集 |
| priority | priority | 用例优先级不应超过需求优先级 |

### 5.2 业务规则

1. **多对一关系**：多个测试用例可以关联同一个测试需求
2. **组件一致性**：测试用例的 `target_components` 必须是需求 `target_components` 的子集或完全一致
3. **优先级规则**：测试用例的 `priority` 建议不超过需求的优先级（如：需求为 P0，用例最高为 P1）
4. **人员独立性**：人员字段在需求和用例层面不一定是同一个人
5. **自动化关联**：测试用例通过 `automation_case_ref` 关联自动化测试用例

## 6. 统一响应格式

所有接口统一返回以下格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 0 表示成功，非 0 表示失败 |
| message | string | 消息描述 |
| data | object | 响应数据 |

## 7. 错误码说明

| code | 说明 |
|------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如重复创建） |