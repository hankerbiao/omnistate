import type React from 'react';
import type { PlanTaskItemResponse, PlanItemDispatchConfig } from '../types';

// ═══════════════════════════════════════════════════════════════════════
//  Type Definitions
// ═══════════════════════════════════════════════════════════════════════

export interface PlanTaskResult {
  source?: 'manual' | 'auto';
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
  executionTaskId?: string | null;
  resultId?: string | null;
  resultSource?: 'manual' | 'auto' | null;
  result?: PlanTaskResult;
  dispatchConfig?: PlanItemDispatchConfig | null;
}

// ═══════════════════════════════════════════════════════════════════════
//  Transformer — 后端 PlanTaskItemResponse → 前端 PlanTask
// ═══════════════════════════════════════════════════════════════════════

export function transformApiItem(item: PlanTaskItemResponse): PlanTask {
  const resultPayload = item.result;
  const result: PlanTaskResult | undefined = resultPayload
    ? {
        source: resultPayload.result_source ?? item.result_source ?? undefined,
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
    executionTaskId: item.execution_task_id,
    resultId: item.result_id,
    resultSource: item.result_source,
    result,
    dispatchConfig: item.dispatch_config,
  };
}

export const STATUS_COLORS: Record<string, string> = {
  pending: '#8b949e',
  running: '#58a6ff',
  done: '#3fb950',
  fail: '#f85149',
};

// ═══════════════════════════════════════════════════════════════════════
//  Shared Styles
// ═══════════════════════════════════════════════════════════════════════

export const TH: React.CSSProperties = {
  padding: '4px 8px', fontSize: 'calc(10px * var(--my-tasks-font-scale, 1))', fontWeight: 600, color: 'var(--text-tertiary)',
  textTransform: 'uppercase', letterSpacing: '0.3px', borderBottom: '1px solid var(--border-subtle)',
  whiteSpace: 'nowrap',
};

export const TD: React.CSSProperties = {
  padding: '5px 8px', fontSize: 'calc(12px * var(--my-tasks-font-scale, 1))', borderBottom: '0.5px solid var(--border-subtle)',
  verticalAlign: 'middle',
  lineHeight: 'var(--my-tasks-line-height, 1.65)',
};

export const modalLabel: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6,
};

export const myTasksStyles: Record<string, React.CSSProperties> = {
  list: { display: 'flex', flexDirection: 'column', gap: '12px' },
  group: { display: 'flex', flexDirection: 'column' },
  groupHeader: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, padding: '0 4px' },
  loadingSmall: { display: 'flex', justifyContent: 'center', padding: 16 },
  contentPreview: { fontSize: 'calc(13px * var(--my-tasks-font-scale, 1))', color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 'var(--my-tasks-line-height, 1.65)', margin: '0 0 8px' },
};
