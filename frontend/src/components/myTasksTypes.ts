import type React from 'react';

// ═══════════════════════════════════════════════════════════════════════
//  Type Definitions
// ═══════════════════════════════════════════════════════════════════════

export interface PlanTaskResult {
  passed?: boolean;
  notes?: string;
  severity?: string;
  executedAt?: string;
  actual?: string;
  expected?: string;
  env?: string;
  testData?: string;
  bugId?: string;
  actualDuration?: string;
  attachments?: string[];
}

export interface PlanTask {
  id: string;
  planId: string;
  planTitle: string;
  caseId: string;
  caseTitle: string;
  type: 'auto' | 'manual';
  component: string;
  assignee: string;
  status: 'pending' | 'running' | 'done' | 'fail';
  result?: PlanTaskResult;
}

// ═══════════════════════════════════════════════════════════════════════
//  Constants
// ═══════════════════════════════════════════════════════════════════════

export const TYPE_LABELS: Record<string, string> = {
  REQUIREMENT: '需求',
  TEST_CASE: '测试用例',
  PLAN_TASK: '执行计划',
};

export const TYPE_COLORS: Record<string, { bg: string; color: string }> = {
  REQUIREMENT: { bg: '#e8f5e9', color: '#2e7d32' },
  TEST_CASE: { bg: '#e3f2fd', color: '#1565c0' },
  PLAN_TASK: { bg: 'rgba(163,113,247,0.15)', color: '#a371f7' },
};

export const COMPONENT_COLORS: Record<string, string> = {
  '内存验证组': '#58a6ff',
  '固件验证组': '#d29922',
  '工具链组': '#3fb950',
  '存储验证组': '#f0883e',
  '平台质量组': '#a371f7',
};

export const STATUS_LABELS: Record<string, string> = {
  pending: '○ 待执行',
  running: '▶ 执行中',
  done: '✓ 已完成',
  fail: '✗ 失败',
};

export const STATUS_COLORS: Record<string, string> = {
  pending: '#8b949e',
  running: '#58a6ff',
  done: '#3fb950',
  fail: '#f85149',
};

// ═══════════════════════════════════════════════════════════════════════
//  Mock Data
// ═══════════════════════════════════════════════════════════════════════

export const MOCK_PLAN_TASKS: PlanTask[] = [
  { id: 'pt-1', planId: 'plan-1', planTitle: 'Sprint 1 · 固件基线验证', caseId: 'TC-002', caseTitle: '内存边界值校验', type: 'manual', component: '内存验证组', assignee: 'tester', status: 'pending' },
  { id: 'pt-2', planId: 'plan-1', planTitle: 'Sprint 1 · 固件基线验证', caseId: 'TC-004', caseTitle: '固件异常断电恢复', type: 'manual', component: '固件验证组', assignee: 'tester', status: 'running' },
  { id: 'pt-3', planId: 'plan-1', planTitle: 'Sprint 1 · 固件基线验证', caseId: 'TC-010', caseTitle: '安全权限验证', type: 'manual', component: '平台质量组', assignee: 'qa', status: 'pending' },
  { id: 'pt-6', planId: 'plan-1', planTitle: 'Sprint 1 · 固件基线验证', caseId: 'TC-001', caseTitle: '内存读写压力测试', type: 'auto', component: '内存验证组', assignee: 'tester', status: 'pending' },
  { id: 'pt-7', planId: 'plan-1', planTitle: 'Sprint 1 · 固件基线验证', caseId: 'TC-003', caseTitle: '固件版本升级测试', type: 'auto', component: '固件验证组', assignee: 'tester', status: 'running' },
  { id: 'pt-4', planId: 'plan-2', planTitle: 'Sprint 2 · 性能基准测试', caseId: 'TC-007', caseTitle: '存储读写性能基准', type: 'manual', component: '存储验证组', assignee: 'dev', status: 'pending' },
  { id: 'pt-8', planId: 'plan-2', planTitle: 'Sprint 2 · 性能基准测试', caseId: 'TC-005', caseTitle: 'CI/CD 管道集成测试', type: 'auto', component: '工具链组', assignee: 'tester', status: 'pending' },
  { id: 'pt-5', planId: 'plan-2', planTitle: 'Sprint 2 · 性能基准测试', caseId: 'TC-009', caseTitle: '多用户并发访问测试', type: 'manual', component: '平台质量组', assignee: 'tester', status: 'done',
    result: { passed: true, notes: '通过。并发用户数 500 时响应正常', severity: 'minor', actual: '500并发下响应时间 < 200ms，无超时', env: '固件 v2.3.1 / 64GB / SSD', testData: '500线程 × 4KB随机读写', bugId: 'BZ-12345', actualDuration: '28', executedAt: '2026-07-02 14:30' } },
];

// ═══════════════════════════════════════════════════════════════════════
//  Shared Styles
// ═══════════════════════════════════════════════════════════════════════

export const groupBadgeStyle = (colors: { bg: string; color: string }): React.CSSProperties => ({
  display: 'inline-block', padding: '2px 10px', borderRadius: 6,
  fontSize: 12, fontWeight: 600, backgroundColor: colors.bg, color: colors.color,
});

export const TH: React.CSSProperties = {
  padding: '4px 8px', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)',
  textTransform: 'uppercase', letterSpacing: '0.3px', borderBottom: '1px solid var(--border-subtle)',
  whiteSpace: 'nowrap',
};

export const TD: React.CSSProperties = {
  padding: '5px 8px', fontSize: 12, borderBottom: '0.5px solid var(--border-subtle)',
  verticalAlign: 'middle',
};

export const modalLabel: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6,
};

export const myTasksStyles: Record<string, React.CSSProperties> = {
  list: { display: 'flex', flexDirection: 'column', gap: '12px' },
  group: { display: 'flex', flexDirection: 'column' },
  groupHeader: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, padding: '0 4px' },
  groupCount: { fontSize: 12, color: 'var(--text-tertiary)' },
  loadingSmall: { display: 'flex', justifyContent: 'center', padding: 16 },
  contentPreview: { fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.5, margin: '0 0 8px' },
};
