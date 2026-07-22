import type {
  AutomationTestCaseResponse,
  CatalogLab,
  TestCaseResponse,
} from '../../types';

/* ── Types ── */

export type CaseType = 'auto' | 'manual';
export type TypeFilter = 'all' | 'auto' | 'manual';

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
  catalogPath?: string[];
  labName?: string;
  tags?: string[];
}

/* ── Constants ── */

/** 紧凑标签，用于弹窗等空间受限场景 */
export const PICKER_TYPE_FILTERS: { key: TypeFilter; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'manual', label: '手工' },
  { key: 'auto', label: '自动化' },
];

export function getCaseTypeLabel(type: CaseType): string {
  return type === 'manual' ? '手工' : '自动';
}

export const CASE_STATUS_LABELS: Record<string, string> = {
  ACTIVE: '活跃', INACTIVE: '停用', DRAFT: '草稿',
  DEPRECATED: '废弃', DONE: '已完成',
  PENDING_REVIEW: '待评审', IN_REVIEW: '评审中', REJECTED: '已驳回',
};

/* ── Helpers ── */

export function getCaseStatusLabel(status: string): string {
  return CASE_STATUS_LABELS[status] || status;
}

export function buildLabMap(labs: CatalogLab[]): Map<string, string> {
  const m = new Map<string, string>();
  for (const lab of labs) m.set(lab.lab_id, lab.name);
  return m;
}

export function buildUnifiedCaseList(
  manualCases: TestCaseResponse[],
  autoCases: AutomationTestCaseResponse[],
  labMap: Map<string, string>,
): UnifiedCaseItem[] {
  const result: UnifiedCaseItem[] = [];
  for (const mc of manualCases) {
    result.push({
      type: 'manual',
      id: mc.id,
      caseId: mc.case_id,
      title: mc.title,
      status: mc.status,
      priority: mc.priority,
      version: mc.version,
      updatedAt: mc.updated_at,
      manualData: mc,
      labId: mc.lab_id,
      catalogPath: mc.catalog_path?.length ? mc.catalog_path : undefined,
      labName: mc.lab_id ? labMap.get(mc.lab_id) || mc.lab_name || undefined : undefined,
      tags: mc.tags?.length ? mc.tags : undefined,
    });
  }
  for (const ac of autoCases) {
    result.push({
      type: 'auto',
      id: ac.id,
      caseId: ac.auto_case_id,
      title: ac.name,
      status: ac.status,
      framework: ac.framework,
      automationType: ac.automation_type,
      version: ac.version,
      updatedAt: ac.updated_at,
      autoData: ac,
      tags: ac.tags?.length ? ac.tags : undefined,
    });
  }
  return result.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
}

export function matchesCatalogPrefix(catalogPath: string[] | undefined, prefix: string[]): boolean {
  if (prefix.length === 0) return true;
  if (!catalogPath || catalogPath.length < prefix.length) return false;
  for (let i = 0; i < prefix.length; i++) {
    if (catalogPath[i] !== prefix[i]) return false;
  }
  return true;
}

export function collectAllTags(items: UnifiedCaseItem[]): string[] {
  const set = new Set<string>();
  for (const item of items) {
    item.tags?.forEach(tag => set.add(tag));
  }
  return Array.from(set).sort();
}

export function getCaseDisplayTitle(
  type: CaseType,
  caseId: string,
  manualMap: Map<string, TestCaseResponse>,
  autoMap: Map<string, AutomationTestCaseResponse>,
): string {
  if (type === 'manual') return manualMap.get(caseId)?.title || caseId;
  return autoMap.get(caseId)?.name || caseId;
}
