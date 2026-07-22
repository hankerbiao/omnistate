// DML V4 开放平台 · Mock 数据

import type {
  ApiKey,
  Capability,
  CallLog,
  MockUser,
  OverviewStats,
} from "../types";

export const mockUsers: MockUser[] = [
  {
    id: "user_admin",
    username: "admin",
    name: "李彪",
    email: "libiao@dml.local",
    role: "admin",
    team: "DML 平台管理员",
    avatar: "李",
    allowedCapabilityIds: [
      "cap_list_tasks",
      "cap_task_status",
      "cap_task_timeline",
      "cap_dispatch_task",
      "cap_rerun_task",
      "cap_task_biz_logs",
      "cap_list_specs",
      "cap_get_case",
      "cap_case_change_logs",
      "cap_list_requirements",
      "cap_get_requirement",
      "cap_list_projects",
      "cap_get_project",
      "cap_project_stats",
      "cap_project_blockers",
      "cap_project_activities",
      "cap_report",
      "cap_webhook",
    ],
    quota: { enabled: true, monthlyLimit: 500000, rpmLimit: 600, concurrency: 60 },
    mustChangePassword: false,
  },
  {
    id: "user_developer",
    username: "developer",
    name: "王小明",
    email: "xiaoming@dml.local",
    role: "developer",
    team: "质量平台组",
    avatar: "王",
    allowedCapabilityIds: ["cap_list_tasks", "cap_task_status", "cap_report"],
    quota: { enabled: true, monthlyLimit: 100000, rpmLimit: 120, concurrency: 10 },
    mustChangePassword: false,
  },
  {
    id: "user_zhaolei",
    username: "zhaolei",
    name: "赵雷",
    email: "zhaolei@dml.local",
    role: "developer",
    team: "算法平台组",
    avatar: "赵",
    allowedCapabilityIds: ["cap_list_tasks", "cap_task_status", "cap_report", "cap_list_specs"],
    quota: { enabled: false, monthlyLimit: 0, rpmLimit: 0, concurrency: 0 },
    mustChangePassword: false,
  },
];

export const mockApiKeys: ApiKey[] = [
  {
    id: "key_01",
    name: "CI 流水线集成",
    ownerUserId: "user_admin",
    prefix: "dml_live_",
    masked: "dml_live_a1b2••••••••••7f9c",
    status: "active",
    scopes: ["execution_tasks:read"],
    createdAt: "2026-05-12T09:24:00+08:00",
    lastUsedAt: "2026-07-17T11:58:00+08:00",
    callsToday: 1284,
    env: "live",
  },
  {
    id: "key_02",
    name: "数据看板同步",
    ownerUserId: "user_developer",
    prefix: "dml_live_",
    masked: "dml_live_c7d8••••••••••3e21",
    status: "active",
    scopes: ["execution_tasks:read", "test_cases:read", "requirements:read"],
    createdAt: "2026-06-03T14:10:00+08:00",
    lastUsedAt: "2026-07-17T10:32:00+08:00",
    callsToday: 642,
    env: "live",
  },
  {
    id: "key_03",
    name: "本地联调（测试）",
    ownerUserId: "user_developer",
    prefix: "dml_test_",
    masked: "dml_test_9f0a••••••••••b4d6",
    status: "active",
    scopes: ["execution_tasks:read"],
    createdAt: "2026-07-01T16:45:00+08:00",
    lastUsedAt: "2026-07-16T20:11:00+08:00",
    callsToday: 87,
    env: "test",
  },
  {
    id: "key_04",
    name: "旧版报表脚本",
    ownerUserId: "user_zhaolei",
    prefix: "dml_live_",
    masked: "dml_live_5e6f••••••••••88a2",
    status: "revoked",
    scopes: ["execution_tasks:read"],
    createdAt: "2026-02-18T11:00:00+08:00",
    lastUsedAt: "2026-04-28T08:03:00+08:00",
    callsToday: 0,
    env: "live",
  },
];

export const mockCapabilities: Capability[] = [
  {
    id: "cap_list_tasks",
    name: "查询我的测试任务",
    category: "测试任务",
    method: "GET",
    path: "/api/v1/open/execution/tasks/my",
    summary: "分页获取当前密钥所属账号最近创建的自动化测试任务。",
    description:
      "返回当前 API 密钥绑定用户最近创建的测试任务列表，支持 limit 控制返回数量。数据访问范围由密钥 scope 与后端权限共同约束。",
    scope: "execution_tasks:read",
    handler: "proxy",
    upstreamPath: "/api/v1/execution/tasks/my",
    params: [
      { name: "limit", type: "integer", required: false, description: "返回任务数量，范围 1-100，默认 20。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": [
    {
      "task_id": "ET-2026-000128",
      "title": "登录模块回归",
      "status": "running",
      "progress": 0.62,
      "created_at": "2026-07-17T09:12:00+08:00"
    }
  ]
}`,
  },
  {
    id: "cap_task_status",
    name: "查询任务状态",
    category: "测试任务",
    method: "GET",
    path: "/api/v1/open/execution/tasks/{task_id}/status",
    summary: "获取单个测试任务的整体状态与执行进度。",
    description:
      "按任务 ID 查询该测试任务的当前状态、进度、用例通过/失败数量等摘要信息。",
    scope: "execution_tasks:read",
    handler: "proxy",
    upstreamPath: "/api/v1/execution/tasks/{task_id}/status",
    params: [
      { name: "task_id", type: "string", required: true, description: "测试任务 ID，例如 ET-2026-000128。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "task_id": "ET-2026-000128",
    "status": "running",
    "progress": 0.62,
    "total": 120,
    "passed": 71,
    "failed": 3
  }
}`,
  },
  {
    id: "cap_task_timeline",
    name: "查询任务时间线",
    category: "测试任务",
    method: "GET",
    path: "/api/v1/open/execution/tasks/{task_id}/timeline",
    summary: "获取测试任务的业务轨迹与执行事件时间线。",
    description:
      "按任务 ID 返回该任务的状态流转与执行事件时间线，可用 limit 限制事件数量，适合审计与进度追踪。",
    scope: "execution_tasks:read",
    handler: "proxy",
    upstreamPath: "/api/v1/execution/tasks/{task_id}/timeline",
    params: [
      { name: "task_id", type: "string", required: true, description: "测试任务 ID。" },
      { name: "limit", type: "integer", required: false, description: "最多返回事件数量，范围 1-500，默认 100。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "task_id": "ET-2026-000128",
    "events": [
      { "at": "2026-07-17T09:12:00+08:00", "type": "created", "actor": "ci-bot" },
      { "at": "2026-07-17T09:13:20+08:00", "type": "dispatched", "case": "TC-001" }
    ]
  }
}`,
  },
  {
    id: "cap_dispatch_task",
    name: "下发自动化测试任务",
    category: "测试任务",
    method: "POST",
    path: "/api/v1/open/execution/tasks/dispatch",
    summary: "创建并下发一批自动化测试任务。",
    description: "外部 CI/CD 或质量平台可调用此接口下发自动化测试任务，请求体透传给 DML 执行服务。",
    scope: "execution_tasks:write",
    handler: "proxy",
    upstreamPath: "/api/v1/execution/tasks/dispatch",
    params: [
      { name: "body", type: "object", required: true, description: "与 DML 后端 DispatchTaskRequest 保持一致的任务下发请求体。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "task_id": "ET-2026-000129",
    "dispatch_status": "queued"
  }
}`,
  },
  {
    id: "cap_rerun_task",
    name: "重新运行测试任务",
    category: "测试任务",
    method: "POST",
    path: "/api/v1/open/execution/tasks/{task_id}/rerun",
    summary: "基于已有任务快照创建一次重新执行。",
    description: "按任务 ID 重新运行测试任务，请求体透传给 DML 后端的 RerunTaskRequest。",
    scope: "execution_tasks:write",
    handler: "proxy",
    upstreamPath: "/api/v1/execution/tasks/{task_id}/rerun",
    params: [
      { name: "task_id", type: "string", required: true, description: "原始测试任务 ID。" },
      { name: "body", type: "object", required: true, description: "重新执行参数，可包含执行通道、覆盖项等后端支持字段。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "task_id": "ET-2026-000130",
    "source_task_id": "ET-2026-000128"
  }
}`,
  },
  {
    id: "cap_task_biz_logs",
    name: "查询任务业务日志",
    category: "测试任务",
    method: "GET",
    path: "/api/v1/open/execution/tasks/{task_id}/biz-logs",
    summary: "查询 execution 平台侧业务节点轨迹日志。",
    description: "返回指定测试任务的平台业务日志，适合外部系统做审计、排障和执行链路追踪。",
    scope: "execution_tasks:read",
    handler: "proxy",
    upstreamPath: "/api/v1/execution/tasks/{task_id}/biz-logs",
    params: [
      { name: "task_id", type: "string", required: true, description: "测试任务 ID。" },
      { name: "limit", type: "integer", required: false, description: "最多返回日志数量，范围 1-500，默认 200。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": [
    { "node": "TASK_CREATE", "outcome": "success", "message": "task created" }
  ]
}`,
  },
  {
    id: "cap_list_specs",
    name: "读取测试用例",
    category: "测试资产",
    method: "GET",
    path: "/api/v1/open/test-specs/cases",
    summary: "读取测试需求与测试用例目录。",
    description:
      "分页读取测试用例及其关联需求，支持按项目、状态过滤。仅返回密钥授权范围内的数据。",
    scope: "test_cases:read",
    handler: "proxy",
    upstreamPath: "/api/v1/test-cases",
    params: [
      { name: "project_id", type: "string", required: false, description: "项目 ID，过滤指定项目。" },
      { name: "status", type: "string", required: false, description: "用例状态过滤，如 active。" },
      { name: "limit", type: "integer", required: false, description: "返回数量，默认 20。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": [
    {
      "case_id": "TC-2026-0451",
      "title": "验证短信验证码有效期",
      "priority": "P1",
      "status": "active"
    }
  ]
}`,
  },
  {
    id: "cap_get_case",
    name: "读取测试用例详情",
    category: "测试资产",
    method: "GET",
    path: "/api/v1/open/test-specs/cases/{case_id}",
    summary: "按用例 ID 读取测试用例详情。",
    description: "返回单条测试用例的完整字段，包括步骤、优先级、关联需求、标签和状态等信息。",
    scope: "test_cases:read",
    handler: "proxy",
    upstreamPath: "/api/v1/test-cases/{case_id}",
    params: [
      { name: "case_id", type: "string", required: true, description: "测试用例 ID。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "case_id": "TC-2026-0451",
    "title": "验证短信验证码有效期",
    "steps": []
  }
}`,
  },
  {
    id: "cap_case_change_logs",
    name: "读取用例变更记录",
    category: "测试资产",
    method: "GET",
    path: "/api/v1/open/test-specs/cases/{case_id}/change-logs",
    summary: "读取测试用例变更历史。",
    description: "按用例 ID 查询最近的变更记录，适合外部质量门户展示用例审计轨迹。",
    scope: "test_cases:read",
    handler: "proxy",
    upstreamPath: "/api/v1/test-cases/{case_id}/change-logs",
    params: [
      { name: "case_id", type: "string", required: true, description: "测试用例 ID。" },
      { name: "limit", type: "integer", required: false, description: "返回数量，默认 20。" },
      { name: "offset", type: "integer", required: false, description: "分页偏移，默认 0。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "items": [
      { "field": "priority", "old_value": "P2", "new_value": "P1" }
    ],
    "total": 1
  }
}`,
  },
  {
    id: "cap_list_requirements",
    name: "读取测试需求列表",
    category: "测试需求",
    method: "GET",
    path: "/api/v1/open/test-specs/requirements",
    summary: "分页读取测试需求。",
    description: "支持按状态、负责人等条件过滤测试需求，用于外部系统同步需求测试资产。",
    scope: "requirements:read",
    handler: "proxy",
    upstreamPath: "/api/v1/requirements",
    params: [
      { name: "status", type: "string", required: false, description: "需求状态过滤。" },
      { name: "limit", type: "integer", required: false, description: "返回数量，默认 20。" },
      { name: "offset", type: "integer", required: false, description: "分页偏移，默认 0。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": [
    { "req_id": "REQ-2026-0012", "title": "登录安全增强", "status": "DONE" }
  ]
}`,
  },
  {
    id: "cap_get_requirement",
    name: "读取测试需求详情",
    category: "测试需求",
    method: "GET",
    path: "/api/v1/open/test-specs/requirements/{req_id}",
    summary: "按需求 ID 读取测试需求详情。",
    description: "返回单条测试需求的描述、验收标准、风险点和负责人等信息。",
    scope: "requirements:read",
    handler: "proxy",
    upstreamPath: "/api/v1/requirements/{req_id}",
    params: [
      { name: "req_id", type: "string", required: true, description: "测试需求 ID。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "req_id": "REQ-2026-0012",
    "title": "登录安全增强",
    "priority": "P1"
  }
}`,
  },
  {
    id: "cap_list_projects",
    name: "读取项目列表",
    category: "项目",
    method: "GET",
    path: "/api/v1/open/projects",
    summary: "分页读取项目列表。",
    description: "返回 DML 项目列表，支持名称、标识、状态和分页过滤。",
    scope: "projects:read",
    handler: "proxy",
    upstreamPath: "/api/v1/projects",
    params: [
      { name: "name", type: "string", required: false, description: "项目名称模糊搜索。" },
      { name: "key", type: "string", required: false, description: "项目标识模糊搜索。" },
      { name: "status", type: "string", required: false, description: "项目状态。" },
      { name: "page", type: "integer", required: false, description: "页码，默认 1。" },
      { name: "page_size", type: "integer", required: false, description: "每页数量，默认 20。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "items": [{ "project_id": "PROJ-001", "name": "DML V4" }],
    "total": 1
  }
}`,
  },
  {
    id: "cap_get_project",
    name: "读取项目详情",
    category: "项目",
    method: "GET",
    path: "/api/v1/open/projects/{project_id}",
    summary: "读取项目详情及统计摘要。",
    description: "按项目 ID 返回项目基础信息和详情数据。",
    scope: "projects:read",
    handler: "proxy",
    upstreamPath: "/api/v1/projects/{project_id}",
    params: [
      { name: "project_id", type: "string", required: true, description: "项目 ID。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "project_id": "PROJ-001",
    "name": "DML V4",
    "status": "active"
  }
}`,
  },
  {
    id: "cap_project_stats",
    name: "读取项目统计",
    category: "项目",
    method: "GET",
    path: "/api/v1/open/projects/{project_id}/stats",
    summary: "读取项目统计数据。",
    description: "返回项目需求、用例、执行等维度的统计数据。",
    scope: "projects:read",
    handler: "proxy",
    upstreamPath: "/api/v1/projects/{project_id}/stats",
    params: [
      { name: "project_id", type: "string", required: true, description: "项目 ID。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "requirements": 24,
    "test_cases": 180,
    "execution_rate": 0.82
  }
}`,
  },
  {
    id: "cap_project_blockers",
    name: "读取项目风险阻塞项",
    category: "项目",
    method: "GET",
    path: "/api/v1/open/projects/{project_id}/blockers",
    summary: "读取项目风险与阻塞项。",
    description: "返回项目当前风险、阻塞项和待处理问题列表。",
    scope: "projects:read",
    handler: "proxy",
    upstreamPath: "/api/v1/projects/{project_id}/blockers",
    params: [
      { name: "project_id", type: "string", required: true, description: "项目 ID。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": [
    { "title": "P0 用例未完成评审", "severity": "high" }
  ]
}`,
  },
  {
    id: "cap_project_activities",
    name: "读取项目最近动态",
    category: "项目",
    method: "GET",
    path: "/api/v1/open/projects/{project_id}/activities",
    summary: "读取项目最近动态。",
    description: "返回项目最近需求、用例、执行等活动记录，可用 limit 控制返回数量。",
    scope: "projects:read",
    handler: "proxy",
    upstreamPath: "/api/v1/projects/{project_id}/activities",
    params: [
      { name: "project_id", type: "string", required: true, description: "项目 ID。" },
      { name: "limit", type: "integer", required: false, description: "返回数量，默认 20。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": [
    { "type": "test_case.updated", "title": "更新登录回归用例" }
  ]
}`,
  },
  {
    id: "cap_report",
    name: "读取执行报告",
    category: "报告分析",
    method: "GET",
    path: "/api/v1/open/reports/{task_id}",
    summary: "获取指定任务的执行报告与失败分析摘要。",
    description:
      "返回测试任务的执行报告汇总，包含通过率、耗时、失败用例与失败原因聚类。",
    scope: "execution_tasks:read",
    handler: "aggregate",
    upstreamPath: null,
    params: [
      { name: "task_id", type: "string", required: true, description: "测试任务 ID。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "task_id": "ET-2026-000128",
    "pass_rate": 0.94,
    "duration_ms": 842000,
    "top_failures": [
      { "reason": "元素定位超时", "count": 2 }
    ]
  }
}`,
  },
  {
    id: "cap_webhook",
    name: "注册结果回调",
    category: "集成",
    method: "POST",
    path: "/api/v1/open/webhooks",
    summary: "注册测试任务完成后的结果回调地址。",
    description:
      "为账号注册 Webhook，当测试任务进入终态时，平台将向指定 URL 推送结果事件。需要 execution_tasks:write 授权。",
    scope: "execution_tasks:write",
    handler: "local",
    upstreamPath: null,
    params: [
      { name: "url", type: "string", required: true, description: "接收回调的 HTTPS 地址。" },
      { name: "events", type: "string[]", required: true, description: "订阅事件类型，如 task.completed。" },
      { name: "secret", type: "string", required: false, description: "用于校验签名的密钥。" },
    ],
    sampleResponse: `{
  "code": 0,
  "data": {
    "webhook_id": "wh_01H9...",
    "status": "active"
  }
}`,
  },
];

function nowMinus(minutes: number): string {
  return new Date(Date.now() - minutes * 60000).toISOString();
}

const baseLogs: Omit<CallLog, "requestId" | "appName" | "gatewayLatencyMs" | "requestBody" | "responseBody" | "errorCode" | "diagnosis">[] = [
  { id: "l1", timestamp: nowMinus(2), keyName: "CI 流水线集成", method: "GET", endpoint: "/api/v1/open/execution/tasks/my", statusCode: 200, status: "success", latencyMs: 84, ip: "10.12.4.19" },
  { id: "l2", timestamp: nowMinus(5), keyName: "数据看板同步", method: "GET", endpoint: "/api/v1/open/test-specs/cases", statusCode: 200, status: "success", latencyMs: 132, ip: "10.12.8.7" },
  { id: "l3", timestamp: nowMinus(9), keyName: "CI 流水线集成", method: "GET", endpoint: "/api/v1/open/execution/tasks/ET-2026-000128/status", statusCode: 200, status: "success", latencyMs: 61, ip: "10.12.4.19" },
  { id: "l4", timestamp: nowMinus(14), keyName: "本地联调（测试）", method: "GET", endpoint: "/api/v1/open/execution/tasks/ET-2026-000099/timeline", statusCode: 404, status: "client_error", latencyMs: 40, ip: "127.0.0.1" },
  { id: "l5", timestamp: nowMinus(21), keyName: "数据看板同步", method: "GET", endpoint: "/api/v1/open/reports/ET-2026-000120", statusCode: 200, status: "success", latencyMs: 210, ip: "10.12.8.7" },
  { id: "l6", timestamp: nowMinus(28), keyName: "CI 流水线集成", method: "GET", endpoint: "/api/v1/open/execution/tasks/my", statusCode: 429, status: "client_error", latencyMs: 12, ip: "10.12.4.19" },
  { id: "l7", timestamp: nowMinus(37), keyName: "数据看板同步", method: "GET", endpoint: "/api/v1/open/test-specs/cases", statusCode: 200, status: "success", latencyMs: 118, ip: "10.12.8.7" },
  { id: "l8", timestamp: nowMinus(45), keyName: "本地联调（测试）", method: "POST", endpoint: "/api/v1/open/webhooks", statusCode: 500, status: "server_error", latencyMs: 903, ip: "127.0.0.1" },
  { id: "l9", timestamp: nowMinus(52), keyName: "CI 流水线集成", method: "GET", endpoint: "/api/v1/open/execution/tasks/ET-2026-000128/status", statusCode: 200, status: "success", latencyMs: 73, ip: "10.12.4.19" },
  { id: "l10", timestamp: nowMinus(66), keyName: "数据看板同步", method: "GET", endpoint: "/api/v1/open/reports/ET-2026-000118", statusCode: 200, status: "success", latencyMs: 187, ip: "10.12.8.7" },
  { id: "l11", timestamp: nowMinus(80), keyName: "CI 流水线集成", method: "GET", endpoint: "/api/v1/open/execution/tasks/my", statusCode: 200, status: "success", latencyMs: 91, ip: "10.12.4.19" },
  { id: "l12", timestamp: nowMinus(95), keyName: "本地联调（测试）", method: "GET", endpoint: "/api/v1/open/execution/tasks/ET-2026-000101/status", statusCode: 200, status: "success", latencyMs: 66, ip: "127.0.0.1" },
];

export const mockLogs: CallLog[] = baseLogs.map((log, index) => {
  const isRateLimited = log.statusCode === 429;
  const isNotFound = log.statusCode === 404;
  const isServerError = log.statusCode >= 500;
  return {
    ...log,
    requestId: `req_20260717_${String(index + 1).padStart(4, "0")}`,
    appName: log.keyName.includes("数据看板") ? "质量数据看板" : log.keyName.includes("本地") ? "本地联调工作区" : "持续集成流水线",
    gatewayLatencyMs: Math.max(4, Math.round(log.latencyMs * 0.16)),
    requestBody: log.method === "POST" ? JSON.stringify({ url: "https://example.com/hooks/dml", events: ["task.completed"] }, null, 2) : null,
    responseBody: JSON.stringify(
      log.status === "success"
        ? { code: 0, data: { accepted: true, request_id: `req_20260717_${String(index + 1).padStart(4, "0")}` } }
        : { code: log.statusCode, message: isRateLimited ? "请求频率超过当前应用限额" : isNotFound ? "未找到指定测试任务" : "服务暂时不可用" },
      null,
      2,
    ),
    errorCode: isRateLimited ? "RATE_LIMIT_EXCEEDED" : isNotFound ? "TASK_NOT_FOUND" : isServerError ? "UPSTREAM_SERVICE_ERROR" : undefined,
    diagnosis: isRateLimited
      ? "当前应用在一分钟内请求过多。建议降低并发、增加指数退避，或申请更高配额。"
      : isNotFound
        ? "请检查任务 ID 是否正确，并确认该密钥有权限访问目标任务。"
        : isServerError
          ? "上游服务出现异常。建议稍后重试；若持续失败，请携带 Request ID 联系平台管理员。"
          : undefined,
  };
});

export const mockOverview: OverviewStats = {
  totalCallsToday: 2013,
  totalCallsTrend: 12.4,
  successRate: 98.6,
  successRateTrend: 0.3,
  activeKeys: 3,
  quotaUsed: 2013,
  quotaLimit: 50000,
  daily: [
    { date: "07-11", calls: 1520, errors: 22 },
    { date: "07-12", calls: 980, errors: 9 },
    { date: "07-13", calls: 1240, errors: 15 },
    { date: "07-14", calls: 1810, errors: 31 },
    { date: "07-15", calls: 1660, errors: 18 },
    { date: "07-16", calls: 1920, errors: 24 },
    { date: "07-17", calls: 2013, errors: 28 },
  ],
  topCapabilities: [
    { name: "查询我的测试任务", calls: 8420 },
    { name: "查询任务状态", calls: 5130 },
    { name: "读取执行报告", calls: 3110 },
    { name: "查询任务时间线", calls: 2260 },
    { name: "读取测试用例", calls: 1040 },
  ],
};
