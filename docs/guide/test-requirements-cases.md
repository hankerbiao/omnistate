# 测试需求、测试用例与自动化用例

## 1. 概述

`test_specs` 模块管理三类对象：

- 测试需求 `Requirement`
- 测试用例 `TestCase`
- 自动化测试用例库 `AutomationTestCase`

它们的关系如下：

- 一个需求可关联多个测试用例。
- 测试用例通过 `ref_req_id` 指向需求的 `req_id`。
- 测试用例可以通过 `/automation-link` 关联自动化测试用例库中的记录。

## 2. 测试需求

### 2.1 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/requirements` | `requirements:write` | 创建需求 |
| GET | `/api/v1/requirements` | `requirements:read` | 查询需求列表 |
| GET | `/api/v1/requirements/{req_id}` | `requirements:read` | 查询需求详情 |
| PUT | `/api/v1/requirements/{req_id}` | `requirements:write` | 更新需求 |
| DELETE | `/api/v1/requirements/{req_id}` | `requirements:write` | 删除需求 |

### 2.2 创建请求字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 需求标题 |
| `description` | string | 否 | 详细描述 |
| `technical_spec` | string | 否 | 技术规格 |
| `target_components` | string[] | 否 | 目标组件 |
| `firmware_version` | string | 否 | 固件版本 |
| `priority` | string | 否 | 默认 `P1` |
| `key_parameters` | object[] | 否 | 关键参数列表 |
| `risk_points` | string | 否 | 风险说明 |
| `tpm_owner_id` | string | 否 | TPM/负责人 |
| `manual_dev_id` | string | 否 | 手测负责人 |
| `auto_dev_id` | string | 否 | 自动化负责人 |
| `attachments` | object[] | 否 | 附件列表 |

重要说明：

- Schema 中存在 `req_id` 可选字段，但路由和命令服务都明确要求由后端生成，客户端不应传入。

### 2.3 响应字段

`RequirementResponse` 主要包括：

- `id`
- `req_id`
- `workflow_item_id`
- `title`
- `description`
- `technical_spec`
- `target_components`
- `firmware_version`
- `priority`
- `key_parameters`
- `risk_points`
- `tpm_owner_id`
- `manual_dev_id`
- `auto_dev_id`
- `status`
- `attachments`
- `created_at`
- `updated_at`

### 2.4 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | string | 按状态过滤 |
| `tpm_owner_id` | string | 按 TPM 过滤 |
| `manual_dev_id` | string | 按手测负责人过滤 |
| `auto_dev_id` | string | 按自动化负责人过滤 |
| `limit` | int | 默认 20，最大 200 |
| `offset` | int | 默认 0 |

## 3. 测试用例

### 3.1 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/test-cases` | `test_cases:write` | 创建用例 |
| GET | `/api/v1/test-cases` | `test_cases:read` | 查询用例列表 |
| GET | `/api/v1/test-cases/{case_id}` | `test_cases:read` | 查询用例详情 |
| PUT | `/api/v1/test-cases/{case_id}` | `test_cases:write` | 更新用例 |
| DELETE | `/api/v1/test-cases/{case_id}` | `test_cases:write` | 删除用例 |
| POST | `/api/v1/test-cases/{case_id}/automation-link` | `test_cases:write` | 关联自动化用例 |

### 3.2 创建请求字段

核心字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ref_req_id` | string | 是 | 关联需求编号 |
| `title` | string | 是 | 用例标题 |
| `version` | int | 否 | 默认 1 |
| `is_active` | bool | 否 | 默认 `true` |
| `owner_id` | string | 否 | 用例负责人 |
| `reviewer_id` | string | 否 | 审核人 |
| `auto_dev_id` | string | 否 | 自动化负责人 |
| `priority` | string | 否 | 优先级 |
| `estimated_duration_sec` | int | 否 | 预估执行时长 |
| `target_components` | string[] | 否 | 目标组件 |
| `required_env` | object | 否 | 所需环境 |
| `tags` | string[] | 否 | 标签 |
| `test_category` | string | 否 | 测试分类 |
| `tooling_req` | string[] | 否 | 工具依赖 |
| `is_destructive` | bool | 否 | 是否破坏性测试 |
| `pre_condition` | string | 否 | 前置条件 |
| `post_condition` | string | 否 | 后置条件 |
| `cleanup_steps` | object[] | 否 | 清理步骤 |
| `steps` | object[] | 否 | 执行步骤 |
| `is_need_auto` | bool | 否 | 是否需自动化 |
| `is_automated` | bool | 否 | 是否已自动化 |
| `automation_type` | string | 否 | 自动化类型 |
| `script_entity_id` | string | 否 | 脚本实体 ID |
| `automation_case_ref` | object | 否 | 自动化引用 |
| `risk_level` | string | 否 | 风险等级 |
| `failure_analysis` | string | 否 | 失败分析 |
| `confidentiality` | string | 否 | 保密级别 |
| `visibility_scope` | string | 否 | 可见范围 |
| `attachments` | object[] | 否 | 附件 |
| `custom_fields` | object | 否 | 自定义字段 |
| `deprecation_reason` | string | 否 | 弃用原因 |
| `approval_history` | object[] | 否 | 审批历史 |

补充说明：

- Schema 中 `case_id` 是可选字段，但当前设计仍以“后端自动生成”为准。
- `cleanup_steps` 和 `steps` 使用统一步骤结构：`step_id`、`name`、`action`、`expected`。

### 3.3 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `ref_req_id` | string | 按关联需求过滤 |
| `status` | string | 按状态过滤 |
| `owner_id` | string | 按负责人过滤 |
| `reviewer_id` | string | 按审核人过滤 |
| `priority` | string | 按优先级过滤 |
| `is_active` | bool | 按激活状态过滤 |
| `limit` | int | 默认 20，最大 200 |
| `offset` | int | 默认 0 |

### 3.4 更新与删除语义

- 更新接口是 `PUT`，但代码实际采用“只更新显式提交字段”的部分更新语义。
- 当请求体没有任何更新字段时，返回 `400 no fields to update`。
- 删除为逻辑删除，由服务层处理。

## 4. 自动化测试用例库

### 4.1 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/automation-test-cases` | `test_cases:write` | 创建自动化用例 |
| POST | `/api/v1/automation-test-cases/report` | 无 | 批量上报自动化用例配置元数据 |
| GET | `/api/v1/automation-test-cases` | `test_cases:read` | 查询自动化用例列表 |
| GET | `/api/v1/automation-test-cases/{auto_case_id}` | `test_cases:read` | 查询自动化用例详情 |
| GET | `/api/v1/automation-test-cases/by-manual-case-id/{dml_manual_case_id}` | `test_cases:read` | 按平台手工用例编号查询自动化用例 |

### 4.2 创建请求字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dml_manual_case_id` | string | 是 | 关联的平台手工测试用例编号 |
| `name` | string | 是 | 自动化用例名称 |
| `description` | string | 否 | 描述 |
| `status` | string | 否 | 默认 `ACTIVE` |
| `framework` | string | 是 | 自动化框架 |
| `automation_type` | string | 否 | 自动化类型 |
| `script_ref` | object | 是 | 脚本定位信息 |
| `config_path` | string | 否 | 配置文件路径 |
| `script_name` | string | 否 | 脚本文件名 |
| `script_path` | string | 否 | 脚本文件路径 |
| `code_snapshot` | object | 是 | 代码版本快照 |
| `param_spec` | object[] | 否 | 参数定义列表 |
| `tags` | string[] | 否 | 标签 |
| `report_meta` | object | 否 | 上报补充信息 |

说明：

- `auto_case_id` 可在请求中出现，但仍建议由后端生成。
- `script_ref.entity_id` 是执行端最常使用的脚本定位字段。
- `code_snapshot.branch` 是当前自动化用例记录中的代码分支来源。

### 4.3 元数据上报结构

`POST /api/v1/automation-test-cases/report` 当前接收：

- `cases: object[]`
- `summary: object`

其中单条 `cases[]` 元数据的当前常用字段包括：

- `requirement_id`
- `title`
- `project_tag`
- `description`
- `tags`
- `timeout`
- `param_spec`
- `case_id` 或 `dml_manual_case_id`
- `config_path`
- `module`
- `project_scope`
- `script_name`
- `script_path`
- `git_snapshot`

服务会将这批字段规范化为自动化用例库记录，并以 `dml_manual_case_id` 为关联键尝试回链平台手工测试用例。

### 4.4 列表查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `framework` | string | 按框架过滤 |
| `automation_type` | string | 按类型过滤 |
| `status` | string | 按状态过滤 |
| `dml_manual_case_id` | string | 按平台手工用例编号过滤 |
| `limit` | int | 默认 20，最大 200 |
| `offset` | int | 默认 0 |

## 5. 业务规则边界

基于当前 Schema、路由和模块说明，可以确认以下规则：

- 创建或更新测试用例时，会校验 `ref_req_id` 对应需求是否存在。
- 关联自动化用例时，会校验目标自动化用例是否存在。
- 需求与用例都与 workflow 模块联动，响应体中包含 `workflow_item_id`。

以下内容在旧文档中被写成了“强约束”，但当前仓库里更适合视为业务约定，而不是已完全由 API 层强制校验的公开契约：

- 用例 `target_components` 必须是需求 `target_components` 的子集。
- 用例优先级不得高于需求优先级。

## 6. 示例

### 6.1 创建需求

```http
POST /api/v1/requirements
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "DDR5 内存兼容性测试",
  "description": "验证服务器主板对 DDR5 内存的兼容性",
  "technical_spec": "支持 DDR5-4800 到 DDR5-5600 规格",
  "target_components": ["motherboard", "memory_module", "bios"],
  "firmware_version": "2.3.1",
  "priority": "P0"
}
```

成功返回示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439301",
    "req_id": "REQ-20260317-0001",
    "workflow_item_id": "67d7d62f1f1f1f1f1f1f1001",
    "title": "DDR5 内存兼容性测试",
    "description": "验证服务器主板对 DDR5 内存的兼容性",
    "technical_spec": "支持 DDR5-4800 到 DDR5-5600 规格",
    "target_components": ["motherboard", "memory_module", "bios"],
    "firmware_version": "2.3.1",
    "priority": "P0",
    "key_parameters": [],
    "risk_points": null,
    "tpm_owner_id": "admin",
    "manual_dev_id": null,
    "auto_dev_id": null,
    "status": "DRAFT",
    "attachments": [],
    "created_at": "2026-03-17T12:20:00Z",
    "updated_at": "2026-03-17T12:20:00Z"
  }
}
```

查询需求列表示例：

```http
GET /api/v1/requirements?status=DRAFT&limit=20&offset=0
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "id": "507f1f77bcf86cd799439301",
      "req_id": "REQ-20260317-0001",
      "workflow_item_id": "67d7d62f1f1f1f1f1f1f1001",
      "title": "DDR5 内存兼容性测试",
      "description": "验证服务器主板对 DDR5 内存的兼容性",
      "technical_spec": "支持 DDR5-4800 到 DDR5-5600 规格",
      "target_components": ["motherboard", "memory_module", "bios"],
      "firmware_version": "2.3.1",
      "priority": "P0",
      "key_parameters": [],
      "risk_points": null,
      "tpm_owner_id": "admin",
      "manual_dev_id": null,
      "auto_dev_id": null,
      "status": "DRAFT",
      "attachments": [],
      "created_at": "2026-03-17T12:20:00Z",
      "updated_at": "2026-03-17T12:20:00Z"
    }
  ]
}
```

### 6.2 创建测试用例

```http
POST /api/v1/test-cases
Authorization: Bearer <token>
Content-Type: application/json

{
  "ref_req_id": "REQ-20260317-0001",
  "title": "DDR5 内存容量识别测试",
  "steps": [
    {
      "step_id": "S1",
      "name": "安装内存",
      "action": "安装 4 条 DDR5 内存并开机",
      "expected": "系统可正常识别容量"
    }
  ]
}
```

成功返回示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439302",
    "case_id": "TC-20260317-0001",
    "ref_req_id": "REQ-20260317-0001",
    "workflow_item_id": "67d7d62f1f1f1f1f1f1f1002",
    "title": "DDR5 内存容量识别测试",
    "version": 1,
    "is_active": true,
    "change_log": null,
    "status": "DRAFT",
    "owner_id": null,
    "reviewer_id": null,
    "auto_dev_id": null,
    "priority": null,
    "estimated_duration_sec": null,
    "target_components": [],
    "required_env": {},
    "tags": [],
    "test_category": null,
    "tooling_req": [],
    "is_destructive": false,
    "pre_condition": null,
    "post_condition": null,
    "cleanup_steps": [],
    "steps": [
      {
        "step_id": "S1",
        "name": "安装内存",
        "action": "安装 4 条 DDR5 内存并开机",
        "expected": "系统可正常识别容量"
      }
    ],
    "is_need_auto": false,
    "is_automated": false,
    "automation_type": null,
    "script_entity_id": null,
    "automation_case_ref": null,
    "risk_level": null,
    "failure_analysis": null,
    "confidentiality": null,
    "visibility_scope": null,
    "attachments": [],
    "custom_fields": {},
    "deprecation_reason": null,
    "approval_history": [],
    "created_at": "2026-03-17T12:25:00Z",
    "updated_at": "2026-03-17T12:25:00Z"
  }
}
```

查询用例详情示例：

```http
GET /api/v1/test-cases/TC-20260317-0001
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439302",
    "case_id": "TC-20260317-0001",
    "ref_req_id": "REQ-20260317-0001",
    "workflow_item_id": "67d7d62f1f1f1f1f1f1f1002",
    "title": "DDR5 内存容量识别测试",
    "version": 1,
    "is_active": true,
    "change_log": null,
    "status": "DRAFT",
    "owner_id": null,
    "reviewer_id": null,
    "auto_dev_id": null,
    "priority": null,
    "estimated_duration_sec": null,
    "target_components": [],
    "required_env": {},
    "tags": [],
    "test_category": null,
    "tooling_req": [],
    "is_destructive": false,
    "pre_condition": null,
    "post_condition": null,
    "cleanup_steps": [],
    "steps": [
      {
        "step_id": "S1",
        "name": "安装内存",
        "action": "安装 4 条 DDR5 内存并开机",
        "expected": "系统可正常识别容量"
      }
    ],
    "is_need_auto": false,
    "is_automated": false,
    "automation_type": null,
    "script_entity_id": null,
    "automation_case_ref": null,
    "risk_level": null,
    "failure_analysis": null,
    "confidentiality": null,
    "visibility_scope": null,
    "attachments": [],
    "custom_fields": {},
    "deprecation_reason": null,
    "approval_history": [],
    "created_at": "2026-03-17T12:25:00Z",
    "updated_at": "2026-03-17T12:25:00Z"
  }
}
```

### 6.3 关联自动化用例

```http
POST /api/v1/test-cases/TC-20260317-0001/automation-link
Authorization: Bearer <token>
Content-Type: application/json

{
  "auto_case_id": "ATC-20260317-0001",
  "version": "1.0.0"
}
```

成功返回示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439302",
    "case_id": "TC-20260317-0001",
    "ref_req_id": "REQ-20260317-0001",
    "workflow_item_id": "67d7d62f1f1f1f1f1f1f1002",
    "title": "DDR5 内存容量识别测试",
    "version": 1,
    "is_active": true,
    "change_log": null,
    "status": "DRAFT",
    "owner_id": null,
    "reviewer_id": null,
    "auto_dev_id": null,
    "priority": null,
    "estimated_duration_sec": null,
    "target_components": [],
    "required_env": {},
    "tags": [],
    "test_category": null,
    "tooling_req": [],
    "is_destructive": false,
    "pre_condition": null,
    "post_condition": null,
    "cleanup_steps": [],
    "steps": [
      {
        "step_id": "S1",
        "name": "安装内存",
        "action": "安装 4 条 DDR5 内存并开机",
        "expected": "系统可正常识别容量"
      }
    ],
    "is_need_auto": false,
    "is_automated": false,
    "automation_type": null,
    "script_entity_id": null,
    "automation_case_ref": {
      "auto_case_id": "ATC-20260317-0001",
      "version": "1.0.0"
    },
    "risk_level": null,
    "failure_analysis": null,
    "confidentiality": null,
    "visibility_scope": null,
    "attachments": [],
    "custom_fields": {},
    "deprecation_reason": null,
    "approval_history": [],
    "created_at": "2026-03-17T12:25:00Z",
    "updated_at": "2026-03-17T12:30:00Z"
  }
}
```

创建自动化测试用例库示例：

```http
POST /api/v1/automation-test-cases
Authorization: Bearer <token>
Content-Type: application/json

{
  "dml_manual_case_id": "TC-2026-00018",
  "name": "风扇基础检查自动化测试",
  "framework": "pytest",
  "automation_type": "bmc",
  "script_ref": {
    "entity_id": "tests/universal/suite/fan/001_basic_check/test_fan_basic.py",
    "module": "universal",
    "project_tag": "universal",
    "project_scope": ""
  },
  "config_path": "tests/universal/suite/fan/001_basic_check/config.py",
  "script_name": "test_fan_basic.py",
  "script_path": "tests/universal/suite/fan/001_basic_check/test_fan_basic.py",
  "code_snapshot": {
    "version": "f8a26e1",
    "commit_id": "f8a26e1e118af0cb247daf097cdc8f167848f456",
    "commit_short_id": "f8a26e1",
    "branch": "master",
    "author": "测试用户 <test@example.com>",
    "commit_time": "2026-03-18T03:07:18+00:00",
    "message": "测试提交"
  },
  "param_spec": [
    {
      "__type__": "ConfigField",
      "name": "target_ip",
      "label": "目标 BMC IP 地址",
      "type": "str",
      "default": "192.168.1.100",
      "required": true,
      "description": "被测 BMC 的 IP 地址",
      "extra_props": {}
    }
  ],
  "tags": ["fan", "demo"],
  "report_meta": {
    "requirement_id": "suite-fan-001",
    "author": "auto_qa_01",
    "timeout": 300
  },
  "description": "风扇基础检查自动化脚本"
}
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "507f1f77bcf86cd799439401",
    "auto_case_id": "ATC-20260317-0001",
    "dml_manual_case_id": "TC-2026-00018",
    "name": "风扇基础检查自动化测试",
    "status": "ACTIVE",
    "framework": "pytest",
    "automation_type": "bmc",
    "script_ref": {
      "entity_id": "tests/universal/suite/fan/001_basic_check/test_fan_basic.py",
      "module": "universal",
      "project_tag": "universal",
      "project_scope": ""
    },
    "config_path": "tests/universal/suite/fan/001_basic_check/config.py",
    "script_name": "test_fan_basic.py",
    "script_path": "tests/universal/suite/fan/001_basic_check/test_fan_basic.py",
    "code_snapshot": {
      "version": "f8a26e1",
      "commit_id": "f8a26e1e118af0cb247daf097cdc8f167848f456",
      "commit_short_id": "f8a26e1",
      "branch": "master",
      "author": "测试用户 <test@example.com>",
      "commit_time": "2026-03-18T03:07:18+00:00",
      "message": "测试提交"
    },
    "param_spec": [
      {
        "type_marker": "ConfigField",
        "name": "target_ip",
        "label": "目标 BMC IP 地址",
        "type": "str",
        "default": "192.168.1.100",
        "required": true,
        "options": null,
        "extensions": null,
        "description": "被测 BMC 的 IP 地址",
        "extra_props": {}
      }
    ],
    "tags": ["fan", "demo"],
    "report_meta": {
      "requirement_id": "suite-fan-001",
      "author": "auto_qa_01",
      "timeout": 300
    },
    "description": "风扇基础检查自动化脚本",
    "created_at": "2026-03-17T12:28:00Z",
    "updated_at": "2026-03-17T12:28:00Z"
  }
}
```
