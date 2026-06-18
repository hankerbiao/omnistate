/**
 * useExecutionPlan - 执行计划状态管理 Hook
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../../../services/api';
import type { PlanSummary, PlanItemSummary, ViewMode } from '../types';

export function useExecutionPlan() {
  // Plans
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activePlanId, setActivePlanId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Plan detail
  const [activePlanItems, setActivePlanItems] = useState<PlanItemSummary[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('statusBoard');

  // Edit mode
  const [editingPlanId, setEditingPlanId] = useState<string>('');
  const [editingItems, setEditingItems] = useState<PlanItemSummary[]>([]);
  const [selectedAddCaseIds, setSelectedAddCaseIds] = useState<string[]>([]);
  const [showAddCases, setShowAddCases] = useState(false);
  const [saving, setSaving] = useState(false);
  const isEditing = editingPlanId === activePlanId && activePlanId !== '';

  // Archive
  const [showArchive, setShowArchive] = useState(false);
  const [archivedItems, setArchivedItems] = useState<unknown[]>([]);
  const [archiveLoading, setArchiveLoading] = useState(false);

  // Users
  const [users, setUsers] = useState<{ user_id: string; username: string }[]>([]);
  const [currentUserId, setCurrentUserId] = useState('');

  // Overview
  const [showOverview, setShowOverview] = useState(false);
  const [overviewData, setOverviewData] = useState<Record<string, unknown> | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);

  // Refresh
  const [refreshDetail, setRefreshDetail] = useState(0);

  // Test cases & collections
  const [testCases, setTestCases] = useState<Record<string, { case_id: string; title: string; type: string; priority: string; created_at: string }>>({});
  const [collections, setCollections] = useState<{ collection_id: string; name: string; description?: string | null; case_count: number }[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);

  // Wizard
  const [showWizard, setShowWizard] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [caseSearch, setCaseSearch] = useState('');
  const [submittingPlan, setSubmittingPlan] = useState(false);
  const [newPlan, setNewPlan] = useState<{
    title: string; description: string; startDate: string; endDate: string; triggerAt: string;
    selectedCases: string[]; assignments: Record<string, { assignee: string }>;
  }>({
    title: '', description: '', startDate: '', endDate: '', triggerAt: '',
    selectedCases: [], assignments: {},
  });

  // Result modal
  const [resultModal, setResultModal] = useState<{
    item: PlanItemSummary;
    taskData: unknown;
    timelineData: unknown;
    loading: boolean;
    error?: string;
  } | null>(null);

  // Rerun confirm
  const [rerunConfirm, setRerunConfirm] = useState<PlanItemSummary | null>(null);

  const activePlan = plans.find((p) => p.plan_id === activePlanId);

  // Filtered plans
  const filteredPlans = useMemo(() => {
    return plans.filter((p) => {
      if (searchQuery && !p.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (statusFilter && p.status !== statusFilter) return false;
      return true;
    });
  }, [plans, searchQuery, statusFilter]);

  // Load test cases lazily
  const loadCases = useCallback(async () => {
    if (Object.keys(testCases).length > 0 || casesLoading) return;
    setCasesLoading(true);
    try {
      const [manualRes, autoRes] = await Promise.all([
        api.listTestCases({ limit: 200 }),
        api.listAutomationTestCases({ limit: 200 }),
      ]);
      const map: Record<string, { case_id: string; title: string; type: string; priority: string; created_at: string }> = {};
      for (const tc of manualRes.data || []) {
        map[tc.case_id] = { case_id: tc.case_id, title: tc.title, type: 'manual', priority: tc.priority || 'P3', created_at: tc.created_at || '' };
      }
      for (const atc of autoRes.data || []) {
        map[atc.auto_case_id] = { case_id: atc.auto_case_id, title: atc.name, type: 'auto', priority: 'P3', created_at: atc.created_at || '' };
      }
      setTestCases(map);
    } catch {
      setTestCases({});
    } finally {
      setCasesLoading(false);
    }
  }, [testCases, casesLoading]);

  // Case map
  const caseMap = useMemo(() => new Map(
    Object.values(testCases)
      .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
      .map((tc) => [tc.case_id, { id: tc.case_id, title: tc.title, type: (tc.type === 'auto' ? 'auto' : 'manual') as 'auto' | 'manual', priority: tc.priority }]),
  ), [testCases]);

  // Fetch plans
  const fetchPlans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listPlans();
      setPlans((res.data as unknown as PlanSummary[]) || []);
    } catch {
      setError('获取计划列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch overview
  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const res = await api.getPlanOverview();
      setOverviewData((res.data as Record<string, unknown>) || null);
    } catch {
      setOverviewData(null);
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  // Initialize
  useEffect(() => { void fetchPlans(); }, [fetchPlans]);

  useEffect(() => {
    if (showOverview) fetchOverview();
  }, [showOverview, fetchOverview]);

  useEffect(() => {
    api.listUsers({ limit: 200 })
      .then((res) => {
        setUsers(res.data || []);
        setCurrentUserId(res.data?.[0]?.user_id || '');
      })
      .catch(() => {
        api.getCurrentUser().then((u) => {
          if (u.data) {
            setUsers([u.data]);
            setCurrentUserId(u.data.user_id);
          }
        }).catch(() => setUsers([]));
      });

    api.listCollections()
      .then((res) => setCollections(res.data || []))
      .catch(() => setCollections([]));
  }, []);

  // Fetch plan detail
  useEffect(() => {
    if (!activePlanId) {
      setActivePlanItems([]);
      return;
    }
    setDetailLoading(true);
    api.getPlanDetail(activePlanId)
      .then((res) => {
        const d = res.data as Record<string, unknown> | undefined;
        const items = (d?.items as PlanItemSummary[]) || [];
        setActivePlanItems(items);
        setPlans((prev) => prev.map((p) =>
          p.plan_id === activePlanId ? { ...p, item_count: items.length, done_count: items.filter((i) => i.status === 'done').length } : p,
        ));
      })
      .catch(() => setActivePlanItems([]))
      .finally(() => setDetailLoading(false));
  }, [activePlanId, refreshDetail]);

  return {
    // State
    plans, loading, error, activePlanId, searchQuery, statusFilter,
    activePlanItems, detailLoading, viewMode,
    editingPlanId, editingItems, selectedAddCaseIds, showAddCases, saving, isEditing,
    showArchive, archivedItems, archiveLoading,
    users, currentUserId,
    showOverview, overviewData, overviewLoading,
    refreshDetail,
    testCases, collections, casesLoading,
    showWizard, wizardStep, caseSearch, submittingPlan, newPlan,
    resultModal, rerunConfirm,
    caseMap,
    // Setters
    setActivePlanId, setSearchQuery, setStatusFilter, setViewMode,
    setEditingPlanId, setEditingItems, setSelectedAddCaseIds, setShowAddCases, setSaving,
    setShowArchive, setArchivedItems, setArchiveLoading,
    setShowOverview, setOverviewData,
    setShowWizard, setWizardStep, setCaseSearch, setSubmittingPlan, setNewPlan,
    setResultModal, setRerunConfirm,
    setActivePlanItems, setPlans,
    // Actions
    loadCases, fetchPlans, fetchOverview,
  };
}