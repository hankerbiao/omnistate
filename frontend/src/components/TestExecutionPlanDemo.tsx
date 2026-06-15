/**
 * TestExecutionPlanDemo — 执行计划(demo) 页面
 *
 * 基于前端设计评审重构的 Demo 版本，主要改进:
 * - 左侧计划列表侧栏 + 右侧计划详情区分工
 * - 看板按执行状态分组（待执行/执行中/失败/已完成）
 * - 去除重复的 meta bar
 * - 减少 emoji 依赖，使用 badge + 色彩传递语义
 * - 搜索无结果时显示明确空状态
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { api } from '../services/api';
import type { UserResponse } from '../types';

// ═══════════════════════════════════════════════════════════════════
//  Types
// ═══════════════════════════════════════════════════════════════════

interface PlanSummary {
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

interface PlanItemSummary {
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
}

type ViewMode = 'statusBoard' | 'componentView' | 'listView';

// ═══════════════════════════════════════════════════════════════════
//  Color / label constants (centralised, no emoji)
// ═══════════════════════════════════════════════════════════════════

const STATUS = ['pending', 'running', 'fail', 'done'] as const;
type ItemStatus = (typeof STATUS)[number];

const STATUS_META: Record<ItemStatus, { label: string; color: string; bg: string }> = {
  pending: { label: '待执行', color: '#8b949e', bg: 'rgba(139,148,158,0.08)' },
  running: { label: '执行中', color: '#58a6ff', bg: 'rgba(88,166,255,0.08)' },
  fail:    { label: '失败',   color: '#f85149', bg: 'rgba(248,81,73,0.08)' },
  done:    { label: '已完成', color: '#3fb950', bg: 'rgba(63,185,80,0.08)' },
};

const PLAN_STATUS_META: Record<string, { label: string; color: string }> = {
  active:   { label: '进行中', color: '#3fb950' },
  done:     { label: '已完成', color: '#8b949e' },
};

const PRIORITY_COLORS: Record<string, string> = {
  P0: '#f85149', P1: '#d29922', P2: '#58a6ff', P3: '#8b949e',
};

// ═══════════════════════════════════════════════════════════════════
//  Main component
// ═══════════════════════════════════════════════════════════════════

export default function TestExecutionPlanDemo() {
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

  // ── Archive ──
  const [showArchive, setShowArchive] = useState(false);
  const [archivedItems, setArchivedItems] = useState<any[]>([]);
  const [archiveLoading, setArchiveLoading] = useState(false);

  // ── Users (from real API) ──
  const [users, setUsers] = useState<UserResponse[]>([]);

  // ── Overview ──
  const [showOverview, setShowOverview] = useState(false);
  const [overviewData, setOverviewData] = useState<Record<string, any> | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);

  // ── Test cases & collections (from real API) ──
  const [testCases, setTestCases] = useState<Record<string, { case_id: string; title: string; type: string; priority: string }>>({});
  const [collections, setCollections] = useState<{ collection_id: string; name: string; description?: string | null; case_count: number }[]>([]);

  // Build caseMap from real test cases
  const caseMap = useMemo(() => new Map(
    Object.values(testCases).map(tc => [tc.case_id, {
      id: tc.case_id,
      title: tc.title,
      type: (tc.type === 'auto' ? 'auto' : 'manual') as 'auto' | 'manual',
      priority: tc.priority,
    }]),
  ), [testCases]);

  // ── Wizard ──
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

  const activePlan = plans.find(p => p.plan_id === activePlanId);

  // ── Derived filtered plans ──
  const filteredPlans = useMemo(() => {
    return plans.filter(p => {
      if (searchQuery && !p.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (statusFilter && p.status !== statusFilter) return false;
      return true;
    });
  }, [plans, searchQuery, statusFilter]);

  // ── Fetch plans ──
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

  useEffect(() => { void fetchPlans(); }, [fetchPlans]);

  // ── Fetch overview data ──
  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const res = await api.getPlanOverview();
      setOverviewData((res.data as Record<string, any>) || null);
    } catch {
      setOverviewData(null);
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  useEffect(() => {
    if (showOverview) fetchOverview();
  }, [showOverview, fetchOverview]);

  // ── Fetch users, test cases, and collections ──
  useEffect(() => {
    api.listUsers({ limit: 200 })
      .then(res => setUsers(res.data || []))
      .catch(() => {
        // 权限不足时至少包含当前用户
        api.getCurrentUser().then(u => {
          if (u.data) setUsers([u.data]);
        }).catch(() => setUsers([]));
      });

    const manualPromise = api.listTestCases({ limit: 200 });
    const autoPromise = api.listAutomationTestCases({ limit: 200 });

    Promise.all([manualPromise, autoPromise])
      .then(([manualRes, autoRes]) => {
        const map: Record<string, { case_id: string; title: string; type: string; priority: string }> = {};
        for (const tc of (manualRes.data || [])) {
          map[tc.case_id] = { case_id: tc.case_id, title: tc.title, type: 'manual', priority: tc.priority || 'P3' };
        }
        for (const atc of (autoRes.data || [])) {
          map[atc.auto_case_id] = { case_id: atc.auto_case_id, title: atc.name, type: 'auto', priority: 'P3' };
        }
        setTestCases(map);
      })
      .catch(() => setTestCases({}));

    api.listCollections()
      .then(res => setCollections(res.data || []))
      .catch(() => setCollections([]));
  }, []);

  // ── Fetch plan detail ──
  useEffect(() => {
    if (!activePlanId) {
      setActivePlanItems([]);
      return;
    }
    setDetailLoading(true);
    api.getPlanDetail(activePlanId)
      .then(res => {
        const d = res.data as Record<string, unknown> | undefined;
        setActivePlanItems((d?.items as PlanItemSummary[]) || []);
      })
      .catch(() => setActivePlanItems([]))
      .finally(() => setDetailLoading(false));
  }, [activePlanId]);

  // ── Result viewer ──
  const [resultModal, setResultModal] = useState<{ item: PlanItemSummary; taskData: any; loading: boolean } | null>(null);

  // ══════════════════════════════════════════════════
  //  Actions
  // ══════════════════════════════════════════════════

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
      for (const id of removedIds) {
        await api.deletePlanItem(activePlanId, id);
      }
      const existingCaseIds = new Set(activePlanItems.map(i => i.case_id));
      const newItems = editingItems
        .filter(e => !existingCaseIds.has(e.case_id))
        .map(e => ({
          ref_type: e.ref_type === 'auto' ? 'auto' as const : 'manual' as const,
          case_id: e.case_id,
          assignee_id: e.assignee_id || undefined,
        }));
      if (newItems.length > 0) {
        await api.addPlanItems(activePlanId, { items: newItems });
      }
      // 保存已存在条目的执行人变更
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
      const res = await api.getPlanDetail(activePlanId);
      const d = res.data as Record<string, unknown> | undefined;
      setActivePlanItems((d?.items as PlanItemSummary[]) || []);
    } catch (err) {
      console.error('保存失败:', err);
      // 即使 API 报错，条目可能已部分入库，尝试刷新
      try {
        const res = await api.getPlanDetail(activePlanId);
        const d = res.data as Record<string, unknown> | undefined;
        setActivePlanItems((d?.items as PlanItemSummary[]) || []);
      } catch { /* ignore */ }
      setEditingPlanId('');
      setSelectedAddCaseIds([]);
      setShowAddCases(false);
    } finally {
      setSaving(false);
    }
  }, [activePlanId, activePlanItems, editingItems]);

  const handleAddCaseToggle = useCallback((cid: string) => {
    setSelectedAddCaseIds(prev =>
      prev.includes(cid) ? prev.filter(c => c !== cid) : [...prev, cid],
    );
  }, []);

  // 添加已选用例到编辑列表（立即生效，无需等待"保存更改"）
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
          };
        });
      return [...prev, ...newItems];
    });
    setShowAddCases(false);
    setSelectedAddCaseIds([]);
  }, [selectedAddCaseIds, caseMap]);

  // 编辑模式下更新条目的执行人（本地状态，保存持久化）
  const handleUpdateItemAssignee = useCallback((itemId: string, assigneeId: string) => {
    setEditingItems(prev => prev.map(item =>
      item.item_id === itemId ? { ...item, assignee_id: assigneeId || null } : item
    ));
  }, []);

  const openArchive = useCallback(() => {
    setShowArchive(true);
    setArchiveLoading(true);
    api.listArchivedItems('')
      .then(res => setArchivedItems(res.data || []))
      .catch(() => setArchivedItems([]))
      .finally(() => setArchiveLoading(false));
  }, []);

  const handleUnarchive = useCallback(async (itemId: string) => {
    try {
      await api.unarchiveItem(itemId);
      setArchivedItems(prev => prev.filter((i: any) => i.item_id !== itemId));
    } catch { /* ignore */ }
  }, []);

  // 批量指派执行人
  const handleBatchAssign = useCallback(async (itemIds: string[], assigneeId: string) => {
    if (!activePlanId || itemIds.length === 0) return;
    try {
      await api.batchUpdateAssignee(activePlanId, { item_ids: itemIds, assignee_id: assigneeId });
      // 更新本地状态
      const updateItems = (items: PlanItemSummary[]) => items.map(item =>
        itemIds.includes(item.item_id) ? { ...item, assignee_id: assigneeId } : item
      );
      setEditingItems(updateItems);
      setActivePlanItems(updateItems);
    } catch (err) {
      console.error('批量指派失败:', err);
    }
  }, [activePlanId]);

  // 终止运行任务：删除执行任务 + 重置条目为待执行状态（可重新下发）
  const handleTerminateItem = useCallback(async (planId: string, itemId: string, executionTaskId?: string) => {
    try {
      const executionTaskIdToUse = executionTaskId
        || [...editingItems, ...activePlanItems].find(i => i.item_id === itemId)?.execution_task_id;
      if (executionTaskIdToUse) {
        try { await api.deleteTask(executionTaskIdToUse); } catch { /* ignore */ }
      }
      // 重置为待执行状态，不清除 assignee，可重新下发
      await api.updatePlanItem(planId, itemId, { status: 'pending' });
      if (showOverview) fetchOverview();
      if (activePlanId) {
        const res = await api.getPlanDetail(activePlanId);
        const d = res.data as Record<string, unknown> | undefined;
        setActivePlanItems((d?.items as PlanItemSummary[]) || []);
      }
    } catch (err) {
      console.error('终止失败:', err);
    }
  }, [activePlanId, showOverview, fetchOverview, activePlanItems, editingItems]);

  // 删除计划条目（同时清理关联的执行任务）
  const handleDeleteItem = useCallback(async (planId: string, itemId: string) => {
    try {
      const item = [...editingItems, ...activePlanItems].find(i => i.item_id === itemId);
      if (item?.execution_task_id) {
        try { await api.deleteTask(item.execution_task_id); } catch { /* ignore */ }
      }
      await api.deletePlanItem(planId, itemId);
      if (showOverview) fetchOverview();
      if (activePlanId) {
        const res = await api.getPlanDetail(activePlanId);
        const d = res.data as Record<string, unknown> | undefined;
        setActivePlanItems((d?.items as PlanItemSummary[]) || []);
      }
    } catch (err) {
      console.error('删除失败:', err);
    }
  }, [activePlanId, showOverview, fetchOverview, activePlanItems, editingItems]);

  // 删除整个执行计划
  const handleDeletePlan = useCallback(async (planId: string) => {
    if (!window.confirm('确定要删除该执行计划及其所有条目？此操作不可撤销。')) return;
    try {
      await api.deletePlan(planId);
      setActivePlanId(null);
      setActivePlan(null);
      setActivePlanItems([]);
      fetchOverview();
    } catch (err) {
      console.error('删除计划失败:', err);
    }
  }, [fetchOverview]);

  const handleViewResult = useCallback(async (item: PlanItemSummary) => {
    if (!item.execution_task_id && !item.result) return;
    if (item.execution_task_id) {
      // 自动化任务 — 从 task 状态获取
      setResultModal({ item, taskData: null, loading: true });
      try {
        const res = await api.getTaskStatus(item.execution_task_id);
        setResultModal(prev => prev ? { ...prev, taskData: res.data, loading: false } : null);
      } catch {
        setResultModal(prev => prev ? { ...prev, taskData: { error: true }, loading: false } : null);
      }
    } else {
      // 手工用例 — 直接展示 item.result
      setResultModal({ item, taskData: { manualResult: item.result }, loading: false });
    }
  }, []);

  const resetWizard = () => {
    setWizardStep(1);
    setCaseSearch('');
    setSubmittingPlan(false);
    setNewPlan({ title: '', description: '', startDate: '', endDate: '', triggerAt: '', selectedCases: [], assignments: {} });
  };

  const handleCreatePlan = async () => {
    if (!newPlan.title.trim() || newPlan.selectedCases.length === 0) return;
    setSubmittingPlan(true);
    try {
      const planRes = await api.createPlan({
        title: newPlan.title,
        description: newPlan.description || undefined,
        start_date: newPlan.startDate || undefined,
        end_date: newPlan.endDate || undefined,
        trigger_at: newPlan.triggerAt || undefined,
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
      // 即使 addPlanItems 失败，计划可能已创建，刷新列表
      await fetchPlans();
    } finally {
      setSubmittingPlan(false);
      setShowWizard(false);
      resetWizard();
    }
  };

  // ── Wizard helpers ──
  const toggleSelectCase = (cid: string) => {
    setNewPlan(prev => ({
      ...prev,
      selectedCases: prev.selectedCases.includes(cid)
        ? prev.selectedCases.filter(c => c !== cid)
        : [...prev.selectedCases, cid],
    }));
  };
  const toggleSelectCollection = async (col: { collection_id: string; name: string }) => {
    try {
      const res = await api.getCollection(col.collection_id);
      const data = res.data as any;
      const caseIds = [...(data?.case_ids || []), ...(data?.auto_case_ids || [])];
      if (caseIds.length === 0) return;
      setNewPlan(prev => {
        const allSelected = caseIds.every((cid: string) => prev.selectedCases.includes(cid));
        const ids = new Set(prev.selectedCases);
        for (const cid of caseIds) {
          if (allSelected) ids.delete(cid);
          else ids.add(cid);
        }
        return { ...prev, selectedCases: Array.from(ids) };
      });
    } catch { /* ignore */ }
  };
  const setAssignment = (caseId: string, value: string) => {
    setNewPlan(prev => ({
      ...prev,
      assignments: { ...prev.assignments, [caseId]: { assignee: value } },
    }));
  };

  // ══════════════════════════════════════════════════
  //  Render
  // ══════════════════════════════════════════════════

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* ── Top bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 24px', borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--surface-primary)', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.2px' }}>
            执行计划
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn--ghost btn--sm" onClick={openArchive}
            style={{ fontSize: 12, padding: '6px 12px' }}>
            归档记录{archivedItems.length > 0 ? ` (${archivedItems.length})` : ''}
          </button>
          <button className="btn btn--primary btn--sm"
            onClick={() => { resetWizard(); setShowWizard(true); }}
            style={{ padding: '6px 16px', fontSize: 13 }}>
            + 新建计划
          </button>
        </div>
      </div>

      {/* ── Toolbar: search + status filter ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '10px 24px', borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--surface-primary)', flexShrink: 0,
      }}>
        <input
          className="form-input"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="搜索计划名称..."
          style={{ width: 200, fontSize: 13, padding: '5px 10px' }}
        />
        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { key: '', label: '全部' },
            { key: 'active', label: '进行中' },
            { key: 'done', label: '已完成' },
          ].map(f => (
            <button key={f.key} onClick={() => setStatusFilter(f.key)}
              style={{
                padding: '3px 10px', fontSize: 12, border: 'none', borderRadius: 6, cursor: 'pointer',
                background: statusFilter === f.key ? 'var(--accent-primary)' : 'var(--surface-secondary)',
                color: statusFilter === f.key ? '#fff' : 'var(--text-secondary)',
                fontWeight: statusFilter === f.key ? 600 : 400,
              }}>
              {f.label}
            </button>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        <button
          onClick={() => setShowOverview(v => !v)}
          style={{
            padding: '3px 12px', fontSize: 12, border: 'none', borderRadius: 6, cursor: 'pointer',
            background: showOverview ? 'var(--accent-primary)' : 'var(--surface-secondary)',
            color: showOverview ? '#fff' : 'var(--text-secondary)',
            fontWeight: showOverview ? 600 : 400,
            marginRight: 8,
          }}
        >
          {showOverview ? '计划列表' : '运行总览'}
        </button>
        {error && (
          <div style={{ marginLeft: 'auto', fontSize: 12, color: '#f85149', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>{error}</span>
            <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f85149' }}>x</button>
          </div>
        )}
      </div>

      {/* ── Main split: sidebar + detail, or overview ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {showOverview ? (
          <OverviewView
            data={overviewData}
            loading={overviewLoading}
            onRefresh={fetchOverview}
            onSelectPlan={(planId) => {
              setShowOverview(false);
              setActivePlanId(planId);
            }}
            users={users}
            onViewResult={handleViewResult}
            onDeleteItem={handleTerminateItem}  // 概览中删除 = 终止（删执行任务，保留用例）
          />
        ) : (
          <>
            {/* ── Left: Plan list sidebar ── */}
            <PlanSidebar
          plans={filteredPlans}
          activePlanId={activePlanId}
          loading={loading}
          searchQuery={searchQuery}
          onSelect={setActivePlanId}
        />

        {/* ── Right: Plan detail ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--surface-secondary)' }}>
          {!activePlan ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, color: 'var(--text-tertiary)', padding: 40 }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.4">
                <rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" />
              </svg>
              <span style={{ fontSize: 14 }}>从左侧选择一个计划</span>
              <span style={{ fontSize: 12 }}>或点击「新建计划」创建一个新的执行计划</span>
            </div>
          ) : detailLoading ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
              加载计划详情...
            </div>
          ) : (
            <PlanDetailView
              plan={activePlan}
              items={isEditing ? editingItems : activePlanItems}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              isEditing={isEditing}
              onStartEditing={startEditing}
              onCancelEditing={cancelEditing}
              onSaveEditing={saveEditing}
              onRemoveItem={removeEditingItem}
              saving={saving}
              onShowAddCases={() => setShowAddCases(true)}
              users={users}
              onViewResult={handleViewResult}
              onBatchAssign={handleBatchAssign}
              onTerminateItem={handleTerminateItem}
              onDeleteItem={handleDeleteItem}
              onDeletePlan={handleDeletePlan}
              onUpdateItemAssignee={handleUpdateItemAssignee}
            />
          )}
        </div>
          </>
        )}
      </div>

      {/* ── Modals ── */}
      {showAddCases && (
        <AddCasesModal
          editingItems={editingItems}
          selectedAddCaseIds={selectedAddCaseIds}
          onToggle={handleAddCaseToggle}
          onClose={() => setShowAddCases(false)}
          onConfirm={handleAddSelectedCases}
          cases={Array.from(caseMap.values()).map((tc: any) => ({ id: tc.id, title: tc.title, type: tc.type || 'manual', priority: tc.priority || 'P3' }))}
          users={users}
        />
      )}
      {showWizard && (
        <CreatePlanWizard
          wizardStep={wizardStep}
          onStepChange={setWizardStep}
          newPlan={newPlan}
          onNewPlanChange={setNewPlan}
          caseSearch={caseSearch}
          onCaseSearchChange={setCaseSearch}
          submittingPlan={submittingPlan}
          onCreatePlan={handleCreatePlan}
          onClose={() => setShowWizard(false)}
          onToggleCase={toggleSelectCase}
          onToggleCollection={toggleSelectCollection}
          onSetAssignment={setAssignment}
          users={users}
          collections={collections}
          caseMap={caseMap}
        />
      )}
      <ArchivedModal
        open={showArchive}
        loading={archiveLoading}
        items={archivedItems}
        onClose={() => setShowArchive(false)}
        onUnarchive={handleUnarchive}
      />

      {/* ── Result modal ── */}
      {resultModal && (
        <ResultModal
          item={resultModal.item}
          taskData={resultModal.taskData}
          loading={resultModal.loading}
          onClose={() => setResultModal(null)}
        />
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  PlanSidebar — 左侧计划列表
// ═══════════════════════════════════════════════════════════════════

function PlanSidebar({ plans, activePlanId, loading, searchQuery, onSelect }: {
  plans: PlanSummary[];
  activePlanId: string;
  loading: boolean;
  searchQuery: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div style={{
      width: 280, flexShrink: 0, borderRight: '1px solid var(--border-subtle)',
      background: 'var(--surface-primary)', display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
        计划列表
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: 20, textAlign: 'center', fontSize: 12, color: 'var(--text-tertiary)' }}>加载中...</div>
        ) : plans.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
              {searchQuery ? '没有匹配的计划' : '暂无执行计划'}
            </div>
            {searchQuery && (
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>尝试更换搜索关键词</div>
            )}
          </div>
        ) : (
          plans.map(p => {
            const isActive = p.plan_id === activePlanId;
            const meta = PLAN_STATUS_META[p.status] || { label: p.status, color: '#8b949e' };
            return (
              <div key={p.plan_id} onClick={() => onSelect(p.plan_id)}
                style={{
                  padding: '10px 14px', cursor: 'pointer', borderBottom: '1px solid var(--border-subtle)',
                  background: isActive ? 'color-mix(in srgb, var(--accent-primary) 8%, transparent)' : 'transparent',
                  borderLeft: isActive ? '3px solid var(--accent-primary)' : '3px solid transparent',
                }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{p.title}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                  {p.start_date || '-'} 至 {p.end_date || '-'}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                  <div style={{ flex: 1, height: 3, background: 'var(--surface-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      width: `${p.progress_percent ?? 0}%`, height: '100%',
                      background: p.status === 'active' ? 'var(--accent-primary)' : '#8b949e',
                      borderRadius: 2, transition: 'width 0.3s',
                    }} />
                  </div>
                  <span style={{ fontSize: 10, color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
                    {p.done_count}/{p.item_count}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  PlanDetailView — 右侧计划详情 + 视图切换
// ═══════════════════════════════════════════════════════════════════

function PlanDetailView({ plan, items, viewMode, onViewModeChange, isEditing, onStartEditing, onCancelEditing, onSaveEditing, onRemoveItem, saving, onShowAddCases, users, onViewResult, onBatchAssign, onTerminateItem, onDeleteItem, onDeletePlan, onUpdateItemAssignee }: {
  plan: PlanSummary;
  items: PlanItemSummary[];
  viewMode: ViewMode;
  onViewModeChange: (m: ViewMode) => void;
  isEditing: boolean;
  onStartEditing: () => void;
  onCancelEditing: () => void;
  onSaveEditing: () => void;
  onRemoveItem: (itemId: string) => void;
  saving: boolean;
  onShowAddCases: () => void;
  users: UserResponse[];
  onViewResult?: (item: PlanItemSummary) => void;
  onBatchAssign?: (itemIds: string[], assigneeId: string) => void;
  onTerminateItem?: (planId: string, itemId: string) => void;
  onDeleteItem?: (planId: string, itemId: string) => void;
  onUpdateItemAssignee?: (itemId: string, assigneeId: string) => void;
}) {
  const meta = PLAN_STATUS_META[plan.status] || { label: plan.status, color: '#8b949e' };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '16px 20px' }}>
      {/* Plan header — 单一来源，不再在子视图中重复 */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '10px 16px', background: 'var(--surface-primary)',
        borderRadius: 8, border: '1px solid var(--border-subtle)',
        flexShrink: 0, marginBottom: 12,
      }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>{plan.title}</span>
        <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: `${meta.color}18`, color: meta.color, fontWeight: 600 }}>
          {meta.label}
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
          {plan.start_date || '-'} 至 {plan.end_date || '-'}
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
          进度 {plan.progress_percent ?? 0}% ({plan.done_count}/{plan.item_count})
        </span>
        <div style={{ width: 60, height: 3, background: 'var(--surface-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${plan.progress_percent ?? 0}%`, height: '100%', background: plan.status === 'active' ? 'var(--accent-primary)' : '#8b949e', borderRadius: 2 }} />
        </div>
        <div style={{ flex: 1 }} />
        {isEditing ? (
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn btn--ghost btn--sm" onClick={onCancelEditing} disabled={saving} style={{ fontSize: 12 }}>取消</button>
            <button className="btn btn--primary btn--sm" onClick={() => onSaveEditing()} disabled={saving} style={{ fontSize: 12 }}>
              {saving ? '保存中...' : '保存更改'}
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn btn--ghost btn--sm" onClick={onStartEditing} style={{ fontSize: 12 }}>编辑</button>
            <button className="btn btn--ghost btn--sm" onClick={() => onDeletePlan(plan.plan_id)} style={{ fontSize: 12, color: '#f85149' }}>删除</button>
          </div>
        )}
      </div>

      {/* View switcher + add cases (edit mode) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 10, flexShrink: 0 }}>
        {([
          { key: 'statusBoard' as ViewMode, label: '状态看板' },
          { key: 'listView' as ViewMode, label: '列表' },
        ]).map(v => (
          <button key={v.key} onClick={() => onViewModeChange(v.key)}
            style={{
              padding: '4px 12px', fontSize: 12, border: '1px solid var(--border-subtle)', borderRadius: 6, cursor: 'pointer',
              background: viewMode === v.key ? 'var(--accent-primary)' : 'var(--surface-primary)',
              color: viewMode === v.key ? '#fff' : 'var(--text-secondary)',
              fontWeight: viewMode === v.key ? 600 : 400,
            }}>
            {v.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        {isEditing && (
          <button className="btn btn--ghost btn--sm" onClick={onShowAddCases} style={{ fontSize: 12 }}>
            + 添加用例
          </button>
        )}
      </div>

      {/* View content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {items.length === 0 ? (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', gap: 6 }}>
            <span style={{ fontSize: 13 }}>该计划暂无条目</span>
            {isEditing && (
              <button className="btn btn--ghost btn--sm" onClick={onShowAddCases} style={{ fontSize: 12 }}>添加用例</button>
            )}
          </div>
        ) : viewMode === 'statusBoard' ? (
          <StatusBoard items={items} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} onTerminateItem={onTerminateItem} onDeleteItem={onDeleteItem} onUpdateItemAssignee={onUpdateItemAssignee} />
        ) : viewMode === 'componentView' ? (
          <ComponentBoard items={items} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} />
        ) : (
          <DataTable items={items} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} onBatchAssign={onBatchAssign} onTerminateItem={onTerminateItem} onDeleteItem={onDeleteItem} onUpdateItemAssignee={onUpdateItemAssignee} />
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  StatusBoard — 按执行状态分栏看板
// ═══════════════════════════════════════════════════════════════════

function StatusBoard({ items, isEditing, onRemoveItem, users, onViewResult, onTerminateItem, onDeleteItem, onUpdateItemAssignee }: {
  items: PlanItemSummary[];
  isEditing?: boolean;
  onRemoveItem?: (itemId: string) => void;
  users: UserResponse[];
  onViewResult?: (item: PlanItemSummary) => void;
  onTerminateItem?: (planId: string, itemId: string) => void;
  onDeleteItem?: (planId: string, itemId: string) => void;
  onUpdateItemAssignee?: (itemId: string, assigneeId: string) => void;
}) {
  const groups = useMemo(() => {
    const map = new Map<string, PlanItemSummary[]>();
    for (const s of STATUS) map.set(s, []);
    for (const item of items) {
      const key = STATUS.includes(item.status as ItemStatus) ? item.status : 'pending';
      map.get(key)!.push(item);
    }
    return Array.from(map.entries());
  }, [items]);

  return (
    <div style={{ height: '100%', display: 'flex', gap: 10, overflow: 'auto' }}>
      {groups.map(([status, caseItems]) => {
        const meta = STATUS_META[status as ItemStatus] || { label: status, color: '#8b949e', bg: 'rgba(0,0,0,0.04)' };
        return (
          <div key={status} style={{ flex: 1, minWidth: 200, display: 'flex', flexDirection: 'column' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 10px', marginBottom: 6, borderRadius: 6,
              background: meta.bg,
            }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: meta.color }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: meta.color }}>{meta.label}</span>
              <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginLeft: 'auto' }}>{caseItems.length}</span>
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4, overflowY: 'auto' }}>
              {caseItems.length === 0 && (
                <div style={{ padding: 12, textAlign: 'center', fontSize: 11, color: 'var(--text-tertiary)', border: '1px dashed var(--border-subtle)', borderRadius: 8 }}>-</div>
              )}
              {caseItems.map(item => (
                <StatusCard key={item.item_id} item={item} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} onTerminateItem={onTerminateItem} onDeleteItem={onDeleteItem} onUpdateItemAssignee={onUpdateItemAssignee} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StatusCard({ item, isEditing, onRemoveItem, users, onViewResult, onTerminateItem, onDeleteItem, onUpdateItemAssignee }: {
  item: PlanItemSummary;
  isEditing?: boolean;
  onRemoveItem?: (itemId: string) => void;
  users: UserResponse[];
  onViewResult?: (item: PlanItemSummary) => void;
  onTerminateItem?: (planId: string, itemId: string) => void;
  onDeleteItem?: (planId: string, itemId: string) => void;
  onUpdateItemAssignee?: (itemId: string, assigneeId: string) => void;
}) {
  const meta = STATUS_META[item.status as ItemStatus] || STATUS_META.pending;
  const isAuto = item.ref_type === 'auto';
  const [showAssigneePicker, setShowAssigneePicker] = useState(false);
  return (
    <div style={{
      padding: '8px 10px', borderRadius: 6, background: 'var(--surface-primary)',
      border: `1px solid ${meta.color}20`, borderLeft: `3px solid ${meta.color}`,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
        <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{item.case_id}</span>
        {isEditing && onRemoveItem && (
          <span onClick={(e) => { e.stopPropagation(); onRemoveItem(item.item_id); }}
            style={{ fontSize: 12, cursor: 'pointer', color: 'var(--text-tertiary)', opacity: 0.4 }}>x</span>
        )}
      </div>
      <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, lineHeight: 1.4 }}>{item.case_title}</div>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
        <span style={{
          fontSize: 9, padding: '1px 5px', borderRadius: 3,
          background: isAuto ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)',
          color: isAuto ? '#39d0d6' : '#a371f7', fontWeight: 600,
        }}>
          {isAuto ? 'AUTO' : 'MANUAL'}
        </span>
        <span style={{ fontSize: 9, color: PRIORITY_COLORS[item.priority] || '#8b949e', fontWeight: 600 }}>{item.priority}</span>
        {isEditing && onUpdateItemAssignee ? (
          showAssigneePicker ? (
            <select
              className="form-input form-select"
              value={item.assignee_id || ''}
              onChange={e => { onUpdateItemAssignee(item.item_id, e.target.value); setShowAssigneePicker(false); }}
              style={{ fontSize: 9, width: 120 }}
              autoFocus
            >
              <option value="">未指派</option>
              {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
            </select>
          ) : (
            <span onClick={() => setShowAssigneePicker(true)}
              style={{ fontSize: 9, color: 'var(--accent-primary)', cursor: 'pointer', textDecoration: 'underline dotted' }}>
              {item.assignee_id ? (users.find(u => u.user_id === item.assignee_id)?.username || item.assignee_id) : '+ 指派'}
            </span>
          )
        ) : (
          item.assignee_id && (
            <span style={{ fontSize: 9, color: 'var(--text-tertiary)' }}>
              {users.find(u => u.user_id === item.assignee_id)?.username || item.assignee_id}
            </span>
          )
        )}
        {item.result && (
          <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3,
            color: item.result.passed ? '#3fb950' : '#f85149',
            background: item.result.passed ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)',
            fontWeight: 600, marginLeft: item.execution_task_id ? 0 : 'auto',
          }}>
            {item.result.passed ? '通过' : '失败'}
          </span>
        )}
        {(item.execution_task_id || item.result) && onViewResult && (
          <button type="button" onClick={(e) => { e.stopPropagation(); onViewResult(item); }}
            style={{
              fontSize: 9, padding: '1px 6px', borderRadius: 4, border: '1px solid var(--border-subtle)',
              background: 'var(--surface-secondary)', color: 'var(--accent-primary)', cursor: 'pointer',
              marginLeft: 'auto',
            }}>
            结果
          </button>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  ComponentBoard — 按组件分栏（原名"看板"）
// ═══════════════════════════════════════════════════════════════════

function ComponentBoard({ items, isEditing, onRemoveItem, users, onViewResult }: {
  items: PlanItemSummary[];
  isEditing?: boolean;
  onRemoveItem?: (itemId: string) => void;
  users: UserResponse[];
  onViewResult?: (item: PlanItemSummary) => void;
}) {
  const groups = useMemo(() => {
    const map = new Map<string, PlanItemSummary[]>();
    for (const item of items) {
      const comp = item.component || 'other';
      if (!map.has(comp)) map.set(comp, []);
      map.get(comp)!.push(item);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [items]);

  const compName = (id: string) => id;

  return (
    <div style={{ height: '100%', display: 'flex', gap: 10, overflow: 'auto' }}>
      {groups.map(([compId, caseItems]) => (
        <div key={compId} style={{ minWidth: 240, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', marginBottom: 6, fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
            <span>{compName(compId)}</span>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginLeft: 'auto' }}>{caseItems.length}</span>
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4, overflowY: 'auto' }}>
            {caseItems.map(item => (
              <StatusCard key={item.item_id} item={item} isEditing={isEditing} onRemoveItem={onRemoveItem} users={users} onViewResult={onViewResult} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  DataTable — 表格视图（支持批量指派执行人）
// ═══════════════════════════════════════════════════════════════════

function DataTable({ items, isEditing, onRemoveItem, users, onViewResult, onBatchAssign, onTerminateItem, onDeleteItem, onUpdateItemAssignee }: {
  items: PlanItemSummary[];
  isEditing?: boolean;
  onRemoveItem?: (itemId: string) => void;
  users: UserResponse[];
  onViewResult?: (item: PlanItemSummary) => void;
  onBatchAssign?: (itemIds: string[], assigneeId: string) => void;
  onTerminateItem?: (planId: string, itemId: string) => void;
  onDeleteItem?: (planId: string, itemId: string) => void;
  onUpdateItemAssignee?: (itemId: string, assigneeId: string) => void;
}) {
  const compName = (id: string) => id;
  const [selectedItemIds, setSelectedItemIds] = useState<Set<string>>(new Set());
  const [batchAssigneeId, setBatchAssigneeId] = useState<string>('');

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedItemIds.size === items.length) {
      setSelectedItemIds(new Set());
    } else {
      setSelectedItemIds(new Set(items.map(i => i.item_id)));
    }
  };

  // 选择单个条目
  const handleSelectItem = (itemId: string) => {
    const newSet = new Set(selectedItemIds);
    if (newSet.has(itemId)) {
      newSet.delete(itemId);
    } else {
      newSet.add(itemId);
    }
    setSelectedItemIds(newSet);
  };

  // 批量指派
  const handleBatchAssign = () => {
    if (onBatchAssign && selectedItemIds.size > 0 && batchAssigneeId) {
      onBatchAssign(Array.from(selectedItemIds), batchAssigneeId);
      setSelectedItemIds(new Set());
      setBatchAssigneeId('');
    }
  };

  // 清除没有执行人的条目选择
  const selectUnassigned = () => {
    const unassignedIds = items.filter(i => !i.assignee_id).map(i => i.item_id);
    setSelectedItemIds(new Set(unassignedIds));
  };

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      {/* 批量操作栏 */}
      {isEditing && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '8px 12px', marginBottom: 8,
          background: 'var(--surface-primary)', borderRadius: 6,
          border: '1px solid var(--border-subtle)',
        }}>
          <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
            已选 {selectedItemIds.size} 条
          </span>
          <button
            onClick={selectUnassigned}
            style={{
              fontSize: 11, padding: '2px 8px', borderRadius: 4,
              border: '1px solid var(--border-subtle)', background: 'transparent',
              color: 'var(--text-secondary)', cursor: 'pointer',
            }}
          >
            选中无执行人
          </button>
          <select
            className="form-input form-select"
            value={batchAssigneeId}
            onChange={e => setBatchAssigneeId(e.target.value)}
            style={{ width: 140, fontSize: 11 }}
          >
            <option value="">选择执行人</option>
            {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
          </select>
          <button
            onClick={handleBatchAssign}
            disabled={selectedItemIds.size === 0 || !batchAssigneeId}
            style={{
              fontSize: 11, padding: '2px 12px', borderRadius: 4,
              border: 'none', background: selectedItemIds.size > 0 && batchAssigneeId ? 'var(--accent-primary)' : 'var(--surface-tertiary)',
              color: selectedItemIds.size > 0 && batchAssigneeId ? '#fff' : 'var(--text-tertiary)',
              cursor: selectedItemIds.size > 0 && batchAssigneeId ? 'pointer' : 'not-allowed',
            }}
          >
            指派
          </button>
          {selectedItemIds.size > 0 && (
            <button
              onClick={() => setSelectedItemIds(new Set())}
              style={{
                fontSize: 11, padding: '2px 8px', borderRadius: 4,
                border: 'none', background: 'transparent',
                color: 'var(--text-tertiary)', cursor: 'pointer',
              }}
            >
              清除选择
            </button>
          )}
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: 'var(--surface-primary)', position: 'sticky', top: 0, zIndex: 1 }}>
            {isEditing && (
              <th style={{ padding: '8px 12px', textAlign: 'center', width: 40, borderBottom: '1px solid var(--border-subtle)' }}>
                <input
                  type="checkbox"
                  checked={items.length > 0 && selectedItemIds.size === items.length}
                  onChange={handleSelectAll}
                  style={{ cursor: 'pointer' }}
                />
              </th>
            )}
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>用例</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>类型</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>组件</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>优先级</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>执行人</th>
            <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>状态</th>
            <th style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>结果</th>
            {isEditing && <th style={{ padding: '8px 12px', textAlign: 'center', width: 30, borderBottom: '1px solid var(--border-subtle)' }}></th>}
          </tr>
        </thead>
        <tbody>
          {items.map(item => {
            const statusMeta = STATUS_META[item.status as ItemStatus] || STATUS_META.pending;
            const isSelected = selectedItemIds.has(item.item_id);
            return (
              <tr key={item.item_id} style={{
                borderBottom: '1px solid var(--border-subtle)',
                background: isSelected ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'transparent',
              }}>
                {isEditing && (
                  <td style={{ padding: '7px 12px', textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleSelectItem(item.item_id)}
                      style={{ cursor: 'pointer' }}
                    />
                  </td>
                )}
                <td style={{ padding: '7px 12px' }}>
                  <div style={{ fontWeight: 500 }}>{item.case_title}</div>
                  <div style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{item.case_id}</div>
                </td>
                <td style={{ padding: '7px 12px' }}>
                  <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4,
                    background: item.ref_type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)',
                    color: item.ref_type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                  }}>{item.ref_type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                </td>
                <td style={{ padding: '7px 12px', color: 'var(--text-secondary)' }}>{compName(item.component)}</td>
                <td style={{ padding: '7px 12px', color: PRIORITY_COLORS[item.priority] || '#8b949e', fontWeight: 600 }}>{item.priority}</td>
                <td style={{ padding: '7px 12px', color: 'var(--text-secondary)' }}>
                  {isEditing && onUpdateItemAssignee ? (
                    <select
                      className="form-input form-select"
                      value={item.assignee_id || ''}
                      onChange={e => onUpdateItemAssignee(item.item_id, e.target.value)}
                      style={{ fontSize: 11, width: 110 }}
                      onClick={e => e.stopPropagation()}
                    >
                      <option value="">未指派</option>
                      {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                    </select>
                  ) : item.assignee_id ? (
                    users.find(u => u.user_id === item.assignee_id)?.username || item.assignee_id
                  ) : (
                    <span style={{ color: 'var(--status-warn)', fontSize: 10 }}>未指派</span>
                  )}
                </td>
                <td style={{ padding: '7px 12px' }}>
                  <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6,
                    background: `${statusMeta.color}15`, color: statusMeta.color, fontWeight: 600,
                  }}>{statusMeta.label}</span>
                </td>
                <td style={{ padding: '7px 12px', textAlign: 'center' }}>
                  {item.result && (
                    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3,
                      color: item.result.passed ? '#3fb950' : '#f85149',
                      background: item.result.passed ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)',
                      fontWeight: 600, marginRight: 6,
                    }}>
                      {item.result.passed ? '通过' : '失败'}
                    </span>
                  )}
                  {(item.execution_task_id || item.result) && onViewResult ? (
                    <button type="button" onClick={(e) => { e.stopPropagation(); onViewResult(item); }}
                      style={{ fontSize: 10, padding: '2px 10px', borderRadius: 4, border: '1px solid var(--border-subtle)',
                        background: 'var(--surface-secondary)', color: 'var(--accent-primary)', cursor: 'pointer' }}>
                      详情
                    </button>
                  ) : (
                    <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>-</span>
                  )}
                </td>
                {isEditing && onRemoveItem && (
                  <td style={{ padding: '7px 12px', textAlign: 'center' }}>
                    <span onClick={() => onRemoveItem(item.item_id)}
                      style={{ fontSize: 12, cursor: 'pointer', color: 'var(--text-tertiary)', opacity: 0.4 }}>x</span>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  AddCasesModal — 编辑模式下添加用例
// ═══════════════════════════════════════════════════════════════════

function AddCasesModal({ editingItems, selectedAddCaseIds, onToggle, onClose, onConfirm, cases, users }: {
  editingItems: PlanItemSummary[];
  selectedAddCaseIds: string[];
  onToggle: (cid: string) => void;
  onClose: () => void;
  onConfirm: (assigneeId: string) => void;
  cases: { id: string; title: string; type: string; priority: string }[];
  users: UserResponse[];
}) {
  const [step, setStep] = useState<1 | 2>(1);
  const [assigneeId, setAssigneeId] = useState('');
  const editingCaseIds = useMemo(() => new Set(editingItems.map(e => e.case_id)), [editingItems]);

  // 进入第二步：指派执行人
  const goToAssignStep = () => {
    if (selectedAddCaseIds.length > 0) {
      setStep(2);
    }
  };

  // 返回第一步
  const goBack = () => {
    setStep(1);
  };

  // 确认添加
  const handleConfirm = () => {
    if (assigneeId && selectedAddCaseIds.length > 0) {
      onConfirm(assigneeId);
      setStep(1);
      setAssigneeId('');
    }
  };

  // 关闭时重置状态
  const handleClose = () => {
    setStep(1);
    setAssigneeId('');
    onClose();
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-elevated)', borderRadius: 12, width: 520, maxWidth: '94vw',
        maxHeight: '70vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 25px 60px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)',
      }}>
        {/* Header */}
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>
              {step === 1 ? '添加测试用例' : '指派执行人'}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{
                fontSize: 10, padding: '2px 8px', borderRadius: 8,
                background: step === 1 ? 'var(--accent-primary)' : 'rgba(63,185,80,0.12)',
                color: step === 1 ? '#fff' : '#3fb950',
                fontWeight: 600,
              }}>1. 选用例</span>
              <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>→</span>
              <span style={{
                fontSize: 10, padding: '2px 8px', borderRadius: 8,
                background: step === 2 ? 'var(--accent-primary)' : 'var(--surface-tertiary)',
                color: step === 2 ? '#fff' : 'var(--text-tertiary)',
                fontWeight: step === 2 ? 600 : 400,
              }}>2. 指派</span>
            </div>
          </div>
          <button onClick={handleClose} style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>x</button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '10px 18px' }}>
          {step === 1 ? (
            // 第一步：选择用例
            <>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 12 }}>
                已选择 <strong style={{ color: 'var(--accent-primary)' }}>{selectedAddCaseIds.length}</strong> 个用例
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {cases.map(tc => {
                  const alreadyInPlan = editingCaseIds.has(tc.id);
                  const selected = selectedAddCaseIds.includes(tc.id);
                  return (
                    <label key={tc.id} onClick={() => { if (!alreadyInPlan) onToggle(tc.id); }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', borderRadius: 6,
                        cursor: alreadyInPlan ? 'not-allowed' : 'pointer', opacity: alreadyInPlan ? 0.5 : 1,
                        border: selected ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                        background: selected ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'var(--bg-primary)',
                      }}>
                      <input type="checkbox" checked={selected || alreadyInPlan} disabled={alreadyInPlan} onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                      <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 50 }}>{tc.id}</span>
                      <span style={{ flex: 1, fontSize: 12 }}>{tc.title}</span>
                      <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3,
                        background: tc.type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)',
                        color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                      }}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                      {alreadyInPlan && <span style={{ fontSize: 9, color: 'var(--text-tertiary)' }}>已在计划中</span>}
                    </label>
                  );
                })}
              </div>
            </>
          ) : (
            // 第二步：指派执行人
            <>
              <div style={{
                background: 'var(--surface-primary)', borderRadius: 8, padding: '12px 14px',
                marginBottom: 16, border: '1px solid var(--border-subtle)',
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 6 }}>即将添加的用例</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {selectedAddCaseIds.length} 个用例
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
                  请为这些用例指定执行人
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 8 }}>
                  选择执行人 <span style={{ color: 'var(--status-error)' }}>*</span>
                </label>
                <select
                  className="form-input form-select"
                  value={assigneeId}
                  onChange={e => setAssigneeId(e.target.value)}
                  style={{ width: '100%', fontSize: 13, padding: '8px 12px' }}
                >
                  <option value="">请选择执行人</option>
                  {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                </select>
                {!assigneeId && (
                  <div style={{ fontSize: 11, color: 'var(--status-warn)', marginTop: 6 }}>
                    必须指定执行人才能添加用例
                  </div>
                )}
              </div>

              {/* 预览已选用的例 */}
              <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 6 }}>
                {cases.filter(tc => selectedAddCaseIds.includes(tc.id)).map(tc => (
                  <div key={tc.id} style={{
                    display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
                    borderBottom: '1px solid var(--border-subtle)',
                    fontSize: 11,
                  }}>
                    <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 50 }}>{tc.id}</span>
                    <span style={{ flex: 1 }}>{tc.title}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 4px', borderRadius: 3,
                      background: tc.type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)',
                      color: tc.type === 'auto' ? '#39d0d6' : '#a371f7',
                    }}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '10px 18px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
          {step === 1 ? (
            <>
              <button className="btn btn--ghost btn--sm" onClick={handleClose} style={{ fontSize: 12 }}>取消</button>
              <button
                className="btn btn--primary btn--sm"
                onClick={goToAssignStep}
                disabled={selectedAddCaseIds.length === 0}
                style={{ fontSize: 12 }}
              >
                下一步：指派执行人 →
              </button>
            </>
          ) : (
            <>
              <button className="btn btn--ghost btn--sm" onClick={goBack} style={{ fontSize: 12 }}>← 返回</button>
              <button
                className="btn btn--primary btn--sm"
                onClick={handleConfirm}
                disabled={!assigneeId}
                style={{ fontSize: 12 }}
              >
                确认添加 ({selectedAddCaseIds.length} 个)
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  CreatePlanWizard — 新建计划向导
// ═══════════════════════════════════════════════════════════════════

function CreatePlanWizard({ wizardStep, onStepChange, newPlan, onNewPlanChange, caseSearch, onCaseSearchChange, submittingPlan, onCreatePlan, onClose, onToggleCase, onToggleCollection, onSetAssignment, users, collections, caseMap }: {
  wizardStep: number; onStepChange: (s: number) => void;
  newPlan: any; onNewPlanChange: (p: any) => void;
  caseSearch: string; onCaseSearchChange: (s: string) => void;
  submittingPlan: boolean; onCreatePlan: () => void; onClose: () => void;
  onToggleCase: (cid: string) => void; onToggleCollection: (col: any) => void;
  onSetAssignment: (caseId: string, value: string) => void;
  users: UserResponse[]; collections: any[]; caseMap: Map<string, any>;
}) {
  const stepLabels = ['基本信息', '选择用例', '分配执行人', '排期确认'];
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-elevated)', borderRadius: 12, width: 680, maxWidth: '94vw',
        maxHeight: '88vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 25px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)',
      }}>
        {/* Header */}
        <div style={{ padding: '16px 22px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>新建执行计划</div>
            <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
              {stepLabels.map((s, i) => (
                <span key={i} style={{
                  fontSize: 11, padding: '2px 10px', borderRadius: 8,
                  background: wizardStep === i + 1 ? 'var(--accent-primary)' : wizardStep > i + 1 ? 'rgba(63,185,80,0.12)' : 'var(--surface-tertiary)',
                  color: wizardStep === i + 1 ? '#fff' : wizardStep > i + 1 ? '#3fb950' : 'var(--text-tertiary)',
                  fontWeight: wizardStep === i + 1 ? 600 : 400,
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  {wizardStep > i + 1 ? <span style={{ fontSize: 10 }}>v</span> : <span>{i + 1}</span>}
                  <span>{s}</span>
                </span>
              ))}
            </div>
          </div>
          <button onClick={onClose} style={{ fontSize: 22, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>x</button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '18px 22px' }}>
          {wizardStep === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>计划名称 *</label>
                <input className="form-input" value={newPlan.title} onChange={e => onNewPlanChange((p: any) => ({ ...p, title: e.target.value }))}
                  placeholder="例如: Sprint 3 安全回归" style={{ width: '100%' }} autoFocus />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>描述</label>
                <textarea className="form-input" value={newPlan.description} onChange={e => onNewPlanChange((p: any) => ({ ...p, description: e.target.value }))}
                  placeholder="计划的目的、范围、备注..." rows={3} style={{ width: '100%', resize: 'vertical' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>计划周期</label>
                <DateRangePicker
                  startDate={newPlan.startDate}
                  endDate={newPlan.endDate}
                  onChange={(start, end) => onNewPlanChange((p: any) => ({ ...p, startDate: start, endDate: end }))}
                />
              </div>
            </div>
          )}

          {wizardStep === 2 && (
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                已选 <strong>{newPlan.selectedCases.length}</strong> 个用例
              </div>
              <input className="form-input" value={caseSearch} onChange={e => onCaseSearchChange(e.target.value)}
                placeholder="搜索用例名称、ID 或预置用例集..." style={{ width: '100%', fontSize: 12, padding: '6px 10px', marginBottom: 10, boxSizing: 'border-box' }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {(() => {
                  const q = caseSearch.trim().toLowerCase();
                  const matchedCollections = q
                    ? collections.filter((col: any) => col.name?.toLowerCase().includes(q) || (col.description || '').toLowerCase().includes(q))
                    : collections;
                  const allCases = Array.from(caseMap.values());
                  const matchedCases = q ? allCases.filter((tc: any) => tc.id.includes(q) || tc.title.toLowerCase().includes(q)) : allCases;
                  return (
                    <>
                      {matchedCollections.map((col: any) => {
                        return (
                          <label key={col.collection_id} onClick={() => onToggleCollection(col)}
                            style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 6, cursor: 'pointer',
                              border: '1px solid var(--border-subtle)',
                              background: 'var(--bg-primary)',
                              marginBottom: 2,
                            }}>
                            <div style={{ flex: 1 }}>
                              <div style={{ fontSize: 12, fontWeight: 500 }}>{col.name}</div>
                              {col.description && <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 1 }}>{col.description}</div>}
                            </div>
                            <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>{(col.case_count || 0) + (col.auto_case_count || 0)} 个用例</span>
                          </label>
                        );
                      })}
                      {matchedCases.map((tc: any) => {
                        const sel = newPlan.selectedCases.includes(tc.id);
                        return (
                          <label key={tc.id} onClick={() => onToggleCase(tc.id)}
                            style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 6, cursor: 'pointer',
                              border: sel ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                              background: sel ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--bg-primary)',
                            }}>
                            <input type="checkbox" checked={sel} onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                            <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 50 }}>{tc.id}</span>
                            <span style={{ flex: 1, fontSize: 12, fontWeight: sel ? 600 : 400 }}>{tc.title}</span>
                            <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4,
                              background: tc.type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)',
                              color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                            }}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                            {tc.priority && <span style={{ fontSize: 10, color: PRIORITY_COLORS[tc.priority] || '#8b949e', fontWeight: 600 }}>{tc.priority}</span>}
                          </label>
                        );
                      })}
                      {matchedCollections.length === 0 && matchedCases.length === 0 && (
                        <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>无匹配的用例或集合</div>
                      )}
                    </>
                  );
                })()}
              </div>
            </div>
          )}

          {wizardStep === 3 && (
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                为已选用例分配执行人
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {newPlan.selectedCases.map((cid: string) => {
                  const tc = caseMap.get(cid);
                  if (!tc) return null;
                  return (
                    <div key={cid} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 50 }}>{cid}</span>
                      <span style={{ flex: 1, fontSize: 12, fontWeight: 500 }}>{tc.title}</span>
                      <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4,
                        background: tc.type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)',
                        color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                      }}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                      <select className="form-input form-select" style={{ width: 120, fontSize: 11 }}
                        value={newPlan.assignments[cid]?.assignee || ''}
                        onChange={e => onSetAssignment(cid, e.target.value)}>
                        <option value="">执行人</option>
                        {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                      </select>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {wizardStep === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>自动触发时间</label>
                <input type="datetime-local" className="form-input" value={newPlan.triggerAt}
                  onChange={e => onNewPlanChange((p: any) => ({ ...p, triggerAt: e.target.value }))} style={{ width: 260 }} />
                <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 4 }}>到达设定时间后自动开始执行，留空为手动触发</div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', borderRadius: 8, padding: 14, border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>计划概览</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 14px', fontSize: 12 }}>
                  <span style={{ color: 'var(--text-tertiary)' }}>名称</span><span style={{ fontWeight: 500 }}>{newPlan.title || '-'}</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>周期</span><span>{newPlan.startDate || '-'} 至 {newPlan.endDate || '-'}</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>触发方式</span><span>{newPlan.triggerAt || '手动触发'}</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>用例数</span><span style={{ fontWeight: 600 }}>{newPlan.selectedCases.length} 个（{newPlan.selectedCases.filter((c: string) => caseMap.get(c)?.type === 'auto').length} 自动 / {newPlan.selectedCases.filter((c: string) => caseMap.get(c)?.type === 'manual').length} 手动）</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 22px', borderTop: '1px solid var(--border-subtle)' }}>
          <button className="btn btn--secondary btn--sm" onClick={() => wizardStep > 1 ? onStepChange(wizardStep - 1) : onClose()} style={{ fontSize: 12 }}>
            {wizardStep > 1 ? '上一步' : '取消'}
          </button>
          {wizardStep < 4 ? (
            <button className="btn btn--primary btn--sm" onClick={() => onStepChange(wizardStep + 1)} disabled={wizardStep === 1 && !newPlan.title.trim()} style={{ fontSize: 12 }}>
              下一步
            </button>
          ) : (
            <button className="btn btn--primary btn--sm" onClick={onCreatePlan}
              disabled={newPlan.selectedCases.length === 0 || submittingPlan} style={{ fontSize: 12 }}>
              {submittingPlan ? '创建中...' : '创建计划'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  DateRangePicker
// ═══════════════════════════════════════════════════════════════════

function DateRangePicker({ startDate, endDate, onChange }: {
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
}) {
  const parseDate = (s: string) => s ? new Date(s + 'T00:00:00') : null;
  const fmtDate = (d: Date | null) => d ? d.toISOString().slice(0, 10) : '';
  const [start, setStart] = useState<Date | null>(parseDate(startDate));
  const [end, setEnd] = useState<Date | null>(parseDate(endDate));
  const handleChange = (dates: [Date | null, Date | null]) => {
    const [s, e] = dates;
    setStart(s);
    setEnd(e);
    onChange(fmtDate(s), fmtDate(e));
  };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <DatePicker selected={start} onChange={handleChange} startDate={start} endDate={end}
        selectsRange inline monthsShown={1} dateFormat="yyyy-MM-dd"
        calendarClassName="compact-datepicker"
        dayClassName={d => {
          const ds = fmtDate(d);
          if (startDate && endDate && ds >= startDate && ds <= endDate) return 'rdp-in-range';
          if (ds === startDate || ds === endDate) return 'rdp-selected';
          return '';
        }}
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
        <span style={{ fontWeight: 500, color: start ? 'var(--accent-primary)' : 'var(--text-tertiary)' }}>{startDate || '未选'}</span>
        <span style={{ color: 'var(--text-tertiary)' }}>至</span>
        <span style={{ fontWeight: 500, color: end ? 'var(--accent-primary)' : 'var(--text-tertiary)' }}>{endDate || '未选'}</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 3 }}>
          {[
            { label: '清除', fn: () => { setStart(null); setEnd(null); onChange('', ''); } },
            { label: '今天', fn: () => { const t = new Date(); setStart(t); setEnd(new Date(t)); onChange(fmtDate(t), fmtDate(t)); } },
            { label: '7 天', fn: () => { const t = new Date(); const n = new Date(t); n.setDate(t.getDate() + 7); setStart(t); setEnd(n); onChange(fmtDate(t), fmtDate(n)); } },
            { label: '30 天', fn: () => { const t = new Date(); const n = new Date(t); n.setDate(t.getDate() + 30); setStart(t); setEnd(n); onChange(fmtDate(t), fmtDate(n)); } },
          ].map(b => (
            <button key={b.label} className="btn btn--ghost btn--sm" onClick={b.fn}
              style={{ fontSize: 9, padding: '2px 6px', lineHeight: 1.5 }}>{b.label}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  ArchivedModal — 已归档条目
// ═══════════════════════════════════════════════════════════════════

function ArchivedModal({ open, loading, items, onClose, onUnarchive }: {
  open: boolean; loading: boolean; items: any[]; onClose: () => void; onUnarchive: (itemId: string) => void;
}) {
  if (!open) return null;
  const doneCount = items.filter((i: any) => i.status === 'done').length;
  const failCount = items.filter((i: any) => i.status === 'fail').length;
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-elevated)', borderRadius: 12, width: 620, maxWidth: '94vw',
        maxHeight: '80vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 30px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)',
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>已归档条目</div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{items.length} 条记录</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {doneCount > 0 && <div style={{ padding: '3px 8px', borderRadius: 6, background: 'rgba(63,185,80,0.1)', fontSize: 10, color: '#3fb950', fontWeight: 600 }}>已完成 {doneCount}</div>}
            {failCount > 0 && <div style={{ padding: '3px 8px', borderRadius: 6, background: 'rgba(248,81,73,0.1)', fontSize: 10, color: '#f85149', fontWeight: 600 }}>失败 {failCount}</div>}
          </div>
          <button onClick={onClose} style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>x</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {loading ? (
            <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>加载中...</div>
          ) : items.length === 0 ? (
            <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
              暂无已归档条目
              <div style={{ fontSize: 11, marginTop: 4 }}>已完成的任务会自动归档到这里</div>
            </div>
          ) : (
            items.map((item: any) => (
              <div key={item.item_id} style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                borderRadius: 6, border: '1px solid var(--border-subtle)', background: 'var(--bg-primary)', fontSize: 12,
              }}>
                <div style={{
                  width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                  background: item.status === 'done' ? '#3fb950' : item.status === 'fail' ? '#f85149' : '#8b949e',
                }} />
                <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', flexShrink: 0 }}>{item.case_id}</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>{item.case_title}</span>
                <span style={{ fontSize: 10, color: 'var(--text-secondary)', flexShrink: 0 }}>{item.plan_title}</span>
                <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, flexShrink: 0, fontWeight: 600,
                  color: item.status === 'done' ? '#3fb950' : item.status === 'fail' ? '#f85149' : '#8b949e',
                  background: item.status === 'done' ? 'rgba(63,185,80,0.12)' : item.status === 'fail' ? 'rgba(248,81,73,0.12)' : 'rgba(139,148,158,0.12)',
                }}>
                  {item.status === 'done' ? '已完成' : item.status === 'fail' ? '失败' : item.status}
                </span>
                <button onClick={() => onUnarchive(item.item_id)}
                  style={{ padding: '3px 10px', fontSize: 10, border: 'none', borderRadius: 4, cursor: 'pointer',
                    background: 'var(--surface-secondary)', color: 'var(--text-secondary)', fontWeight: 500, flexShrink: 0,
                  }}>
                  取回
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  OverviewView — 运行总览
// ═══════════════════════════════════════════════════════════════════

function OverviewView({ data, loading, onRefresh, onSelectPlan, users, onViewResult, onTerminateItem, onDeleteItem }: {
  data: Record<string, any> | null;
  loading: boolean;
  onRefresh: () => void;
  onSelectPlan: (planId: string) => void;
  users: UserResponse[];
  onViewResult?: (item: PlanItemSummary) => void;
  onDeleteItem?: (planId: string, itemId: string, executionTaskId?: string) => void;
}) {
  const plans = (data?.plans as any[]) || [];
  const runningItems = (data?.running_items as any[]) || [];

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '16px 20px', background: 'var(--surface-secondary)' }}>
      {/* 头部统计 */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexShrink: 0 }}>
        {[
          { label: '总计划', value: data?.total_plans ?? 0, color: '#58a6ff' },
          { label: '总条目', value: data?.total_items ?? 0, color: '#8b949e' },
          { label: '执行中', value: data?.running_count ?? 0, color: '#3fb950' },
          { label: '待执行', value: data?.pending_count ?? 0, color: '#d29922' },
          { label: '已完成', value: data?.done_count ?? 0, color: '#8b949e' },
          { label: '失败', value: data?.fail_count ?? 0, color: '#f85149' },
        ].map(s => (
          <div key={s.label} style={{
            padding: '10px 16px', borderRadius: 8, border: '1px solid var(--border-subtle)',
            background: 'var(--bg-elevated)', minWidth: 80, textAlign: 'center',
          }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'flex-end', marginLeft: 'auto' }}>
          <button className="btn btn--ghost btn--sm" onClick={onRefresh} disabled={loading}
            style={{ fontSize: 12 }}>
            {loading ? '刷新中...' : '刷新'}
          </button>
        </div>
      </div>

      {/* 计划概览卡片 */}
      <div style={{ marginBottom: 16, flexShrink: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
          执行计划列表
        </div>
        {loading && plans.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>加载中...</div>
        ) : plans.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>暂无计划</div>
        ) : (
          <div style={{ display: 'flex', gap: 8, overflow: 'auto', paddingBottom: 4 }}>
            {plans.map((p: any) => {
              const planStatusMeta = PLAN_STATUS_META[p.status] || { label: p.status, color: '#8b949e' };
              return (
                <div key={p.plan_id} onClick={() => onSelectPlan(p.plan_id)}
                  style={{
                    minWidth: 200, padding: '10px 14px', borderRadius: 8, cursor: 'pointer',
                    background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
                  }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{p.title}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                      color: planStatusMeta.color, background: `${planStatusMeta.color}18`,
                    }}>{planStatusMeta.label}</span>
                  </div>
                  <div style={{ height: 3, background: 'var(--surface-tertiary)', borderRadius: 2, marginBottom: 6 }}>
                    <div style={{ width: `${p.progress_percent ?? 0}%`, height: '100%', background: 'var(--accent-primary)', borderRadius: 2 }} />
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 11, color: 'var(--text-tertiary)' }}>
                    <span>共 {p.item_count}</span>
                    <span style={{ color: '#3fb950' }}>运行 {p.running_count}</span>
                    <span style={{ color: '#d29922' }}>待执 {p.pending_count}</span>
                    <span style={{ color: '#f85149' }}>失败 {p.fail_count}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 运行中任务列表 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
          运行中任务
        </div>
        {loading && runningItems.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>加载中...</div>
        ) : runningItems.length === 0 ? (
          <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>暂没有运行中的任务</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--surface-primary)', position: 'sticky', top: 0, zIndex: 1 }}>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>计划</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>用例ID</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>标题</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>类型</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>执行人</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>优先级</th>
                <th style={{ padding: '6px 10px', textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)' }}>结果</th>
                <th style={{ padding: '6px 10px', textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '1px solid var(--border-subtle)', width: 100 }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {runningItems.map((item: any) => {
                const statusMeta = STATUS_META[item.status as ItemStatus] || STATUS_META.pending;
                return (
                  <tr key={item.item_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '6px 10px', color: 'var(--accent-primary)', fontSize: 11, cursor: 'pointer' }}
                      onClick={() => onSelectPlan(item.plan_id)}>
                      {item.plan_title || item.plan_id}
                    </td>
                    <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 10, color: 'var(--text-tertiary)' }}>{item.case_id}</td>
                    <td style={{ padding: '6px 10px', fontWeight: 500 }}>{item.case_title}</td>
                    <td style={{ padding: '6px 10px' }}>
                      <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3,
                        background: item.ref_type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)',
                        color: item.ref_type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                      }}>{item.ref_type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                    </td>
                    <td style={{ padding: '6px 10px', color: 'var(--text-secondary)' }}>
                      {item.assignee_id ? (users.find((u: UserResponse) => u.user_id === item.assignee_id)?.username || item.assignee_id) : (
                        <span style={{ color: 'var(--status-warn)', fontSize: 10 }}>未指派</span>
                      )}
                    </td>
                    <td style={{ padding: '6px 10px', color: PRIORITY_COLORS[item.priority] || '#8b949e', fontWeight: 600 }}>{item.priority}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'center' }}>
                      {(item.execution_task_id || item.result) && onViewResult ? (
                        <button type="button" onClick={(e) => { e.stopPropagation(); onViewResult(item); }}
                          style={{ fontSize: 10, padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border-subtle)',
                            background: 'var(--surface-secondary)', color: 'var(--accent-primary)', cursor: 'pointer' }}>
                          查看
                        </button>
                      ) : (
                        <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>-</span>
                      )}
                    </td>
                    <td style={{ padding: '6px 10px', textAlign: 'center' }}>
                      {onDeleteItem && (
                        <button type="button" onClick={(e) => { e.stopPropagation(); onDeleteItem(item.plan_id, item.item_id, item.execution_task_id); }}
                          style={{ fontSize: 10, padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border-subtle)',
                            background: 'transparent', color: '#d29922', cursor: 'pointer' }}>
                          取消执行
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  ResultModal — 用例执行结果查看
// ═══════════════════════════════════════════════════════════════════

function ResultModal({ item, taskData, loading, onClose }: {
  item: PlanItemSummary;
  taskData: any;
  loading: boolean;
  onClose: () => void;
}) {
  const caseSummary = taskData?.cases?.find((c: any) => c.auto_case_id === item.case_id);
  const r = caseSummary?.result_data;
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--overlay-bg)', backdropFilter: 'blur(2px)', zIndex: 2000, display: 'flex', justifyContent: 'center', alignItems: 'center' }}
      onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--surface-primary)', borderRadius: 12, width: 600, maxWidth: '94vw',
        maxHeight: '80vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 25px 80px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)',
      }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', background: 'var(--surface-tertiary)', padding: '1px 8px', borderRadius: 4 }}>{item.case_id}</span>
              <span style={{ fontSize: 13, fontWeight: 600 }}>执行结果</span>
            </span>
          </div>
          <button onClick={onClose} style={{ fontSize: 18, color: 'var(--text-tertiary)', background: 'none', border: 'none', cursor: 'pointer' }}>x</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>加载执行结果...</div>
          ) : taskData?.error ? (
            <div style={{ padding: 30, textAlign: 'center', color: 'var(--status-error)', fontSize: 13 }}>获取结果失败</div>
          ) : !caseSummary ? (
            <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>暂未获取到执行结果</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* ── 摘要卡片 ── */}
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {[
                  { label: '执行状态', value: caseSummary.status, color: STATUS_META[caseSummary.status as ItemStatus]?.color || '#8b949e' },
                  { label: '分派状态', value: caseSummary.dispatch_status },
                  { label: '进度', value: `${caseSummary.progress_percent ?? 0}%` },
                  { label: '尝试次数', value: caseSummary.dispatch_attempts ?? 0 },
                  { label: '事件数', value: caseSummary.event_count ?? 0 },
                ].map(kv => (
                  <div key={kv.label} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)', minWidth: 80 }}>
                    <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 2 }}>{kv.label}</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: kv.color || 'var(--text-primary)' }}>{kv.value ?? '-'}</div>
                  </div>
                ))}
              </div>

              {/* ── 步骤统计 ── */}
              {(caseSummary.step_total > 0) && (
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)' }}>
                    <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 2 }}>步骤总数</div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{caseSummary.step_total}</div>
                  </div>
                  <div style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(63,185,80,0.3)', background: 'rgba(63,185,80,0.05)' }}>
                    <div style={{ fontSize: 10, color: '#3fb950', marginBottom: 2 }}>通过</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#3fb950' }}>{caseSummary.step_passed ?? 0}</div>
                  </div>
                  <div style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(248,81,73,0.3)', background: 'rgba(248,81,73,0.05)' }}>
                    <div style={{ fontSize: 10, color: '#f85149', marginBottom: 2 }}>失败</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#f85149' }}>{caseSummary.step_failed ?? 0}</div>
                  </div>
                  <div style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(139,148,158,0.3)', background: 'rgba(139,148,158,0.05)' }}>
                    <div style={{ fontSize: 10, color: '#8b949e', marginBottom: 2 }}>跳过</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#8b949e' }}>{caseSummary.step_skipped ?? 0}</div>
                  </div>
                </div>
              )}

              {/* ── 时间线 ── */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: 12 }}>
                {caseSummary.started_at && <><span style={{ color: 'var(--text-tertiary)' }}>开始</span><span>{new Date(caseSummary.started_at).toLocaleString('zh-CN')}</span></>}
                {caseSummary.finished_at && <><span style={{ color: 'var(--text-tertiary)' }}>结束</span><span>{new Date(caseSummary.finished_at).toLocaleString('zh-CN')}</span></>}
                {caseSummary.failure_message && <><span style={{ color: 'var(--status-error)' }}>失败信息</span><span style={{ color: 'var(--status-error)' }}>{caseSummary.failure_message}</span></>}
              </div>
              {r?.assertions?.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>断言 ({r.assertions.length})</div>
                  {r.assertions.map((a: any, i: number) => (
                    <div key={i} style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border-subtle)', fontSize: 12, marginBottom: 4 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 500 }}>#{a.seq ?? i + 1} {a.name || '-'}</span>
                        <span style={{ padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 600,
                          color: a.status === 'PASSED' ? '#3fb950' : a.status === 'FAILED' ? '#f85149' : '#58a6ff',
                          background: a.status === 'PASSED' ? 'rgba(63,185,80,0.1)' : a.status === 'FAILED' ? 'rgba(248,81,73,0.1)' : 'rgba(88,166,255,0.1)',
                        }}>{a.status || '-'}</span>
                      </div>
                      {a.error && <div style={{ color: 'var(--status-error)', fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(a.error)}</div>}
                      {a.timestamp && <div style={{ color: 'var(--text-tertiary)', fontSize: 10, marginTop: 2 }}>{new Date(a.timestamp).toLocaleString('zh-CN')}</div>}
                    </div>
                  ))}
                </div>
              )}
              {r?.data && Object.keys(r.data).length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>返回数据</div>
                  <pre style={{ fontSize: 11, background: 'var(--surface-secondary)', padding: 10, borderRadius: 6, overflow: 'auto', maxHeight: 200, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{JSON.stringify(r.data, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}