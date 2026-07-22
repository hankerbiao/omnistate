/**
 * CreatePlanWizard — Multi-step plan creation wizard.
 * Redesigned: standard modal sheet pattern with fixed header/body/footer.
 */
import { useMemo, useState } from 'react';
import { Dialog, DialogClose, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Calendar,
  FileText,
  Info,
  Search,
  Sparkles,
  Users,
  UserCheck,
  ListChecks,
} from 'lucide-react';
import { DateRangePicker } from '../DateRangePicker';
import type { NewPlanData, CaseMapEntry, CollectionEntry } from '../types';
import { PRIORITY_COLORS } from '../types';
import type { UserResponse } from '../../../types';
import AiRecommendCasesPanel from '../../ui/AiRecommendCasesPanel';

interface CreatePlanWizardProps {
  wizardStep: number;
  onStepChange: (s: number) => void;
  newPlan: NewPlanData;
  onNewPlanChange: (updater: (p: NewPlanData) => NewPlanData) => void;
  caseSearch: string;
  onCaseSearchChange: (s: string) => void;
  submittingPlan: boolean;
  onCreatePlan: () => void;
  onClose: () => void;
  onToggleCase: (cid: string) => void;
  onToggleCollection: (col: { collection_id: string; name: string }) => void;
  onSetAssignment: (caseId: string, value: string) => void;
  users: UserResponse[];
  collections: CollectionEntry[];
  caseMap: Map<string, CaseMapEntry>;
  casesLoading: boolean;
  currentUserId: string;
}

type CaseTab = 'all' | 'collections' | 'manual' | 'auto' | 'high';
type CaseFilter = { key: string; label: string; value: string };
type AssignTypeFilter = 'all' | 'manual' | 'auto';

const STEP_LABELS = ['基本信息', '选择用例', '分配执行人', '排期确认'];

const caseIncludesQuery = (tc: CaseMapEntry, q: string) => {
  if (!q) return true;
  return [
    tc.id,
    tc.title,
    tc.priority,
    tc.testCategory,
    tc.labId,
    tc.labName || '',
    tc.catalogBreadcrumb || '',
    ...(tc.catalogPath || []),
    tc.framework || '',
    ...(tc.tags || []),
  ].some(v => String(v || '').toLowerCase().includes(q));
};

const getCaseGroupLabel = (tc: CaseMapEntry) => (
  tc.catalogBreadcrumb || tc.catalogPath?.join(' / ') || tc.labName || tc.framework || tc.testCategory || '未分类'
);

const getUserLabel = (users: UserResponse[], userId?: string) => {
  if (!userId) return '未设置';
  const u = users.find(item => item.user_id === userId);
  return u?.username || userId;
};

const getCollectionIds = (col: CollectionEntry) => [...(col.case_ids || []), ...(col.auto_case_ids || [])];

export function CreatePlanWizard({
  wizardStep, onStepChange, newPlan, onNewPlanChange, caseSearch, onCaseSearchChange,
  submittingPlan, onCreatePlan, onClose, onToggleCase, onToggleCollection, onSetAssignment,
  users, collections, caseMap, casesLoading, currentUserId,
}: CreatePlanWizardProps) {
  const [showAiRecommend, setShowAiRecommend] = useState(false);
  const [activeCaseTab, setActiveCaseTab] = useState<CaseTab>('all');
  const [caseFilter, setCaseFilter] = useState<CaseFilter | null>(null);
  const [showSelectedOnly, setShowSelectedOnly] = useState(false);
  const [assignSearch, setAssignSearch] = useState('');
  const [assignTypeFilter, setAssignTypeFilter] = useState<AssignTypeFilter>('all');
  const [focusedAssignIds, setFocusedAssignIds] = useState<string[]>([]);
  const [typeAssignees, setTypeAssignees] = useState({ manual: '', auto: '' });

  const q = caseSearch.trim().toLowerCase();
  const selectedSet = useMemo(() => new Set(newPlan.selectedCases), [newPlan.selectedCases]);
  const userIds = useMemo(() => new Set(users.map(u => u.user_id)), [users]);
  const allCases = useMemo(() => Array.from(caseMap.values()), [caseMap]);
  const selectedCases = useMemo(
    () => newPlan.selectedCases.map(cid => caseMap.get(cid)).filter((tc): tc is CaseMapEntry => Boolean(tc)),
    [caseMap, newPlan.selectedCases],
  );

  const tabCounts = useMemo(() => ({
    all: allCases.length,
    collections,
    manual: allCases.filter(tc => tc.type === 'manual').length,
    auto: allCases.filter(tc => tc.type === 'auto').length,
    high: allCases.filter(tc => tc.priority === 'P0' || tc.priority === 'P1').length,
  }), [allCases, collections]);

  const matchedCollections = useMemo(() => {
    if (activeCaseTab !== 'all' && activeCaseTab !== 'collections') return [];
    return collections.filter(col => {
      if (!q) return true;
      return [
        col.name,
        col.description || '',
        ...(col.tags || []),
      ].some(v => String(v || '').toLowerCase().includes(q));
    });
  }, [activeCaseTab, collections, q]);

  const filterOptions = useMemo(() => {
    const makeOptions = (kind: string, labeler: (tc: CaseMapEntry) => string | undefined, limit = 8) => {
      const counts = new Map<string, number>();
      for (const tc of allCases) {
        const label = labeler(tc);
        if (!label) continue;
        counts.set(label, (counts.get(label) || 0) + 1);
      }
      return Array.from(counts.entries())
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .slice(0, limit)
        .map(([label, count]) => ({ key: `${kind}:${label}`, label: `${label} ${count}`, value: label }));
    };
    return [
      ...makeOptions('priority', tc => tc.priority),
      ...makeOptions('group', getCaseGroupLabel, 10),
      ...makeOptions('tag', tc => tc.tags?.[0], 8),
      ...makeOptions('owner', tc => tc.defaultOwnerId ? getUserLabel(users, tc.defaultOwnerId) : undefined, 8),
    ];
  }, [allCases, users]);

  const filteredCases = useMemo(() => {
    return allCases.filter(tc => {
      if (activeCaseTab === 'collections') return false;
      if (activeCaseTab === 'manual' && tc.type !== 'manual') return false;
      if (activeCaseTab === 'auto' && tc.type !== 'auto') return false;
      if (activeCaseTab === 'high' && tc.priority !== 'P0' && tc.priority !== 'P1') return false;
      if (showSelectedOnly && !selectedSet.has(tc.id)) return false;
      if (!caseIncludesQuery(tc, q)) return false;
      if (!caseFilter) return true;
      const [kind] = caseFilter.key.split(':');
      if (kind === 'priority') return tc.priority === caseFilter.value;
      if (kind === 'group') return getCaseGroupLabel(tc) === caseFilter.value;
      if (kind === 'tag') return (tc.tags || []).includes(caseFilter.value);
      if (kind === 'owner') return getUserLabel(users, tc.defaultOwnerId) === caseFilter.value;
      return true;
    });
  }, [activeCaseTab, allCases, caseFilter, q, selectedSet, showSelectedOnly, users]);

  const assignCases = useMemo(() => {
    const query = assignSearch.trim().toLowerCase();
    return selectedCases.filter(tc => {
      if (assignTypeFilter !== 'all' && tc.type !== assignTypeFilter) return false;
      if (!query) return true;
      return caseIncludesQuery(tc, query) || getUserLabel(users, newPlan.assignments[tc.id]?.assignee).toLowerCase().includes(query);
    });
  }, [assignSearch, assignTypeFilter, newPlan.assignments, selectedCases, users]);

  const assignmentStats = useMemo(() => {
    const stats = new Map<string, { assigneeId: string; label: string; total: number; manual: number; auto: number }>();
    for (const tc of selectedCases) {
      const assigneeId = newPlan.assignments[tc.id]?.assignee || '';
      const key = assigneeId || '__unassigned__';
      const label = assigneeId ? getUserLabel(users, assigneeId) : '未分配';
      const row = stats.get(key) || { assigneeId, label, total: 0, manual: 0, auto: 0 };
      row.total += 1;
      if (tc.type === 'auto') row.auto += 1;
      else row.manual += 1;
      stats.set(key, row);
    }
    return Array.from(stats.values()).sort((a, b) => b.total - a.total || a.label.localeCompare(b.label));
  }, [newPlan.assignments, selectedCases, users]);

  const visibleCaseIds = filteredCases.map(tc => tc.id);
  const focusedSet = new Set(focusedAssignIds);
  const selectedVisibleCount = visibleCaseIds.filter(id => selectedSet.has(id)).length;
  const assignmentTargetIds = focusedAssignIds.filter(id => selectedSet.has(id));

  const setSelectedCases = (caseIds: string[]) => {
    onNewPlanChange(prev => ({
      ...prev,
      selectedCases: caseIds,
      assignments: Object.fromEntries(Object.entries(prev.assignments).filter(([id]) => caseIds.includes(id))),
    }));
  };

  const selectVisibleCases = () => {
    const ids = new Set(newPlan.selectedCases);
    visibleCaseIds.forEach(id => ids.add(id));
    setSelectedCases(Array.from(ids));
  };

  const clearVisibleCases = () => {
    const visible = new Set(visibleCaseIds);
    setSelectedCases(newPlan.selectedCases.filter(id => !visible.has(id)));
    setFocusedAssignIds(prev => prev.filter(id => !visible.has(id)));
  };

  const setAssignmentsFor = (caseIds: string[], assigneeId: string) => {
    onNewPlanChange(prev => ({
      ...prev,
      assignments: {
        ...prev.assignments,
        ...Object.fromEntries(caseIds.map(id => [id, { assignee: assigneeId }])),
      },
    }));
  };

  const assignAllToMe = () => {
    if (!currentUserId) return;
    setAssignmentsFor(newPlan.selectedCases, currentUserId);
  };

  const assignByDefaultOwner = () => {
    const fallback = currentUserId || users[0]?.user_id || '';
    onNewPlanChange(prev => ({
      ...prev,
      assignments: {
        ...prev.assignments,
        ...Object.fromEntries(selectedCases.map(tc => {
          const defaultOwner = tc.defaultOwnerId && userIds.has(tc.defaultOwnerId) ? tc.defaultOwnerId : fallback;
          return [tc.id, { assignee: defaultOwner }];
        })),
      },
    }));
  };

  const assignByType = () => {
    const updates = selectedCases
      .filter(tc => (tc.type === 'manual' ? typeAssignees.manual : typeAssignees.auto))
      .map(tc => [tc.id, { assignee: tc.type === 'manual' ? typeAssignees.manual : typeAssignees.auto }] as const);
    if (updates.length === 0) return;
    onNewPlanChange(prev => ({ ...prev, assignments: { ...prev.assignments, ...Object.fromEntries(updates) } }));
  };

  const toggleFocusCase = (caseId: string) => {
    setFocusedAssignIds(prev => prev.includes(caseId) ? prev.filter(id => id !== caseId) : [...prev, caseId]);
  };

  const selectedManualCount = selectedCases.filter(tc => tc.type === 'manual').length;
  const selectedAutoCount = selectedCases.length - selectedManualCount;
  const unassignedCount = selectedCases.filter(tc => !newPlan.assignments[tc.id]?.assignee).length;

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[1040px] max-h-[90vh] p-0 gap-0 overflow-hidden grid grid-rows-[auto_minmax(0,1fr)_auto] rounded-2xl shadow-2xl">
        <div className="px-8 pt-7 pb-4 border-b border-[var(--border-subtle)] flex-shrink-0 bg-[var(--surface-primary)]">
          <div className="flex items-start justify-between mb-4">
            <div>
              <DialogTitle className="text-[20px] font-bold tracking-tight text-[var(--text-primary)] leading-tight">
                新建执行计划
              </DialogTitle>
              <p className="text-xs text-[var(--text-tertiary)] mt-1">按步骤填写，完成后可随时编辑</p>
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-[11px] text-[var(--text-tertiary)] bg-[var(--surface-secondary)] border border-[var(--border-subtle)] px-2.5 py-1 rounded-full font-medium">
                {wizardStep} / {STEP_LABELS.length}
              </span>
              <DialogClose className="w-7 h-7 rounded-full flex items-center justify-center text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)] transition-colors" aria-label="关闭">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M1 1L13 13M13 1L1 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                </svg>
              </DialogClose>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {STEP_LABELS.map((s, i) => {
              const step = i + 1;
              const isActive = wizardStep === step;
              const isDone = wizardStep > step;
              return (
                <div key={s} className="flex items-center gap-1.5 flex-1">
                  <div className={`flex items-center gap-2 flex-1 px-3 py-2 rounded-lg transition-all ${
                    isActive
                      ? 'bg-[var(--status-info-bg)] border border-[var(--status-info)]'
                      : isDone
                        ? 'bg-[var(--status-success-bg)] border border-[var(--status-success)]'
                        : 'bg-[var(--surface-secondary)] border border-[var(--border-subtle)]'
                  }`}>
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                      isActive
                        ? 'bg-[var(--accent-primary)] text-white'
                        : isDone
                          ? 'bg-[var(--status-success)] text-white'
                          : 'bg-[var(--surface-tertiary)] text-[var(--text-tertiary)]'
                    }`}>
                      {isDone ? <Check size={10} strokeWidth={3} /> : step}
                    </span>
                    <span className={`text-[11px] font-medium whitespace-nowrap ${
                      isActive
                        ? 'text-[var(--status-info)]'
                        : isDone
                          ? 'text-[var(--status-success)]'
                          : 'text-[var(--text-tertiary)]'
                    }`}>
                      {s}
                    </span>
                  </div>
                  {i < STEP_LABELS.length - 1 && (
                    <div className={`w-3 h-px flex-shrink-0 ${wizardStep > step ? 'bg-[var(--status-success)]' : 'bg-[var(--border-subtle)]'}`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="px-8 py-5 overflow-y-auto flex-1 min-h-0 bg-[var(--surface-secondary)]">
          {wizardStep === 1 && (
            <div className="flex flex-col gap-3.5">
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-[var(--status-info-bg)] border border-[var(--status-info)]">
                <Info size={14} className="text-[var(--status-info)] mt-0.5 flex-shrink-0" />
                <p className="text-xs text-[var(--status-info)] leading-relaxed">
                  填写计划的基本信息，这些信息将帮助团队成员快速了解计划的目标和范围。
                </p>
              </div>

              <div className="bg-[var(--surface-primary)] rounded-xl p-5 border border-[var(--border-subtle)] space-y-4">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                      <FileText size={14} className="text-[var(--status-info)]" />
                      计划名称 <span className="text-[var(--status-error)]">*</span>
                    </label>
                    <span className={`text-xs font-medium tabular-nums ${newPlan.title.length > 50 ? 'text-[var(--status-error)]' : 'text-[var(--text-tertiary)]'}`}>
                      {newPlan.title.length}/50
                    </span>
                  </div>
                  <Input
                    value={newPlan.title}
                    onChange={e => {
                      const val = e.target.value;
                      if (val.length <= 50) onNewPlanChange(p => ({ ...p, title: val }));
                    }}
                    placeholder="例如：Sprint 3 安全回归测试"
                    autoFocus
                    className="h-10 text-sm bg-[var(--surface-secondary)]"
                  />
                  <p className="text-xs text-[var(--text-tertiary)]">建议包含迭代版本和测试范围，便于识别</p>
                </div>

                <div className="space-y-1.5">
                  <label className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                    <FileText size={14} className="text-[var(--text-tertiary)]" />
                    描述
                  </label>
                  <Textarea
                    value={newPlan.description}
                    onChange={e => onNewPlanChange(p => ({ ...p, description: e.target.value }))}
                    placeholder="说明计划的目的、覆盖范围、验收标准等..."
                    rows={3}
                    className="min-h-[72px] text-[13px] resize-none bg-[var(--surface-secondary)]"
                  />
                </div>
              </div>

              <div className="bg-[var(--surface-primary)] rounded-xl p-5 border border-[var(--border-subtle)] space-y-2.5">
                <label className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                  <Calendar size={14} className="text-[var(--status-info)]" />
                  计划周期
                </label>
                <DateRangePicker
                  startDate={newPlan.startDate}
                  endDate={newPlan.endDate}
                  onChange={(start, end) => onNewPlanChange(p => ({ ...p, startDate: start, endDate: end }))}
                />
              </div>
            </div>
          )}

          {wizardStep === 2 && (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                  <ListChecks size={15} className="text-[var(--accent-primary)]" />
                  已选 <strong className="text-[var(--text-primary)]">{newPlan.selectedCases.length}</strong> 个用例
                  <span className="text-xs text-[var(--text-tertiary)]">当前结果 {filteredCases.length} 条</span>
                </div>
                <button type="button" onClick={() => setShowAiRecommend(true)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold text-white bg-[#7c3aed] hover:opacity-90 transition-opacity">
                  <Sparkles size={12} /> AI 推荐
                </button>
              </div>

              <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-xl p-3 space-y-3">
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { key: 'all' as const, label: '全部', count: tabCounts.all },
                    { key: 'collections' as const, label: '预置集合', count: tabCounts.collections.length },
                    { key: 'manual' as const, label: '手工用例', count: tabCounts.manual },
                    { key: 'auto' as const, label: '自动化用例', count: tabCounts.auto },
                    { key: 'high' as const, label: '高优先级', count: tabCounts.high },
                  ].map(tab => (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => { setActiveCaseTab(tab.key); setCaseFilter(null); }}
                      className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${activeCaseTab === tab.key ? 'bg-[var(--accent-primary)] text-white' : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]'}`}
                    >
                      {tab.label} <span className="tabular-nums opacity-80">{tab.count}</span>
                    </button>
                  ))}
                </div>

                <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                  <div className="relative">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]" />
                    <Input
                      value={caseSearch}
                      onChange={e => onCaseSearchChange(e.target.value)}
                      placeholder="搜索用例名称、ID、集合、标签、目录、Lab 或 Framework..."
                      className="pl-8 text-sm bg-[var(--surface-secondary)]"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowSelectedOnly(v => !v)}
                    className={`px-3 rounded-md text-xs font-semibold border transition-colors ${showSelectedOnly ? 'border-[var(--accent-primary)] text-[var(--accent-primary)] bg-[var(--status-info-bg)]' : 'border-[var(--border-subtle)] text-[var(--text-secondary)] bg-[var(--surface-secondary)] hover:bg-[var(--surface-hover)]'}`}
                  >
                    只看已选
                  </button>
                </div>

                <div className="flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    onClick={() => setCaseFilter(null)}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-medium ${!caseFilter ? 'bg-[var(--text-primary)] text-[var(--surface-primary)]' : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)]'}`}
                  >
                    不限条件
                  </button>
                  {filterOptions.map(filter => (
                    <button
                      key={filter.key}
                      type="button"
                      onClick={() => setCaseFilter(caseFilter?.key === filter.key ? null : filter)}
                      title={filter.value}
                      className={`max-w-[180px] truncate px-2.5 py-1 rounded-md text-[11px] font-medium ${caseFilter?.key === filter.key ? 'bg-[var(--accent-primary)] text-white' : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]'}`}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <Button size="sm" variant="secondary" onClick={selectVisibleCases} disabled={visibleCaseIds.length === 0}>
                    选择当前结果
                  </Button>
                  <Button size="sm" variant="ghost" onClick={clearVisibleCases} disabled={selectedVisibleCount === 0}>
                    取消当前结果
                  </Button>
                  <span className="text-[var(--text-tertiary)]">当前结果已选 {selectedVisibleCount} / {visibleCaseIds.length}</span>
                </div>
              </div>

              {casesLoading ? (
                <div className="py-10 text-center text-sm text-[var(--text-tertiary)]">加载用例中...</div>
              ) : (
                <div className="grid grid-cols-1 gap-2">
                  {matchedCollections.map(col => {
                    const collectionIds = getCollectionIds(col);
                    const selectedCount = collectionIds.filter(id => selectedSet.has(id)).length;
                    const allSelected = collectionIds.length > 0 && selectedCount === collectionIds.length;
                    return (
                      <button
                        type="button"
                        key={col.collection_id}
                        onClick={() => onToggleCollection(col)}
                        className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg cursor-pointer border border-[var(--border-subtle)] bg-[var(--surface-primary)] hover:bg-[var(--surface-hover)] hover:border-[var(--border-default)] transition-colors text-left"
                      >
                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 ${allSelected ? 'bg-[var(--accent-primary)] border-[var(--accent-primary)]' : 'border-[var(--border-default)]'}`}>
                          {allSelected && <Check size={11} className="text-white" strokeWidth={3} />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">{col.name}</div>
                          {col.description && <div className="text-[11px] text-[var(--text-tertiary)] mt-0.5 truncate">{col.description}</div>}
                        </div>
                        <Badge variant="secondary">{col.case_count + (col.auto_case_count || 0)} 个用例</Badge>
                        <span className="text-[11px] text-[var(--text-tertiary)] min-w-[70px] text-right">
                          {collectionIds.length > 0 ? `${selectedCount}/${collectionIds.length}` : '点击选择'}
                        </span>
                      </button>
                    );
                  })}

                  {filteredCases.map(tc => {
                    const sel = selectedSet.has(tc.id);
                    return (
                      <button
                        key={tc.id}
                        type="button"
                        onClick={() => onToggleCase(tc.id)}
                        className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg cursor-pointer transition-colors text-left"
                        style={{
                          border: sel ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                          background: sel ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'var(--surface-primary)',
                        }}
                      >
                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${sel ? 'bg-[var(--accent-primary)] border-[var(--accent-primary)]' : 'border-[var(--border-default)]'}`}>
                          {sel && <Check size={11} className="text-white" strokeWidth={3} />}
                        </div>
                        <span className="text-[11px] font-mono text-[var(--text-tertiary)] w-[74px] truncate">{tc.id}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm truncate" style={{ fontWeight: sel ? 600 : 500 }}>{tc.title}</div>
                          <div className="text-[11px] text-[var(--text-tertiary)] truncate">
                            {getCaseGroupLabel(tc)}
                            {tc.tags?.length ? ` | ${tc.tags.slice(0, 3).join(', ')}` : ''}
                          </div>
                        </div>
                        <Badge variant={tc.type === 'auto' ? 'info' : 'secondary'}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</Badge>
                        {tc.priority && <span className="text-[11px] font-semibold w-6 text-right" style={{ color: PRIORITY_COLORS[tc.priority] }}>{tc.priority}</span>}
                        <span className="text-[11px] text-[var(--text-tertiary)] w-[72px] truncate text-right">{getUserLabel(users, tc.defaultOwnerId)}</span>
                      </button>
                    );
                  })}

                  {matchedCollections.length === 0 && filteredCases.length === 0 && (
                    <div className="py-10 text-center text-sm text-[var(--text-tertiary)]">无匹配的用例或集合</div>
                  )}
                </div>
              )}
            </div>
          )}

          {wizardStep === 3 && (
            <div className="grid grid-cols-[minmax(0,1.35fr)_minmax(260px,0.65fr)] gap-4">
              <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-xl p-3 min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div>
                    <div className="text-sm font-semibold text-[var(--text-primary)]">待分配用例</div>
                    <div className="text-xs text-[var(--text-tertiary)]">选中左侧用例后，在右侧一键分配给执行人</div>
                  </div>
                  <div className="flex items-center gap-1">
                    {(['all', 'manual', 'auto'] as AssignTypeFilter[]).map(key => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setAssignTypeFilter(key)}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-semibold ${assignTypeFilter === key ? 'bg-[var(--accent-primary)] text-white' : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)]'}`}
                      >
                        {key === 'all' ? '全部' : key === 'manual' ? '手工' : '自动'}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="relative mb-2">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]" />
                  <Input
                    value={assignSearch}
                    onChange={e => setAssignSearch(e.target.value)}
                    placeholder="搜索已选用例、目录、标签或执行人..."
                    className="pl-8 text-sm bg-[var(--surface-secondary)]"
                  />
                </div>

                <div className="flex items-center justify-between mb-2 text-xs text-[var(--text-tertiary)]">
                  <span>当前显示 {assignCases.length} 条，已聚焦 {assignmentTargetIds.length} 条</span>
                  <div className="flex gap-2">
                    <button type="button" className="text-[var(--accent-primary)] hover:underline" onClick={() => setFocusedAssignIds(assignCases.map(tc => tc.id))}>全选当前</button>
                    <button type="button" className="text-[var(--text-tertiary)] hover:underline" onClick={() => setFocusedAssignIds([])}>清空聚焦</button>
                  </div>
                </div>

                <div className="max-h-[390px] overflow-y-auto flex flex-col gap-1.5 pr-1">
                  {assignCases.length === 0 ? (
                    <div className="py-10 text-center text-sm text-[var(--text-tertiary)]">暂无已选用例</div>
                  ) : assignCases.map(tc => {
                    const focused = focusedSet.has(tc.id);
                    return (
                      <div
                        key={tc.id}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${focused ? 'border-[var(--accent-primary)] bg-[var(--status-info-bg)]' : 'border-[var(--border-subtle)] bg-[var(--surface-secondary)]'}`}
                      >
                        <button
                          type="button"
                          onClick={() => toggleFocusCase(tc.id)}
                          className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${focused ? 'bg-[var(--accent-primary)] border-[var(--accent-primary)]' : 'border-[var(--border-default)]'}`}
                          aria-label={focused ? '取消聚焦用例' : '聚焦用例'}
                        >
                          {focused && <Check size={11} className="text-white" strokeWidth={3} />}
                        </button>
                        <span className="font-mono text-[10px] text-[var(--text-tertiary)] w-[66px] truncate">{tc.id}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-semibold truncate">{tc.title}</div>
                          <div className="text-[10px] text-[var(--text-tertiary)] truncate">{getCaseGroupLabel(tc)}</div>
                        </div>
                        <Badge variant={tc.type === 'auto' ? 'info' : 'secondary'}>{tc.type === 'auto' ? '自动' : '手工'}</Badge>
                        <Select className="w-[130px] text-xs" value={newPlan.assignments[tc.id]?.assignee || ''} onChange={e => onSetAssignment(tc.id, e.target.value)}>
                          <option value="">未指派</option>
                          {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                        </Select>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-xl p-3 min-w-0">
                <div className="flex items-center gap-2 mb-3">
                  <Users size={15} className="text-[var(--accent-primary)]" />
                  <div>
                    <div className="text-sm font-semibold text-[var(--text-primary)]">执行人分布</div>
                    <div className="text-xs text-[var(--text-tertiary)]">未聚焦用例时，先在左侧选择要分派的用例</div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div className="rounded-lg bg-[var(--surface-secondary)] p-2">
                    <div className="text-[10px] text-[var(--text-tertiary)]">总数</div>
                    <div className="text-lg font-bold">{selectedCases.length}</div>
                  </div>
                  <div className="rounded-lg bg-[var(--surface-secondary)] p-2">
                    <div className="text-[10px] text-[var(--text-tertiary)]">手工/自动</div>
                    <div className="text-sm font-bold">{selectedManualCount}/{selectedAutoCount}</div>
                  </div>
                  <div className="rounded-lg bg-[var(--surface-secondary)] p-2">
                    <div className="text-[10px] text-[var(--text-tertiary)]">未分配</div>
                    <div className="text-lg font-bold text-[var(--status-warning)]">{unassignedCount}</div>
                  </div>
                </div>

                <div className="flex flex-col gap-2 mb-3">
                  <Button size="sm" variant="secondary" onClick={assignAllToMe} disabled={!currentUserId || selectedCases.length === 0}>
                    <UserCheck size={14} /> 全部分配给我
                  </Button>
                  <Button size="sm" variant="secondary" onClick={assignByDefaultOwner} disabled={selectedCases.length === 0}>
                    按默认负责人分配
                  </Button>
                  <div className="grid grid-cols-[1fr_1fr_auto] gap-1.5">
                    <Select className="text-xs" value={typeAssignees.manual} onChange={e => setTypeAssignees(prev => ({ ...prev, manual: e.target.value }))}>
                      <option value="">手工执行人</option>
                      {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                    </Select>
                    <Select className="text-xs" value={typeAssignees.auto} onChange={e => setTypeAssignees(prev => ({ ...prev, auto: e.target.value }))}>
                      <option value="">自动执行人</option>
                      {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                    </Select>
                    <Button size="sm" variant="ghost" onClick={assignByType} disabled={!typeAssignees.manual && !typeAssignees.auto}>应用</Button>
                  </div>
                </div>

                <div className="space-y-1.5 mb-3">
                  {users.map(u => {
                    const stat = assignmentStats.find(item => item.assigneeId === u.user_id);
                    return (
                      <button
                        type="button"
                        key={u.user_id}
                        onClick={() => setAssignmentsFor(assignmentTargetIds, u.user_id)}
                        disabled={assignmentTargetIds.length === 0}
                        className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-left disabled:opacity-50 enabled:hover:border-[var(--accent-primary)] transition-colors"
                      >
                        <span className="text-xs font-semibold truncate">{u.username}</span>
                        <span className="text-[11px] text-[var(--text-tertiary)]">{stat?.total || 0} 条</span>
                      </button>
                    );
                  })}
                </div>

                <div className="border-t border-[var(--border-subtle)] pt-3 space-y-1.5">
                  {assignmentStats.length === 0 ? (
                    <div className="text-xs text-[var(--text-tertiary)]">暂无分配数据</div>
                  ) : assignmentStats.map(stat => (
                    <div key={stat.assigneeId || 'unassigned'} className="flex items-center justify-between text-xs">
                      <span className="font-medium truncate">{stat.label}</span>
                      <span className="text-[var(--text-tertiary)]">{stat.total} 条 | 手工 {stat.manual} / 自动 {stat.auto}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {wizardStep === 4 && (
            <div className="flex flex-col gap-5">
              <div className="bg-[var(--surface-primary)] rounded-xl p-4 border border-[var(--border-subtle)]">
                <div className="text-sm font-semibold text-[var(--text-primary)] mb-3">计划概览</div>
                <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
                  <span className="text-[var(--text-tertiary)]">名称</span>
                  <span className="font-medium text-[var(--text-primary)]">{newPlan.title || '-'}</span>
                  <span className="text-[var(--text-tertiary)]">周期</span>
                  <span className="text-[var(--text-primary)]">{newPlan.startDate || '-'} 至 {newPlan.endDate || '-'}</span>
                  <span className="text-[var(--text-tertiary)]">用例数</span>
                  <span className="font-semibold text-[var(--text-primary)]">
                    {selectedCases.length} 个（{selectedAutoCount} 自动 / {selectedManualCount} 手动）
                  </span>
                  <span className="text-[var(--text-tertiary)]">未分配</span>
                  <span className="font-semibold text-[var(--text-primary)]">{unassignedCount} 个</span>
                </div>
              </div>

              <div className="bg-[var(--surface-primary)] rounded-xl p-4 border border-[var(--border-subtle)]">
                <div className="text-sm font-semibold text-[var(--text-primary)] mb-3">执行人分布</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {assignmentStats.length === 0 ? (
                    <div className="text-sm text-[var(--text-tertiary)]">暂无分配数据</div>
                  ) : assignmentStats.map(stat => (
                    <div key={stat.assigneeId || 'unassigned'} className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-secondary)] px-3 py-2">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-semibold truncate">{stat.label}</span>
                        <span className="text-sm font-bold">{stat.total}</span>
                      </div>
                      <div className="text-[11px] text-[var(--text-tertiary)] mt-1">手工 {stat.manual} / 自动 {stat.auto}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="px-8 py-3.5 border-t border-[var(--border-subtle)] flex items-center justify-between flex-shrink-0 bg-[var(--surface-primary)]">
          <Button variant="ghost" size="sm" onClick={() => wizardStep > 1 ? onStepChange(wizardStep - 1) : onClose()} className="text-[var(--text-secondary)]">
            {wizardStep > 1 ? <><ChevronLeft size={16} /> 上一步</> : '取消'}
          </Button>
          <div className="flex items-center gap-3">
            {wizardStep < 4 && (
              <span className="text-xs text-[var(--text-tertiary)]">
                还有 {STEP_LABELS.length - wizardStep} 个步骤
              </span>
            )}
            {wizardStep < 4 ? (
              <Button
                size="sm"
                onClick={() => onStepChange(wizardStep + 1)}
                disabled={(wizardStep === 1 && !newPlan.title.trim()) || (wizardStep === 2 && newPlan.selectedCases.length === 0)}
                className="px-5"
                style={{
                  background: 'var(--accent-primary)',
                  color: 'white',
                  opacity: (wizardStep === 1 && !newPlan.title.trim()) || (wizardStep === 2 && newPlan.selectedCases.length === 0) ? 0.5 : 1,
                }}
              >
                下一步 <ChevronRight size={16} />
              </Button>
            ) : (
              <Button size="sm" onClick={onCreatePlan} disabled={newPlan.selectedCases.length === 0 || submittingPlan} className="px-5" style={{ background: 'var(--accent-primary)', color: 'white', opacity: submittingPlan ? 0.5 : 1 }}>
                {submittingPlan ? '创建中...' : '创建计划'}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
      {showAiRecommend && (
        <AiRecommendCasesPanel
          onSelectCases={(ids) => {
            ids.forEach(id => {
              if (!newPlan.selectedCases.includes(id)) {
                onToggleCase(id);
              }
            });
          }}
          onClose={() => setShowAiRecommend(false)}
        />
      )}
    </Dialog>
  );
}
