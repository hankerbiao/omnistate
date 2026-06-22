// ═══════════════════════════════════════════════════════════════════════
//  projects/mockData.ts — 项目详情页 Mock 数据（待后端 API 补齐后替换）
// ═══════════════════════════════════════════════════════════════════════

import type { ProjectStats } from '../../types'

// ── 类型定义 ─────────────────────────────────────────────────────────

export interface MockTask {
  id: string; name: string; assignee: string; status: string; progress: number; priority: string; updated: string
}

export interface MockCase {
  id: string; title: string; module: string; status: string; priority: string; executor: string; lastResult: string
}

export interface MockPlan {
  id: string; name: string; status: string; total: number; passed: number; failed: number; executor: string; date: string
}

export interface MockRequirement {
  id: string; title: string; priority: string; status: string; caseCount: number; coverageRate: number; owner: string
}

export interface MockActivity {
  id: string; time: string; user: string; action: string; target: string; type: string
}

// ── 数据 ─────────────────────────────────────────────────────────────

export const mockTasks: MockTask[] = [
  { id: 'T-001', name: '登录模块功能验证', assignee: '张三', status: '已完成', progress: 100, priority: 'P0', updated: '2024-03-15' },
  { id: 'T-002', name: '权限管理回归测试', assignee: '李四', status: '进行中', progress: 65, priority: 'P1', updated: '2024-03-14' },
  { id: 'T-003', name: '数据导出性能测试', assignee: '王五', status: '进行中', progress: 30, priority: 'P1', updated: '2024-03-13' },
  { id: 'T-004', name: 'UI兼容性适配验证', assignee: '赵六', status: '失败', progress: 45, priority: 'P2', updated: '2024-03-12' },
  { id: 'T-005', name: '接口安全扫描', assignee: '张三', status: '待执行', progress: 0, priority: 'P0', updated: '2024-03-11' },
  { id: 'T-006', name: '批量导入功能测试', assignee: '李四', status: '待执行', progress: 0, priority: 'P2', updated: '2024-03-10' },
  { id: 'T-007', name: '消息通知推送验证', assignee: '王五', status: '已完成', progress: 100, priority: 'P1', updated: '2024-03-09' },
  { id: 'T-008', name: '搜索功能准确率测试', assignee: '赵六', status: '进行中', progress: 80, priority: 'P2', updated: '2024-03-08' },
]

export const mockManualCases: MockCase[] = [
  { id: 'MC-001', title: '用户登录-正常流程', module: '登录', status: '通过', priority: 'P0', executor: '张三', lastResult: '通过' },
  { id: 'MC-002', title: '用户登录-密码错误', module: '登录', status: '通过', priority: 'P0', executor: '张三', lastResult: '通过' },
  { id: 'MC-003', title: '权限分配-管理员', module: '权限', status: '通过', priority: 'P1', executor: '李四', lastResult: '通过' },
  { id: 'MC-004', title: '权限分配-只读用户', module: '权限', status: '失败', priority: 'P1', executor: '李四', lastResult: '失败' },
  { id: 'MC-005', title: '数据导出-CSV格式', module: '数据', status: '通过', priority: 'P2', executor: '王五', lastResult: '通过' },
  { id: 'MC-006', title: '数据导出-Excel格式', module: '数据', status: '阻塞', priority: 'P2', executor: '王五', lastResult: '未执行' },
  { id: 'MC-007', title: 'UI-深色模式显示', module: 'UI', status: '通过', priority: 'P2', executor: '赵六', lastResult: '通过' },
  { id: 'MC-008', title: 'UI-移动端适配', module: 'UI', status: '进行中', priority: 'P1', executor: '赵六', lastResult: '未执行' },
]

export const mockAutoCases: MockCase[] = [
  { id: 'AC-001', title: '[自动] 登录接口测试', module: 'API', status: '通过', priority: 'P0', executor: 'CI', lastResult: '通过' },
  { id: 'AC-002', title: '[自动] 用户注册校验', module: 'API', status: '通过', priority: 'P0', executor: 'CI', lastResult: '通过' },
  { id: 'AC-003', title: '[自动] 权限拦截测试', module: 'API', status: '失败', priority: 'P1', executor: 'CI', lastResult: '失败' },
  { id: 'AC-004', title: '[自动] 数据一致性检查', module: '数据', status: '通过', priority: 'P1', executor: 'CI', lastResult: '通过' },
  { id: 'AC-005', title: '[自动] 超时处理测试', module: 'API', status: '通过', priority: 'P2', executor: 'CI', lastResult: '通过' },
  { id: 'AC-006', title: '[自动] 并发请求测试', module: '性能', status: '失败', priority: 'P1', executor: 'CI', lastResult: '失败' },
]

export const mockPlans: MockPlan[] = [
  { id: 'P-001', name: 'V2.0 回归测试计划', status: '已完成', total: 120, passed: 108, failed: 12, executor: '张三', date: '2024-03-01 ~ 2024-03-10' },
  { id: 'P-002', name: 'V2.1 冒烟测试', status: '进行中', total: 45, passed: 32, failed: 3, executor: '李四', date: '2024-03-11 ~ 2024-03-15' },
  { id: 'P-003', name: '安全专项扫描', status: '待执行', total: 60, passed: 0, failed: 0, executor: '王五', date: '2024-03-20 ~ 2024-03-25' },
]

export const mockRequirements: MockRequirement[] = [
  { id: 'R-001', title: '用户登录功能', priority: 'P0', status: '已覆盖', caseCount: 8, coverageRate: 100, owner: '张三' },
  { id: 'R-002', title: '权限分级管理', priority: 'P0', status: '已覆盖', caseCount: 12, coverageRate: 100, owner: '李四' },
  { id: 'R-003', title: '数据导出功能', priority: 'P1', status: '部分覆盖', caseCount: 5, coverageRate: 62, owner: '王五' },
  { id: 'R-004', title: '深色模式适配', priority: 'P2', status: '部分覆盖', caseCount: 3, coverageRate: 50, owner: '赵六' },
  { id: 'R-005', title: '消息实时推送', priority: 'P1', status: '未覆盖', caseCount: 0, coverageRate: 0, owner: '张三' },
]

export const mockActivities: MockActivity[] = [
  { id: 'A-01', time: '刚刚', user: '张三', action: '完成', target: '登录模块功能验证', type: 'task_done' },
  { id: 'A-02', time: '5分钟前', user: '李四', action: '标记进行中', target: '权限管理回归测试', type: 'task_running' },
  { id: 'A-03', time: '1小时前', user: '王五', action: '创建计划', target: '安全专项扫描', type: 'plan_create' },
  { id: 'A-04', time: '2小时前', user: '赵六', action: '提交用例', target: 'UI-深色模式显示', type: 'case_pass' },
  { id: 'A-05', time: '3小时前', user: '张三', action: '标记失败', target: '接口安全扫描', type: 'task_fail' },
  { id: 'A-06', time: '昨天', user: '李四', action: '归档计划', target: 'V2.0 回归测试计划', type: 'plan_done' },
]

export const mockBlockers = [
  { id: 'T-004', name: 'UI兼容性适配验证', type: '失败', assignee: '赵六', color: '#f85149' },
  { id: 'T-005', name: '接口安全扫描', type: '待执行(P0)', assignee: '张三', color: '#f85149' },
  { id: 'MC-004', name: '权限分配-只读用户', type: '失败', assignee: '李四', color: '#f85149' },
  { id: 'AC-003', name: '[自动] 权限拦截测试', type: '失败', assignee: 'CI', color: '#f85149' },
]

// ── Mock Stats（API 返回空时降级使用） ────────────────────────────────

export const MOCK_STATS: ProjectStats = {
  test_case_count: 36,
  auto_case_count: 18,
  requirement_count: 8,
  plan_count: 5,
  collection_count: 4,
  task: { total: 20, done: 9, running: 4, failed: 2, pending: 5, progress: 45 },
  task_progress: 45,
  manual_pass: { total: 36, passed: 28, failed: 5, pass_rate: 78 },
  auto_pass: { total: 18, passed: 14, failed: 4, pass_rate: 78 },
  coverage_rate: 72,
  assignee_distribution: [
    { assignee_id: 'u001', assignee_name: '张三', item_count: 6, done_count: 3, progress: 50 },
    { assignee_id: 'u002', assignee_name: '李四', item_count: 5, done_count: 2, progress: 40 },
    { assignee_id: 'u003', assignee_name: '王五', item_count: 5, done_count: 2, progress: 40 },
    { assignee_id: 'u004', assignee_name: '赵六', item_count: 4, done_count: 2, progress: 50 },
  ],
}
