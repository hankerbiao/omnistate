/**
 * Test Execution Plan — Types & Constants
 * Extracted from TestExecutionPlanDemo.tsx for modularity.
 */

export const RERUNNABLE_STATUSES: ReadonlyArray<string> = ['fail', 'done'];

export interface PlanSummary {
  plan_id: string;
  title: string;
  description: string;
  status: string;
  start_date: string;
  end_date: string;
  trigger_at: string;
  created_by: string;
  item_count: number;
  done_count: number;
  progress_percent: number;
  created_at: string;
  updated_at: string;
}

export interface PlanItemSummary {
  item_id: string;
  case_id: string;
  case_title: string;
  ref_type: string;
  component: string;
  priority: string;
  assignee_id: string | null;
  status: string;
  order_no: number;
  execution_task_id?: string | null;
  result?: { passed?: boolean; notes?: string; actual?: string } | null;
  created_at?: string | null;
  updated_at?: string | null;
  archived_at?: string | null;
}

export type ViewMode = 'statusBoard' | 'componentView' | 'listView';

export const STATUS = ['pending', 'running', 'fail', 'done'] as const;
export type ItemStatus = (typeof STATUS)[number];

export const STATUS_META: Record<ItemStatus, { label: string; color: string; bg: string }> = {
  pending: { label: '待执行', color: 'var(--text-tertiary)', bg: 'var(--surface-tertiary)' },
  running: { label: '执行中', color: 'var(--accent-primary)', bg: 'rgba(37, 99, 235, 0.08)' },
  fail:    { label: '失败',   color: 'var(--status-error)', bg: 'var(--status-error-bg)' },
  done:    { label: '已完成', color: 'var(--status-success)', bg: 'var(--status-success-bg)' },
};

export const PLAN_STATUS_META: Record<string, { label: string; color: string }> = {
  active:   { label: '进行中', color: 'var(--status-success)' },
  done:     { label: '已完成', color: 'var(--text-tertiary)' },
};

export const PRIORITY_COLORS: Record<string, string> = {
  P0: 'var(--status-error)',
  P1: 'var(--status-warning)',
  P2: 'var(--accent-primary)',
  P3: 'var(--text-tertiary)',
};

export type NewPlanData = {
  title: string;
  description: string;
  startDate: string;
  endDate: string;
  selectedCases: string[];
  assignments: Record<string, { assignee: string }>;
};

export const emptyNewPlan: NewPlanData = {
  title: '',
  description: '',
  startDate: '',
  endDate: '',
  selectedCases: [],
  assignments: {},
};

export interface CaseMapEntry {
  id: string;
  title: string;
  type: 'auto' | 'manual';
  priority: string;
}

export interface CollectionEntry {
  collection_id: string;
  name: string;
  description?: string | null;
  case_count: number;
}
