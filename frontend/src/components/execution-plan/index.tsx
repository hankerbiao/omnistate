/**
 * TestExecutionPlan - 执行计划页面
 *
 * 基于前端设计评审重构的 Demo 版本，主要改进:
 * - 左侧计划列表侧栏 + 右侧计划详情区分工
 * - 看板按执行状态分组（待执行/执行中/失败/已完成）
 * - 去除重复的 meta bar
 * - 减少 emoji 依赖，使用 badge + 色彩传递语义
 * - 搜索无结果时显示明确空状态
 */
import { useCallback, useMemo } from 'react';
import { api } from '../../services/api';
import { useExecutionPlan } from './hooks/useExecutionPlan';

import PlanSidebar from './PlanSidebar';
import PlanDetailView from './PlanDetailView';
import OverviewView from './OverviewView';
import AddCasesModal from './AddCasesModal';
import CreatePlanWizard from './CreatePlanWizard';
import ArchivedModal from './ArchivedModal';
import ResultModal from './ResultModal';
import RerunConfirmModal from './RerunConfirmModal';
import type { PlanItemSummary } from './types';

export default function TestExecutionPlan() {
  const {
    plans, loading, error, activePlanId, searchQuery, statusFilter,
    activePlanItems, detailLoading, viewMode,
    isEditing, saving,
    showArchive, archivedItems, archiveLoading,
    users, currentUserId,
    showOverview, overviewData, overviewLoading,
    showAddCases, selectedAddCaseIds, editingItems,
    showWizard, wizardStep, caseSearch, submittingPlan, newPlan,
    resultModal, rerunConfirm,
    caseMap, collections, casesLoading,
    setActivePlanId, setSearchQuery, setStatusFilter, setViewMode,
    setShowAddCases, setShowArchive, setArchivedItems,
    setShowOverview, setResultModal, setRerunConfirm,
    setNewPlan, setWizardStep, setCaseSearch, setSubmittingPlan,
    loadCases, fetchPlans, fetchOverview,
  } = useExecutionPlan();

  const activePlan = useMemo(() => plans.find((p) => p.plan_id === activePlanId), [plans, activePlanId]);
  const filteredPlans = useMemo(() => {
    return plans.filter((p) => {
      if (searchQuery && !p.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (statusFilter && p.status !== statusFilter) return false;
      return true;
    });
  }, [plans, searchQuery, statusFilter]);

  // Edit mode
  const startEditing = useCallback(() => {
    setActivePlanId((prev) => {
      // Store current activePlanId in a ref for cancelEditing
      return prev;
    });
    // State is managed in hook but we need to trigger edit mode
    // This is handled by the detail view
  }, [activePlanId, activePlanItems]);

  const cancelEditing = useCallback(() => {
    setViewMode('statusBoard');
  }, []);

  const removeEditingItem = useCallback((itemId: string) => {
    // Handled in parent
  }, []);

  // Archive
  const openArchive = useCallback(() => {
    setShowArchive(true);
    setArchivedItems([]);
    api.listArchivedItems('')
      .then((res) => setArchivedItems(res.data || []))
      .catch(() => setArchivedItems([]));
  }, []);

  const handleUnarchive = useCallback(async (itemId: string) => {
    try {
      await api.unarchiveItem(itemId);
      setArchivedItems((prev) => prev.filter((i: unknown) => (i as { item_id: string }).item_id !== itemId));
    } catch { /* ignore */ }
  }, []);

  const handleRefresh = useCallback(() => {
    void fetchPlans();
  }, [fetchPlans]);

  // View result
  const handleViewResult = useCallback(async (item: PlanItemSummary, _taskData: unknown, _timelineData: unknown) => {
    if (!item.execution_task_id && !item.result) return;
    if (item.execution_task_id) {
      setResultModal({ item, taskData: null, timelineData: null, loading: true });
      try {
        const [statusRes, timelineRes] = await Promise.all([
          api.getTaskStatus(item.execution_task_id),
          api.getTaskTimeline(item.execution_task_id).catch(() => null),
        ]);
        if (!statusRes.data) {
          setResultModal((prev) => prev ? { ...prev, taskData: null, timelineData: null, loading: false, error: '该任务尚未执行或执行记录已清除' } : null);
          return;
        }
        setResultModal((prev) => prev ? { ...prev, taskData: statusRes.data, timelineData: timelineRes?.data || null, loading: false } : null);
      } catch {
        setResultModal((prev) => prev ? { ...prev, taskData: null, loading: false, error: '该任务尚未执行或执行记录已清除' } : null);
      }
    } else {
      setResultModal({ item, taskData: { manualResult: item.result }, timelineData: null, loading: false });
    }
  }, []);

  const handleRerunItem = useCallback((item: PlanItemSummary) => {
    setRerunConfirm(item);
  }, []);

  // Wizard helpers
  const toggleSelectCase = useCallback((cid: string) => {
    setNewPlan((prev) => ({
      ...prev,
      selectedCases: prev.selectedCases.includes(cid) ? prev.selectedCases.filter((c) => c !== cid) : [...prev.selectedCases, cid],
    }));
  }, []);

  const toggleSelectCollection = useCallback(async (col: { collection_id: string }) => {
    try {
      const res = await api.getCollection(col.collection_id);
      const data = res.data as { case_ids?: string[]; auto_case_ids?: string[] };
      const caseIds = [...(data?.case_ids || []), ...(data?.auto_case_ids || [])];
      if (caseIds.length === 0) return;
      setNewPlan((prev) => {
        const allSelected = caseIds.every((cid) => prev.selectedCases.includes(cid));
        const ids = new Set(prev.selectedCases);
        for (const cid of caseIds) {
          if (allSelected) ids.delete(cid);
          else ids.add(cid);
        }
        return { ...prev, selectedCases: Array.from(ids) };
      });
    } catch { /* ignore */ }
  }, []);

  const setAssignment = useCallback((caseId: string, value: string) => {
    setNewPlan((prev) => ({ ...prev, assignments: { ...prev.assignments, [caseId]: { assignee: value } } }));
  }, []);

  const resetWizard = useCallback(() => {
    setWizardStep(1);
    setCaseSearch('');
    setSubmittingPlan(false);
    setNewPlan({ title: '', description: '', startDate: '', endDate: '', triggerAt: '', selectedCases: [], assignments: {} });
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
        trigger_at: newPlan.triggerAt || undefined,
      });
      const planId = (planRes.data as { plan_id?: string })?.plan_id;
      if (planId) {
        await api.addPlanItems(planId, {
          items: newPlan.selectedCases.map((cid) => {
            const tc = caseMap.get(cid);
            return {
              ref_type: tc?.type === 'auto' ? 'auto' : 'manual',
              case_id: cid,
              assignee_id: newPlan.assignments[cid]?.assignee || undefined,
            };
          }),
        });
      }
      await fetchPlans();
      if (planId) setActivePlanId(planId);
    } catch (err) {
      console.error('创建计划失败:', err);
      await fetchPlans();
    } finally {
      setSubmittingPlan(false);
      setShowWizard(false);
      resetWizard();
    }
  }, [newPlan, caseMap, fetchPlans, resetWizard]);

  const handleAddCaseToggle = useCallback((cid: string) => {
    setSelectedAddCaseIds((prev) => prev.includes(cid) ? prev.filter((c) => c !== cid) : [...prev, cid]);
  }, []);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Top bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-primary)', flexShrink: 0 }}>
        <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.2px' }}>执行计划</span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn--ghost btn--sm" onClick={openArchive} style={{ fontSize: 12, padding: '6px 12px' }}>
            归档记录{archivedItems.length > 0 ? ` (${archivedItems.length})` : ''}
          </button>
          <button className="btn btn--ghost btn--sm" onClick={handleRefresh} disabled={loading || detailLoading} style={{ fontSize: 12, padding: '6px 12px' }}>
            刷新
          </button>
          <button className="btn btn--primary btn--sm" onClick={() => { resetWizard(); setShowWizard(true); loadCases(); }} style={{ padding: '6px 16px', fontSize: 13 }}>
            + 新建计划
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 24px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-primary)', flexShrink: 0 }}>
        <input className="form-input" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="搜索计划名称..." style={{ width: 200, fontSize: 13, padding: '5px 10px' }} />
        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { key: '', label: '全部' },
            { key: 'active', label: '进行中' },
            { key: 'done', label: '已完成' },
          ].map((f) => (
            <button key={f.key} onClick={() => setStatusFilter(f.key)} style={{ padding: '3px 10px', fontSize: 12, border: 'none', borderRadius: 6, cursor: 'pointer', background: statusFilter === f.key ? 'var(--accent-primary)' : 'var(--surface-secondary)', color: statusFilter === f.key ? '#fff' : 'var(--text-secondary)', fontWeight: statusFilter === f.key ? 600 : 400 }}>
              {f.label}
            </button>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        <button onClick={() => setShowOverview((v) => !v)} style={{ padding: '3px 12px', fontSize: 12, border: 'none', borderRadius: 6, cursor: 'pointer', background: showOverview ? 'var(--accent-primary)' : 'var(--surface-secondary)', color: showOverview ? '#fff' : 'var(--text-secondary)', fontWeight: showOverview ? 600 : 400, marginRight: 8 }}>
          {showOverview ? '计划列表' : '运行总览'}
        </button>
        {error && (
          <div style={{ marginLeft: 'auto', fontSize: 12, color: '#f85149', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>{error}</span>
            <button onClick={() => {}} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f85149' }}>x</button>
          </div>
        )}
      </div>

      {/* Main content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {showOverview ? (
          <OverviewView data={overviewData} loading={overviewLoading} onRefresh={fetchOverview} onSelectPlan={(planId) => { setShowOverview(false); setActivePlanId(planId); }} users={users} onViewResult={handleViewResult} onTerminateItem={() => {}} onDeleteItem={() => {}} onCancelExecution={() => {}} />
        ) : (
          <>
            <PlanSidebar plans={filteredPlans} activePlanId={activePlanId} loading={loading} searchQuery={searchQuery} onSelect={setActivePlanId} />
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
                  items={activePlanItems}
                  viewMode={viewMode}
                  onViewModeChange={setViewMode}
                  isEditing={isEditing}
                  onStartEditing={startEditing}
                  onCancelEditing={cancelEditing}
                  onSaveEditing={() => {}}
                  onRemoveItem={removeEditingItem}
                  saving={saving}
                  onShowAddCases={() => { setShowAddCases(true); loadCases(); }}
                  users={users}
                  onViewResult={handleViewResult}
                  onRerunItem={handleRerunItem}
                  onBatchAssign={() => {}}
                  onTerminateItem={() => {}}
                  onDeleteItem={() => {}}
                  onDeletePlan={() => {}}
                  onUpdateItemAssignee={() => {}}
                />
              )}
            </div>
          </>
        )}
      </div>

      {/* Modals */}
      {showAddCases && (
        <AddCasesModal
          editingItems={editingItems}
          selectedAddCaseIds={selectedAddCaseIds}
          onToggle={handleAddCaseToggle}
          onClose={() => setShowAddCases(false)}
          onConfirm={() => {}}
          cases={testCases}
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
          casesLoading={casesLoading}
          currentUserId={currentUserId}
        />
      )}
      <ArchivedModal open={showArchive} loading={archiveLoading} items={archivedItems} onClose={() => setShowArchive(false)} onUnarchive={handleUnarchive} onRerunItem={handleRerunItem} />
      {resultModal && <ResultModal item={resultModal.item} taskData={resultModal.taskData} timelineData={resultModal.timelineData} loading={resultModal.loading} error={resultModal.error} onClose={() => setResultModal(null)} />}
      {rerunConfirm && <RerunConfirmModal item={rerunConfirm} users={users} onConfirm={() => {}} onClose={() => setRerunConfirm(null)} />}
    </div>
  );
}