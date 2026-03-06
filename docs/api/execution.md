# 测试执行 API

## 概述

测试执行模块提供与外部测试框架的集成能力，支持测试任务下发、进度跟踪、结果收集等功能。

**基础路径**: `/api/v1/execution`

## 注意事项

- 任务下发接口需要 `execution_tasks:write` 权限
- 任务查询接口需要 `execution_tasks:read` 权限
- 支持与外部测试框架的HTTP回调集成

## 数据模型

### ExecutionTaskDoc

```typescript
interface ExecutionTaskDoc {
  task_id: string;              // 任务ID
  task_name: string;            // 任务名称
  description: string;          // 任务描述
  framework: string;            // 测试框架
  test_suite_id: string;        // 测试套件ID
  target_environment: string;   // 目标环境
  priority: string;             // 任务优先级
  dispatch_status: string;      // 下发状态
  overall_status: string;       // 总体状态
  created_by: string;           // 创建人
  assigned_to: string;          // 执行人
  start_time?: string;          // 开始时间
  end_time?: string;            // 结束时间
  progress: number;             // 进度百分比
  callback_url?: string;        // 回调地址
  framework_config: object;     // 框架配置
  test_cases: TestCaseRef[];    // 测试用例列表
  created_at: string;           // 创建时间
  updated_at: string;           // 更新时间
}

interface TestCaseRef {
  case_id: string;              // 测试用例ID
  case_type: string;            // 用例类型（Manual/Auto）
  execution_order: number;      // 执行顺序
  estimated_duration: number;   // 预估时长
  required_duts: string[];      // 需要的DUT设备
}
```

### ExecutionTaskCaseDoc

```typescript
interface ExecutionTaskCaseDoc {
  id: string;                   // 记录ID
  task_id: string;              // 任务ID
  case_id: string;              // 测试用例ID
  case_type: string;            // 用例类型
  status: string;               // 执行状态
  start_time?: string;          // 开始时间
  end_time?: string;            // 结束时间
  actual_duration?: number;     // 实际执行时长
  result: string;               // 执行结果
  error_message?: string;       // 错误信息
  logs: string;                 // 执行日志
  attachments: string[];        // 附件
  created_at: string;           // 创建时间
  updated_at: string;           // 更新时间
}
```

## 接口详情

### 下发测试任务

向外部测试框架下发测试任务。

```http
POST /api/v1/execution/tasks/dispatch
```

**权限要求**: `execution_tasks:write`

**认证**: 需要当前用户信息

**请求体**:
```json
{
  "task_name": "DDR5内存兼容性测试任务",
  "description": "执行DDR5内存在不同平台上的兼容性测试",
  "framework": "pytest",
  "test_suite_id": "TS-DDR5-001",
  "target_environment": "test_lab_01",
  "priority": "HIGH",
  "assigned_to": "tester_001",
  "callback_url": "http://testframework.com/callback/progress",
  "framework_config": {
    "parallel_execution": true,
    "max_workers": 4,
    "timeout": 3600,
    "retry_failed": true
  },
  "test_cases": [
    {
      "case_id": "TC-20260303-001",
      "case_type": "Auto",
      "execution_order": 1,
      "estimated_duration": 30,
      "required_duts": ["DUT-001", "DUT-002"]
    },
    {
      "case_id": "TC-20260303-002",
      "case_type": "Manual",
      "execution_order": 2,
      "estimated_duration": 45,
      "required_duts": ["DUT-001"]
    }
  ]
}
```

**字段说明**:
- `task_name` (string, required): 任务名称
- `description` (string, required): 任务描述
- `framework` (string, required): 测试框架（pytest/jest/cypress等）
- `test_suite_id` (string, required): 测试套件ID
- `target_environment` (string, required): 目标环境
- `priority` (string, optional): 任务优先级，默认"MEDIUM"
- `assigned_to` (string, optional): 执行人ID
- `callback_url` (string, optional): 进度回调地址
- `framework_config` (object, optional): 框架特定配置
- `test_cases` (TestCaseRef[], required): 测试用例列表

**响应示例**:
```json
{
  "code": 201,
  "message": "Success",
  "data": {
    "task_id": "EXEC-20260303-001",
    "task_name": "DDR5内存兼容性测试任务",
    "dispatch_status": "DISPATCHED",
    "overall_status": "PENDING",
    "progress": 0,
    "created_by": "current_user_id",
    "created_at": "2026-03-03T11:42:00Z",
    "framework_response": {
      "framework_task_id": "PYTEST-20260303-001",
      "status": "accepted",
      "message": "任务已接受并开始执行"
    }
  }
}
```

### 查询任务详情

根据任务ID查询任务详情。

```http
GET /api/v1/execution/tasks/{task_id}
```

**权限要求**: `execution_tasks:read`

**路径参数**:
- `task_id` (string, required): 任务ID

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "task_id": "EXEC-20260303-001",
    "task_name": "DDR5内存兼容性测试任务",
    "description": "执行DDR5内存在不同平台上的兼容性测试",
    "framework": "pytest",
    "test_suite_id": "TS-DDR5-001",
    "target_environment": "test_lab_01",
    "priority": "HIGH",
    "dispatch_status": "DISPATCHED",
    "overall_status": "RUNNING",
    "progress": 45,
    "created_by": "current_user_id",
    "assigned_to": "tester_001",
    "start_time": "2026-03-03T11:43:00Z",
    "callback_url": "http://testframework.com/callback/progress",
    "framework_config": {
      "parallel_execution": true,
      "max_workers": 4
    },
    "test_cases_count": 10,
    "completed_cases_count": 4,
    "failed_cases_count": 1,
    "created_at": "2026-03-03T11:42:00Z",
    "updated_at": "2026-03-03T11:50:00Z"
  }
}
```

### 查询任务列表

分页查询任务列表，支持多种筛选条件。

```http
GET /api/v1/execution/tasks
```

**权限要求**: `execution_tasks:read`

**查询参数**:
- `created_by` (string, optional): 按创建人筛选
- `framework` (string, optional): 按测试框架筛选
- `overall_status` (string, optional): 按总体状态筛选
- `dispatch_status` (string, optional): 按下发状态筛选
- `limit` (integer, optional): 返回数量限制 (1-200, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)

**状态值说明**:
- `overall_status`: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
- `dispatch_status`: PENDING, DISPATCHED, ACKNOWLEDGED, FAILED

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    {
      "task_id": "EXEC-20260303-001",
      "task_name": "DDR5内存兼容性测试任务",
      "framework": "pytest",
      "overall_status": "RUNNING",
      "progress": 45,
      "created_by": "current_user_id",
      "assigned_to": "tester_001",
      "created_at": "2026-03-03T11:42:00Z"
    }
  ]
}
```

### 查询任务用例明细

查询指定任务下的测试用例执行明细。

```http
GET /api/v1/execution/tasks/{task_id}/cases
```

**权限要求**: `execution_tasks:read`

**路径参数**:
- `task_id` (string, required): 任务ID

**查询参数**:
- `status` (string, optional): 按执行状态筛选
- `limit` (integer, optional): 返回数量限制 (1-500, 默认50)
- `offset` (integer, optional): 分页偏移 (默认0)

**用例状态值**:
- PENDING, RUNNING, COMPLETED, FAILED, SKIPPED

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": [
    {
      "id": "ETC-20260303-001-001",
      "task_id": "EXEC-20260303-001",
      "case_id": "TC-20260303-001",
      "case_type": "Auto",
      "status": "COMPLETED",
      "start_time": "2026-03-03T11:43:30Z",
      "end_time": "2026-03-03T11:44:15Z",
      "actual_duration": 45,
      "result": "PASSED",
      "error_message": null,
      "logs": "测试执行正常，无异常",
      "attachments": ["logs/test_result.log", "screenshots/test_001.png"]
    }
  ]
}
```

## 进度回调接口

### 接收测试框架进度回报

外部测试框架向系统报告任务执行进度。

```http
POST /api/v1/execution/callbacks/progress
```

**认证**: 使用HTTP Header进行身份验证

**请求头**:
```
Content-Type: application/json
X-Framework-Id: pytest
X-Event-Id: event-12345
X-Timestamp: 2026-03-03T11:45:00Z
X-Signature: sha256=signature_hash
```

**请求体**:
```json
{
  "task_id": "EXEC-20260303-001",
  "framework_task_id": "PYTEST-20260303-001",
  "event_type": "progress_update",
  "timestamp": "2026-03-03T11:45:00Z",
  "data": {
    "overall_progress": 65,
    "overall_status": "RUNNING",
    "current_test_case": {
      "case_id": "TC-20260303-003",
      "case_name": "DDR5压力测试",
      "status": "RUNNING",
      "start_time": "2026-03-03T11:44:30Z",
      "progress": 30
    },
    "completed_cases": 6,
    "failed_cases": 1,
    "total_cases": 10,
    "execution_stats": {
      "passed": 5,
      "failed": 1,
      "skipped": 0
    }
  }
}
```

**事件类型**:
- `task_started`: 任务开始
- `case_started`: 用例开始
- `case_completed`: 用例完成
- `case_failed`: 用例失败
- `progress_update`: 进度更新
- `task_completed`: 任务完成

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "received": true,
    "ack_id": "ACK-20260303-001",
    "next_expected_event": "continue",
    "framework_response": "progress noted"
  }
}
```

## 状态管理

### 任务状态流转

```
PENDING → DISPATCHED → ACKNOWLEDGED → RUNNING → COMPLETED/FAILED/CANCELLED
  ↓                                                              ↑
  └─────────────── FAILED (下发失败) ←────────────────────────────┘
```

### 进度更新流程

1. 任务创建后状态为PENDING
2. 下发成功后状态变为DISPATCHED
3. 外部框架确认接收后状态变为ACKNOWLEDGED
4. 开始执行后状态变为RUNNING
5. 执行完成后根据结果变为COMPLETED或FAILED
6. 可手动取消任务，状态变为CANCELLED

## 使用示例

### 任务下发和监控

```bash
# 1. 下发测试任务
curl -X POST "http://localhost:8000/api/v1/execution/tasks/dispatch" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "DDR5内存测试",
    "framework": "pytest",
    "test_suite_id": "TS-001",
    "target_environment": "lab_01",
    "test_cases": [
      {
        "case_id": "TC-001",
        "case_type": "Auto",
        "estimated_duration": 30
      }
    ]
  }'

# 2. 查询任务状态
curl -X GET "http://localhost:8000/api/v1/execution/tasks/EXEC-20260303-001" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 查询任务列表
curl -X GET "http://localhost:8000/api/v1/execution/tasks?overall_status=RUNNING&limit=5" \
  -H "Authorization: Bearer your_jwt_token"

# 4. 查询用例执行明细
curl -X GET "http://localhost:8000/api/v1/execution/tasks/EXEC-20260303-001/cases?status=RUNNING" \
  -H "Authorization: Bearer your_jwt_token"
```

### 外部框架回调

```python
# Python示例：测试框架回调进度
import requests
import hashlib
import hmac

def callback_progress(task_data):
    # 准备回调数据
    payload = {
        "task_id": "EXEC-20260303-001",
        "event_type": "progress_update",
        "timestamp": "2026-03-03T11:45:00Z",
        "data": {
            "overall_progress": 50,
            "overall_status": "RUNNING",
            "current_test_case": {
                "case_id": "TC-002",
                "status": "RUNNING"
            }
        }
    }

    # 计算签名
    secret = "your_callback_secret"
    signature = hmac.new(
        secret.encode('utf-8'),
        json.dumps(payload).encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 发送回调
    headers = {
        "Content-Type": "application/json",
        "X-Framework-Id": "pytest",
        "X-Signature": f"sha256={signature}"
    }

    response = requests.post(
        "http://localhost:8000/api/v1/execution/callbacks/progress",
        json=payload,
        headers=headers
    )

    return response.json()
```

## 最佳实践

### 任务设计
1. 合理设置任务粒度，避免过大或过小的任务
2. 明确指定测试环境和依赖条件
3. 提供清晰的回调地址和签名验证

### 进度监控
1. 定期查询任务状态
2. 及时处理失败的任务
3. 关注用例执行明细

### 错误处理
1. 实现重试机制
2. 记录详细的执行日志
3. 及时更新任务状态

### 安全考虑
1. 验证回调请求的签名
2. 限制回调接口的访问权限
3. 敏感信息加密传输