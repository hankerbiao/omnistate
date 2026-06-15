import type React from 'react';
import type { PlanTaskItemResponse } from '../types';

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
//  Transformer — 后端 PlanTaskItemResponse → 前端 PlanTask
// ═══════════════════════════════════════════════════════════════════════

export function transformApiItem(item: PlanTaskItemResponse): PlanTask {
  const resultPayload = item.result;
  const result: PlanTaskResult | undefined = resultPayload
    ? {
        passed: resultPayload.passed,
        notes: resultPayload.notes,
        severity: resultPayload.severity,
        executedAt: resultPayload.executed_at ?? '',
        actual: resultPayload.actual,
        expected: resultPayload.expected,
        env: resultPayload.env,
        testData: resultPayload.test_data,
        bugId: resultPayload.bug_id,
        actualDuration: resultPayload.actual_duration,
        attachments: resultPayload.attachments,
      }
    : undefined;

  return {
    id: item.item_id,
    planId: item.plan_id,
    planTitle: item.plan_title,
    caseId: item.case_id,
    caseTitle: item.case_title,
    type: item.ref_type === 'auto' ? 'auto' : 'manual',
    component: item.component,
    assignee: item.assignee_id ?? '',
    status: item.status as PlanTask['status'],
    result,
  };
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
