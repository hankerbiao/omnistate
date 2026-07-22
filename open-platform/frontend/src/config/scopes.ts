// DML V4 开放平台 · 可选权限范围目录（真实配置，非 Mock 数据）
// 新建密钥时供前端展示可选 scope；生产环境应来自网关，这里保留为静态兜底。
export const AVAILABLE_SCOPES: { id: string; label: string; desc: string }[] = [
  {
    id: "execution_tasks:read",
    label: "任务读取",
    desc: "查询测试任务列表、状态、时间线与执行报告",
  },
  { id: "execution_tasks:write", label: "任务写入", desc: "创建、更新和下发测试任务（受控）" },
  { id: "test_cases:read", label: "用例读取", desc: "读取测试用例" },
  { id: "requirements:read", label: "需求读取", desc: "读取测试需求" },
  { id: "projects:read", label: "项目读取", desc: "读取项目列表、详情、统计、阻塞项和动态" },
];
