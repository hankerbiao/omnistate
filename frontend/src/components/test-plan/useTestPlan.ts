/**
 * useTestPlan — Custom hook for Test Execution Plan
 * Extracts all state management & API calls from the original 2607-line component.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../../services/api';
import type { UserResponse } from '../../types';
import type {
  PlanSummary, PlanItemSummary, ViewMode, NewPlanData, CaseMapEntry,
} from './types';
import { emptyNewPlan } from './types';

interface PlanListPayload {
  items?: PlanSummary[];
}

interface PlanDetailPayload {
  items?: PlanItemSummary[];
}

type LoadedCaseEntry = CaseMapEntry & {
  case_id: string;
};

export function useTestPlan() {
  // ── Plans ──
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activePlanId, setActivePlanId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // ── Plan detail ──
  const [activePlanItems, setActivePlanItems] = useState<PlanItemSummary[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('statusBoard');

  // ── Edit mode ──
  const [editingPlanId, setEditingPlanId] = useState<string>('');
  const [editingItems, setEditingItems] = useState<PlanItemSummary[]>([]);
  const [selectedAddCaseIds, setSelectedAddCaseIds] = useState<string[]>([]);
  const [showAddCases, setShowAddCases] = useState(false);
  const [saving, setSaving] = useState(false);
  const isEditing = editingPlanId === activePlanId && activePlanId !== '';

  // ── Users ──
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [currentUserId, setCurrentUserId] = useState('');

  // ── Refresh ──
  const [refreshDetail, setRefreshDetail] = useState(0);

  // ── Test cases ──
  const [testCases, setTestCases] = useState<Record<string, LoadedCaseEntry>>({});
  const [casesLoading, setCasesLoading] = useState(false);

  // ── Wizard ──
  const [showWizard, setShowWizard] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [caseSearch, setCaseSearch] = useState('');
  const [submittingPlan, setSubmittingPlan] = useState(false);
  const [newPlan, setNewPlan] = useState<NewPlanData>(emptyNewPlan);

  // ── Result viewer ──
  const [resultModal, setResultModal] = useState<{
    item: PlanItemSummary;
    taskData: unknown;
    timelineData: unknown;
    loading: boolean;
    error?: string;
  } | null>(null);

  // ── Rerun confirm ──
  const [rerunConfirm, setRerunConfirm] = useState<PlanItemSummary | null>(null);

  const activePlan = plans.find(p => p.plan_id === activePlanId);

  // ── Derived: filtered plans ──
  const filteredPlans = useMemo(() => {
    return plans.filter(p => {
      if (searchQuery && !p.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (statusFilter && p.status !== statusFilter) return false;
      return true;
    });
  }, [plans, searchQuery, statusFilter]);

  // ── Load test cases lazily ──
  const loadCases = useCallback(async () => {
    if (Object.keys(testCases).length > 0 || casesLoading) return;
    setCasesLoading(true);
    try {
      const [manualRes, autoRes] = await Promise.all([
        api.listTestCases({ limit: 200 }),
        api.listAutomationTestCases({ limit: 200 }),
      ]);
      const map: Record<string, LoadedCaseEntry> = {};
      for (const tc of (manualRes.data || [])) {
        map[tc.case_id] = {
          case_id: tc.case_id,
          id: tc.case_id,
          title: tc.title,
          type: 'manual',
          priority: tc.priority || 'P3',
          createdAt: tc.created_at || '',
          tags: tc.tags || [],
          testCategory: tc.test_category,
          labId: tc.lab_id,
          labName: tc.lab_name,
          catalogPath: tc.catalog_path || [],
          catalogBreadcrumb: tc.catalog_breadcrumb,
          defaultOwnerId: tc.owner_id,
        };
      }
      for (const atc of (autoRes.data || [])) {
        map[atc.auto_case_id] = {
          case_id: atc.auto_case_id,
          id: atc.auto_case_id,
          title: atc.name,
          type: 'auto',
          priority: 'P3',
          createdAt: atc.created_at || '',
          tags: atc.tags || [],
          framework: atc.framework,
          defaultOwnerId: atc.maintainer_id,
        };
      }
      setTestCases(map);
    } catch {
      setTestCases({});
    } finally {
      setCasesLoading(false);
    }
  }, [testCases, casesLoading]);

  const caseMap = useMemo(() => new Map< string, CaseMapEntry>(
    Object.values(testCases)
      .sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''))
      .map(tc => [tc.case_id, {
        id: tc.case_id,
        title: tc.title,
        type: tc.type,
        priority: tc.priority,
        createdAt: tc.createdAt,
        tags: tc.tags,
        testCategory: tc.testCategory,
        labId: tc.labId,
        labName: tc.labName,
        catalogPath: tc.catalogPath,
        catalogBreadcrumb: tc.catalogBreadcrumb,
        framework: tc.framework,
        defaultOwnerId: tc.defaultOwnerId,
      }]),
  ), [testCases]);

  // ── Fetch plans ──
  const fetchPlans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listPlans();
      const plansData = res.data as PlanListPayload | null;
      setPlans(plansData?.items || []);
    } catch {
      setError('获取计划列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void fetchPlans(); }, [fetchPlans]);

  const handleRefresh = useCallback(() => {
    fetchPlans();
    setRefreshDetail(v => v + 1);
  }, [fetchPlans]);

  // ── Fetch users on mount ──
  useEffect(() => {
    api.listUsers({ limit: 200 })
      .then(res => {
        setUsers(res.data || []);
        setCurrentUserId(res.data?.[0]?.user_id || '');
      })
      .catch(() => {
        api.getCurrentUser().then(u => {
          if (u.data) { setUsers([u.data]); setCurrentUserId(u.data.user_id); }
        }).catch(() => setUsers([]));
      });
  }, []);

  // ── Fetch plan detail ──
  const refreshPlanDetail = useCallback(async (planId: string) => {
    if (!planId) { setActivePlanItems([]); return; }
    const res = await api.getPlanDetail(planId);
    const d = res.data as PlanDetailPayload | undefined;
    const items = d?.items || [];
    setActivePlanItems(items);
    setPlans(prev => prev.map(p =>
      p.plan_id === planId
        ? { ...p, item_count: items.length, done_count: items.filter(i => i.status === 'done').length }
        : p
    ));
    return items;
  }, []);

  useEffect(() => {
    if (!activePlanId) { setActivePlanItems([]); return; }
    setDetailLoading(true);
    refreshPlanDetail(activePlanId)
      .catch(() => setActivePlanItems([]))
      .finally(() => setDetailLoading(false));
  }, [activePlanId, refreshDetail, refreshPlanDetail]);

  // ── Edit actions ──
  const startEditing = useCallback(() => {
    setEditingPlanId(activePlanId);
    setEditingItems([...activePlanItems]);
    setSelectedAddCaseIds([]);
  }, [activePlanId, activePlanItems]);

  const cancelEditing = useCallback(() => {
    setEditingPlanId('');
    setEditingItems([]);
    setSelectedAddCaseIds([]);
    setShowAddCases(false);
  }, []);

  const removeEditingItem = useCallback((itemId: string) => {
    setEditingItems(prev => prev.filter(i => i.item_id !== itemId));
  }, []);

  const saveEditing = useCallback(async () => {
    if (!activePlanId) return;
    setSaving(true);
    try {
      const removedIds = activePlanItems
        .filter(orig => !editingItems.find(e => e.item_id === orig.item_id))
        .map(i => i.item_id);
      for (const id of removedIds) await api.deletePlanItem(activePlanId, id);

      const existingCaseIds = new Set(activePlanItems.map(i => i.case_id));
      const newItems = editingItems
        .filter(e => !existingCaseIds.has(e.case_id))
        .map(e => ({
          ref_type: e.ref_type === 'auto' ? 'auto' as const : 'manual' as const,
          case_id: e.case_id,
          assignee_id: e.assignee_id || undefined,
        }));
      if (newItems.length > 0) await api.addPlanItems(activePlanId, { items: newItems });

      const changedItems = editingItems.filter(e => {
        const orig = activePlanItems.find(o => o.item_id === e.item_id);
        return orig && orig.assignee_id !== e.assignee_id;
      });
      for (const item of changedItems) {
        await api.updatePlanItem(activePlanId, item.item_id, { assignee_id: item.assignee_id || '' });
      }
      setEditingPlanId('');
      setSelectedAddCaseIds([]);
      setShowAddCases(false);
      await refreshPlanDetail(activePlanId);
    } catch (err) {
      console.error('保存失败:', err);
      try { await refreshPlanDetail(activePlanId); } catch { /* ignore */ }
      setEditingPlanId('');
      setSelectedAddCaseIds([]);
      setShowAddCases(false);
    } finally {
      setSaving(false);
    }
  }, [activePlanId, activePlanItems, editingItems, refreshPlanDetail]);

  const handleAddCaseToggle = useCallback((cid: string) => {
    setSelectedAddCaseIds(prev =>
      prev.includes(cid) ? prev.filter(c => c !== cid) : [...prev, cid],
    );
  }, []);

  const handleAddSelectedCases = useCallback((assigneeId: string) => {
    setEditingItems(prev => {
      const existingIds = new Set(prev.map(i => i.case_id));
      const newItems = selectedAddCaseIds
        .filter(cid => !existingIds.has(cid))
        .map((cid, i) => {
          const tc = caseMap.get(cid);
          return {
            item_id: `new-${cid}-${Date.now()}`,
            case_id: cid,
            case_title: tc?.title || cid,
            ref_type: tc?.type === 'auto' ? 'auto' : 'manual',
            component: '',
            priority: tc?.priority || 'P3',
            assignee_id: assigneeId || null,
            status: 'pending',
            order_no: prev.length + i + 1,
          } as PlanItemSummary;
        });
      return [...prev, ...newItems];
    });
    setShowAddCases(false);
    setSelectedAddCaseIds([]);
  }, [selectedAddCaseIds, caseMap]);

  const handleUpdateItemAssignee = useCallback((itemId: string, assigneeId: string) => {
    setEditingItems(prev => prev.map(item =>
      item.item_id === itemId ? { ...item, assignee_id: assigneeId || null } : item
    ));
  }, []);

  // ── Batch assign ──
  const handleBatchAssign = useCallback(async (itemIds: string[], assigneeId: string) => {
    if (!activePlanId || itemIds.length === 0) return;
    try {
      await api.batchUpdateAssignee(activePlanId, { item_ids: itemIds, assignee_id: assigneeId });
      const updateItems = (items: PlanItemSummary[]) => items.map(item =>
        itemIds.includes(item.item_id) ? { ...item, assignee_id: assigneeId } : item
      );
      setEditingItems(updateItems);
      setActivePlanItems(updateItems);
    } catch (err) {
      console.error('批量指派失败:', err);
    }
  }, [activePlanId]);

  // ── Delete ──
  const handleDeleteItem = useCallback(async (planId: string, itemId: string) => {
    try {
      try { await api.cancelExecution(itemId); } catch { /* no task */ }
      await api.deletePlanItem(planId, itemId);
      if (activePlanId) await refreshPlanDetail(activePlanId);
    } catch (err) {
      console.error('删除失败:', err);
    }
  }, [activePlanId, refreshPlanDetail]);

  const handleDeletePlan = useCallback(async (planId: string) => {
    if (!window.confirm('确定要删除该执行计划及其所有条目？此操作不可撤销。')) return;
    try {
      await api.deletePlan(planId);
      setActivePlanId('');
      setActivePlanItems([]);
      await fetchPlans();
    } catch (err) {
      console.error('删除计划失败:', err);
    }
  }, [fetchPlans]);

  // ── View result ──
  const handleViewResult = useCallback(async (item: PlanItemSummary) => {
    if (!item.execution_task_id && !item.result) return;
    if (item.execution_task_id) {
      setResultModal({ item, taskData: null, timelineData: null, loading: true });
      try {
        const [statusRes, timelineRes] = await Promise.all([
          api.getTaskStatus(item.execution_task_id),
          api.getTaskTimeline(item.execution_task_id).catch(() => null),
        ]);
        if (!statusRes.data) {
          setResultModal(prev => prev ? { ...prev, taskData: null, timelineData: null, loading: false, error: '该任务尚未执行或执行记录已清除' } : null);
          return;
        }
        setResultModal(prev => prev ? { ...prev, taskData: statusRes.data, timelineData: timelineRes?.data || null, loading: false } : null);
      } catch {
        setResultModal(prev => prev ? { ...prev, taskData: null, loading: false, error: '该任务尚未执行或执行记录已清除' } : null);
      }
    } else {
      setResultModal({ item, taskData: { manualResult: item.result }, timelineData: null, loading: false });
    }
  }, []);

  // ── Rerun ──
  const handleRerunItem = useCallback((item: PlanItemSummary) => {
    setRerunConfirm(item);
  }, []);

  const confirmRerun = useCallback(async (assigneeId: string) => {
    if (!rerunConfirm) return;
    const item = rerunConfirm;
    setRerunConfirm(null);
    try {
      if (item.archived_at) {
        try { await api.unarchiveItem(item.item_id); } catch { /* ignore */ }
      }
      await api.rerunPlanItem(item.item_id, { assignee_id: assigneeId || undefined });
      if (activePlanId) await refreshPlanDetail(activePlanId);
    } catch (err) {
      console.error('重新执行失败:', err);
    }
  }, [rerunConfirm, activePlanId, refreshPlanDetail]);

  // ── Wizard ──
  const resetWizard = useCallback(() => {
    setWizardStep(1);
    setCaseSearch('');
    setSubmittingPlan(false);
    setNewPlan(emptyNewPlan);
  }, []);

  const handleCreatePlan = useCallback(async () => {
    if (!newPlan.title.trim() || newPlan.selectedCases.length === 0) return;
    setSubmittingPlan(true);
    try {
      const planRes = await api.createPlan({
        title: newPlan.title,
        description: newPlan.description || undefined,
        start_date: newPlan.startDate || undefined,
        end_date: newPlan.endDate || undefined,
      });
      const planId = (planRes.data as Record<string, unknown>)?.plan_id as string;
      await api.addPlanItems(planId, {
        items: newPlan.selectedCases.map(cid => {
          const tc = caseMap.get(cid);
          return {
            ref_type: tc?.type === 'auto' ? 'auto' : 'manual',
            case_id: cid,
            assignee_id: newPlan.assignments[cid]?.assignee || undefined,
          };
        }),
      });
      await fetchPlans();
      setActivePlanId(planId);
    } catch (err) {
      console.error('创建计划失败:', err);
      await fetchPlans();
    } finally {
      setSubmittingPlan(false);
      setShowWizard(false);
      resetWizard();
    }
  }, [newPlan, caseMap, fetchPlans, resetWizard]);

  const toggleSelectCase = useCallback((cid: string) => {
    setNewPlan(prev => ({
      ...prev,
      selectedCases: prev.selectedCases.includes(cid)
        ? prev.selectedCases.filter(c => c !== cid)
        : [...prev.selectedCases, cid],
    }));
  }, []);

  const setAssignment = useCallback((caseId: string, value: string) => {
    setNewPlan(prev => ({
      ...prev,
      assignments: { ...prev.assignments, [caseId]: { assignee: value } },
    }));
  }, []);

  return {
    // State
    loading, error, activePlanId, searchQuery, statusFilter,
    activePlanItems, detailLoading, viewMode,
    editingItems, selectedAddCaseIds, showAddCases, saving, isEditing,
    users, currentUserId,
    casesLoading, caseMap,
    showWizard, wizardStep, caseSearch, submittingPlan, newPlan,
    resultModal, rerunConfirm,
    activePlan, filteredPlans,
    // Setters
    setActivePlanId, setSearchQuery, setStatusFilter,
    setViewMode, setShowAddCases,
    setShowWizard,
    setWizardStep, setCaseSearch, setNewPlan,
    setResultModal, setRerunConfirm, setError,
    // Actions
    handleRefresh, loadCases,
    startEditing, cancelEditing, removeEditingItem, saveEditing,
    handleAddCaseToggle, handleAddSelectedCases, handleUpdateItemAssignee,
    handleBatchAssign, handleDeleteItem, handleDeletePlan,
    handleViewResult, handleRerunItem, confirmRerun,
    resetWizard, handleCreatePlan, toggleSelectCase, setAssignment,
  };
}
