export type WorkflowTypeCode = 'REQUIREMENT' | 'TEST_CASE';

/** Workflow 状态中文（通用） */
export const WORKFLOW_STATE_LABELS: Record<string, string> = {
  DRAFT: '草稿',
  PENDING_REVIEW: '待审核',
  PENDING_DEVELOP: '待开发',
  DEVELOPING: '开发中',
  PENDING_TEST: '待测试',
  PENDING_UAT: '待验收',
  PENDING_RELEASE: '待发布',
  RELEASED: '已发布',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  CLOSED: '已关闭',
  ASSIGNED: '已指派',
  DONE: '已完成',
  未开始: '未开始',
};

/** 按业务类型区分歧义状态 */
const TYPE_STATE_OVERRIDES: Partial<Record<WorkflowTypeCode, Record<string, string>>> = {
  TEST_CASE: {
    DEVELOPING: '编写中',
    ASSIGNED: '已指派',
  },
  REQUIREMENT: {
    DEVELOPING: '开发中',
  },
};

export function getStateLabel(state: string, typeCode?: WorkflowTypeCode): string {
  if (typeCode && TYPE_STATE_OVERRIDES[typeCode]?.[state]) {
    return TYPE_STATE_OVERRIDES[typeCode]![state]!;
  }
  return WORKFLOW_STATE_LABELS[state] || state;
}

export const WORKFLOW_ACTION_LABELS: Record<string, string> = {
  SUBMIT: '提交评审',
  APPROVE: '通过',
  REJECT: '驳回',
  START: '开始开发',
  FINISH: '完成开发',
  PASS: '通过',
  PUBLISH: '发布',
  CLOSE: '关闭',
  ASSIGN: '指派编写人',
  START_WRITE: '开始编写',
  SUBMIT_REVIEW: '提交评审',
};

export const WORKFLOW_FIELD_LABELS: Record<string, string> = {
  target_owner_id: '目标处理人',
  priority: '优先级',
  comment: '备注',
};

export function getWorkflowStateStyle(state: string): { bg: string; color: string } {
  const styleMap: Record<string, { bg: string; color: string }> = {
    DRAFT: { bg: 'var(--surface-tertiary)', color: 'var(--text-tertiary)' },
    ASSIGNED: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
    PENDING_REVIEW: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
    PENDING_DEVELOP: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
    DEVELOPING: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
    PENDING_TEST: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
    PENDING_UAT: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
    PENDING_RELEASE: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
    RELEASED: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
    DONE: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
    REJECTED: { bg: 'var(--status-error-bg)', color: 'var(--status-error)' },
  };
  return styleMap[state] || { bg: 'var(--surface-tertiary)', color: 'var(--text-secondary)' };
}

export function getActionButtonStyle(action: string): { bg: string; color: string; border: string } {
  const colorMap: Record<string, { bg: string; color: string; border: string }> = {
    SUBMIT: { bg: '#e3f2fd', color: '#1565c0', border: '#bbdefb' },
    SUBMIT_REVIEW: { bg: '#e3f2fd', color: '#1565c0', border: '#bbdefb' },
    START: { bg: '#e3f2fd', color: '#1565c0', border: '#bbdefb' },
    START_WRITE: { bg: '#e3f2fd', color: '#1565c0', border: '#bbdefb' },
    ASSIGN: { bg: '#fff3e0', color: '#e65100', border: '#ffe0b2' },
    APPROVE: { bg: '#e8f5e9', color: '#2e7d32', border: '#c8e6c9' },
    PASS: { bg: '#e8f5e9', color: '#2e7d32', border: '#c8e6c9' },
    FINISH: { bg: '#e8f5e9', color: '#2e7d32', border: '#c8e6c9' },
    PUBLISH: { bg: '#e0f2f1', color: '#00796b', border: '#b2dfdb' },
    REJECT: { bg: '#ffebee', color: '#c62828', border: '#ffcdd2' },
    CLOSE: { bg: '#f5f5f5', color: '#616161', border: '#e0e0e0' },
  };
  return colorMap[action] || { bg: '#fafafa', color: '#757575', border: '#e0e0e0' };
}

/** 状态机步骤（用于 Stepper 展示） */
export const WORKFLOW_STATE_PIPELINES: Record<WorkflowTypeCode, string[]> = {
  REQUIREMENT: [
    'DRAFT',
    'PENDING_REVIEW',
    'PENDING_DEVELOP',
    'DEVELOPING',
    'PENDING_TEST',
    'PENDING_UAT',
    'PENDING_RELEASE',
    'RELEASED',
  ],
  TEST_CASE: ['DRAFT', 'ASSIGNED', 'DEVELOPING', 'PENDING_REVIEW', 'DONE'],
};

/** ManualTestCaseList 筛选项 */
export const TEST_CASE_STATUS_FILTER_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'DRAFT', label: '草稿' },
  { value: 'ASSIGNED', label: '已指派' },
  { value: 'DEVELOPING', label: '编写中' },
  { value: 'PENDING_REVIEW', label: '待审核' },
  { value: 'DONE', label: '已完成' },
  { value: 'REJECTED', label: '已驳回' },
];

export const REQUIREMENT_STATUS_FILTER_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'DRAFT', label: '草稿' },
  { value: 'PENDING_REVIEW', label: '待审核' },
  { value: 'PENDING_DEVELOP', label: '待开发' },
  { value: 'DEVELOPING', label: '开发中' },
  { value: 'PENDING_TEST', label: '待测试' },
  { value: 'PENDING_UAT', label: '待验收' },
  { value: 'PENDING_RELEASE', label: '待发布' },
  { value: 'RELEASED', label: '已发布' },
];
