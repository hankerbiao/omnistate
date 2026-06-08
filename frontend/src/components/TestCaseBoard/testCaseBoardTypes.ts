import type {
  AutomationTestCaseResponse,
  TestCaseResponse,
  UserResponse,
} from '../../types';
import { SWITCHABLE_USERS } from '../../config/users';

/* ── Types ── */

export type CaseType = 'auto' | 'manual';
export type TypeFilter = 'all' | 'auto' | 'manual';
export type DetailTab = 'info' | 'steps' | 'code' | 'params' | 'relations' | 'workflow' | 'meta';

export interface UnifiedCaseItem {
  type: CaseType;
  id: string;
  caseId: string;
  title: string;
  status: string;
  priority?: string;
  ownerName?: string;
  framework?: string;
  automationType?: string;
  version: string | number;
  updatedAt: string;
  autoData?: AutomationTestCaseResponse;
  manualData?: TestCaseResponse;
  labId?: string;
}

/* ── Constants ── */

export const AUTO_STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Active', INACTIVE: 'Inactive', DRAFT: 'Draft', DEPRECATED: 'Deprecated',
};
export const AUTO_STATUS_DOT: Record<string, string> = {
  ACTIVE: '#3fb950', INACTIVE: '#8b949e', DRAFT: '#58a6ff', DEPRECATED: '#f85149',
};
export const MANUAL_STATUS_DOT: Record<string, string> = {
  DRAFT: '#8b949e', PENDING_REVIEW: '#58a6ff', IN_REVIEW: '#d29922',
  REVISE: '#f0883e', DONE: '#3fb950', REJECTED: '#f85149',
};
export const PRIORITY_COLORS: Record<string, string> = {
  P0: '#f85149', P1: '#d29922', P2: '#58a6ff', P3: '#8b949e',
};
export const FW_ICONS: Record<string, string> = {
  pytest: '\uD83D\uDC0D', Pytest: '\uD83D\uDC0D', PyTest: '\uD83D\uDC0D',
  playwright: '\uD83C\uDFAD', Playwright: '\uD83C\uDFAD',
  cypress: '\uD83C\uDF32', Cypress: '\uD83C\uDF32',
  selenium: '\uD83C\uDF10', Selenium: '\uD83C\uDF10',
  appium: '\uD83D\uDCF1', Appium: '\uD83D\uDCF1',
  requests: '\uD83D\uDCE1', Requests: '\uD83D\uDCE1',
  go: '\uD83D\uDD35', Go: '\uD83D\uDD35',
};
export const FW_COLORS: Record<string, string> = {
  pytest: '#9cf', Playwright: '#e8e8e8', Cypress: '#69d3a8',
  Selenium: '#43b02a', Appium: '#ee6d4a', Requests: '#6cac4d',
  Go: '#00add8',
};
export const FW_FALLBACK_COLOR = 'var(--accent-purple)';

export const TYPE_FILTERS: { key: TypeFilter; label: string; icon: string }[] = [
  { key: 'all', label: '全部', icon: '\u229E' },
  { key: 'manual', label: '手工用例', icon: '\uD83D\uDCCB' },
  { key: 'auto', label: '自动化用例', icon: '\u26A1' },
];

export const STATUS_FILTERS = [
  { value: 'all', label: '全部状态' },
  { value: 'ACTIVE', label: 'Active', type: 'auto' as const },
  { value: 'DRAFT', label: 'Draft', type: 'auto' as const },
  { value: 'DEPRECATED', label: 'Deprecated', type: 'auto' as const },
  { value: 'PENDING_REVIEW', label: '待评审', type: 'manual' as const },
  { value: 'IN_REVIEW', label: '评审中', type: 'manual' as const },
  { value: 'DONE', label: '已完成', type: 'manual' as const },
  { value: 'REJECTED', label: '已驳回', type: 'manual' as const },
];

/* ── Helpers ── */

export function buildUserNameMap(users: UserResponse[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const u of SWITCHABLE_USERS) map.set(u.userId, u.label);
  for (const u of users) map.set(u.user_id, u.username);
  return map;
}

export function getAutoDot(status: string): string {
  return AUTO_STATUS_DOT[status] || '#8b949e';
}
export function getAutoLabel(status: string): string {
  return AUTO_STATUS_LABELS[status] || status;
}
export function getManualDot(status: string): string {
  return MANUAL_STATUS_DOT[status] || '#8b949e';
}
export function getManualLabel(status: string): string {
  const labels: Record<string, string> = {
    DRAFT: '草稿', PENDING_REVIEW: '待评审', IN_REVIEW: '评审中',
    REVISE: '修改中', DONE: '已完成', REJECTED: '已驳回',
  };
  return labels[status] || status;
}
export function fwIcon(fw?: string): string {
  return fw ? (FW_ICONS[fw] || '\u2699\uFE0F') : '\u2699\uFE0F';
}
export function fwColor(fw?: string): string {
  return fw ? (FW_COLORS[fw] || FW_FALLBACK_COLOR) : FW_FALLBACK_COLOR;
}
