/**
 * TestExecutionPlanDemo — 执行计划页面 (Refactored)
 *
 * P1 重构：从 2607 行单文件拆分为模块化架构
 * - 状态逻辑 → useTestPlan hook
 * - 类型/常量 → test-plan/types.ts
 * - 4 个 Modal → test-plan/modals/ (shadcn Dialog)
 * - PlanSidebar → test-plan/PlanSidebar.tsx
 * - CreatePlanWizard → test-plan/modals/CreatePlanWizard.tsx (shadcn Dialog)
 *
 * 本文件只负责：布局编排 + 导入子模块 + 渲染 Modals
 */
import { CalendarClock, RefreshCw, Plus, Eye, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { EmptyState, LoadingState, ErrorState } from '@/components/ui/states';
import { useTestPlan } from './test-plan/useTestPlan';
import { PlanSidebar } from './test-plan/PlanSidebar';
import { PlanDetailView } from './test-plan/views';
import { OverviewView } from './test-plan/OverviewView';
import { AddCasesModal } from './test-plan/modals/AddCasesModal';
import { CreatePlanWizard } from './test-plan/modals/CreatePlanWizard';
import { ResultModal } from './test-plan/modals/ResultModal';
import { RerunConfirmModal } from './test-plan/modals/RerunConfirmModal';

export default function TestExecutionPlanDemo() {
  const h = useTestPlan();

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* ── Top bar ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-primary)', flexShrink: 0 }}>
        <div className="flex items-center gap-3">
          <CalendarClock size={18} className="text-[var(--accent-primary)]" />
          <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.2px' }}>执行计划</span>
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn btn--ghost btn--sm" onClick={h.handleRefresh} disabled={h.loading || h.detailLoading}>
            <RefreshCw size={14} className={h.loading || h.detailLoading ? 'animate-spin' : ''} /> 刷新
          </button>
          <button type="button" className="btn btn--primary btn--sm" onClick={() => { h.resetWizard(); h.setShowWizard(true); h.loadCases(); }}>
            <Plus size={14} /> 新建计划
          </button>
        </div>
      </div>

      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 24px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-primary)', flexShrink: 0 }}>
        <input className="form-input" value={h.searchQuery} onChange={e => h.setSearchQuery(e.target.value)} placeholder="搜索计划名称..." style={{ width: 200, fontSize: 13, padding: '5px 10px' }} />
        <div className="flex gap-1">
          {[{ key: '', label: '全部' }, { key: 'active', label: '进行中' }, { key: 'done', label: '已完成' }].map(f => (
            <button key={f.key} onClick={() => h.setStatusFilter(f.key)}
              style={{ padding: '3px 10px', fontSize: 12, border: 'none', borderRadius: 6, cursor: 'pointer', background: h.statusFilter === f.key ? 'var(--accent-primary)' : 'var(--surface-secondary)', color: h.statusFilter === f.key ? '#fff' : 'var(--text-secondary)', fontWeight: h.statusFilter === f.key ? 600 : 400 }}>
              {f.label}
            </button>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        <button type="button" className={`btn btn--sm ${h.showOverview ? 'btn--primary' : 'btn--secondary'}`} onClick={() => h.setShowOverview(v => !v)}>
          <Eye size={14} /> {h.showOverview ? '计划列表' : '运行总览'}
        </button>
        {h.error && (
          <div className="flex items-center gap-1.5 text-xs text-[var(--status-error)]">
            <AlertCircle size={12} /> {h.error}
            <button onClick={() => h.setError(null)} className="text-[var(--status-error)] hover:opacity-70">x</button>
          </div>
        )}
      </div>

      {/* ── Main content ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {h.showOverview ? (
          <OverviewView
            data={h.overviewData}
            loading={h.overviewLoading}
            onRefresh={h.fetchOverview}
            onSelectPlan={(planId) => { h.setShowOverview(false); h.setActivePlanId(planId); }}
            users={h.users}
            onViewResult={h.handleViewResult}
            onDeleteItem={h.handleTerminateItem}
            onCancelExecution={(itemId: string) => h.handleTerminateItem('', itemId)}
          />
        ) : (
          <>
            <PlanSidebar plans={h.filteredPlans} activePlanId={h.activePlanId} loading={h.loading} searchQuery={h.searchQuery} onSelect={h.setActivePlanId} />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--surface-secondary)' }}>
              {!h.activePlan ? (
                <EmptyState title="从左侧选择一个计划" description="或点击「新建计划」创建一个新的执行计划" className="flex-1" />
              ) : h.detailLoading ? (
                <LoadingState title="加载计划详情..." className="flex-1" />
              ) : (
                <PlanDetailView
                  plan={h.activePlan}
                  items={h.isEditing ? h.editingItems : h.activePlanItems}
                  viewMode={h.viewMode}
                  onViewModeChange={h.setViewMode}
                  isEditing={h.isEditing}
                  onStartEditing={h.startEditing}
                  onCancelEditing={h.cancelEditing}
                  onSaveEditing={h.saveEditing}
                  onRemoveItem={h.removeEditingItem}
                  saving={h.saving}
                  onShowAddCases={() => { h.setShowAddCases(true); h.loadCases(); }}
                  users={h.users}
                  onViewResult={h.handleViewResult}
                  onRerunItem={h.handleRerunItem}
                  onBatchAssign={h.handleBatchAssign}
                  onTerminateItem={h.handleTerminateItem}
                  onDeleteItem={h.handleDeleteItem}
                  onDeletePlan={h.handleDeletePlan}
                  onUpdateItemAssignee={h.handleUpdateItemAssignee}
                />
              )}
            </div>
          </>
        )}
      </div>

      {/* ── Modals ── */}
      {h.showAddCases && (
        <AddCasesModal
          editingItems={h.editingItems}
          selectedAddCaseIds={h.selectedAddCaseIds}
          onToggle={h.handleAddCaseToggle}
          onClose={() => h.setShowAddCases(false)}
          onConfirm={h.handleAddSelectedCases}
          cases={Array.from(h.caseMap.values()).map(tc => ({ id: tc.id, title: tc.title, type: tc.type || 'manual', priority: tc.priority || 'P3' }))}
          users={h.users}
        />
      )}
      {h.showWizard && (
        <CreatePlanWizard
          wizardStep={h.wizardStep}
          onStepChange={h.setWizardStep}
          newPlan={h.newPlan}
          onNewPlanChange={h.setNewPlan}
          caseSearch={h.caseSearch}
          onCaseSearchChange={h.setCaseSearch}
          submittingPlan={h.submittingPlan}
          onCreatePlan={h.handleCreatePlan}
          onClose={() => h.setShowWizard(false)}
          onToggleCase={h.toggleSelectCase}
          onToggleCollection={h.toggleSelectCollection}
          onSetAssignment={h.setAssignment}
          users={h.users}
          collections={h.collections}
          caseMap={h.caseMap}
          casesLoading={h.casesLoading}
          currentUserId={h.currentUserId}
        />
      )}
      {h.resultModal && (
        <ResultModal
          item={h.resultModal.item}
          taskData={h.resultModal.taskData}
          timelineData={h.resultModal.timelineData}
          loading={h.resultModal.loading}
          error={h.resultModal.error}
          onClose={() => h.setResultModal(null)}
        />
      )}
      {h.rerunConfirm && (
        <RerunConfirmModal
          item={h.rerunConfirm}
          users={h.users}
          onConfirm={h.confirmRerun}
          onClose={() => h.setRerunConfirm(null)}
        />
      )}
    </div>
  );
}
