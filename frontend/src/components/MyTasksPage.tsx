import React, { useCallback, useEffect, useState, useMemo } from 'react';
import { api } from '../services/api';
import type { WorkItem, TestCaseResponse, RequirementResponse, PlanTaskItemResponse, PlanTaskResultPayload } from '../types';
import { WorkflowPanel, WorkflowActionToolbar } from './workflow';
import {
  getStateLabel,
  getWorkflowStateStyle,
  type WorkflowTypeCode,
} from '../constants/workflowLabels';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import PlanTaskTable from './PlanTaskTable';
import ResultBackfillModal from './ResultBackfillModal';
import SingleDispatchModal from './SingleDispatchModal';
import DispatchWorkflow from './DispatchWorkflow';
import type { PlanTask, PlanTaskResult } from './myTasksTypes';
import { TYPE_LABELS, TYPE_COLORS, groupBadgeStyle, myTasksStyles } from './myTasksTypes';

interface MyTasksPageProps {
  userId: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  Transformer — 后端 PlanTaskItemResponse → 前端 PlanTask
// ═══════════════════════════════════════════════════════════════════════

function transformApiItem(item: PlanTaskItemResponse): PlanTask {
  const resultPayload = item.result;
  const result: PlanTaskResult | undefined = resultPayload
    ? {
        passed: resultPayload.passed,
        notes: resultPayload.notes,
        severity: resultPayload.severity,
        executedAt: resultPayload.executed_at ?? '',
        actual: resultPayload.actual,
        expected: resultPayload.expected,
        env: resultPayload.env,
        testData: resultPayload.test_data,
        bugId: resultPayload.bug_id,
        actualDuration: resultPayload.actual_duration,
        attachments: resultPayload.attachments,
      }
    : undefined;

  return {
    id: item.item_id,
    planId: item.plan_id,
    planTitle: item.plan_title,
    caseId: item.case_id,
    caseTitle: item.case_title,
    type: item.ref_type === 'auto' ? 'auto' : 'manual',
    component: item.component,
    assignee: item.assignee_id ?? '',
    status: item.status as PlanTask['status'],
    result,
  };
}

const MyTasksPage: React.FC<MyTasksPageProps> = ({ userId }) => {
  const [items, setItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [itemDetail, setItemDetail] = useState<RequirementResponse | TestCaseResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [workflowRefreshSignal, setWorkflowRefreshSignal] = useState(0);

  // Plan task state
  const [planTasks, setPlanTasks] = useState<PlanTask[]>([]);
  const [planTasksLoading, setPlanTasksLoading] = useState(false);
  const [planTasksError, setPlanTasksError] = useState<string | null>(null);

  // Modal state: which task is being edited for result backfill
  const [resultModalTask, setResultModalTask] = useState<PlanTask | null>(null);

  // Single dispatch modal state
  const [dispatchModal, setDispatchModal] = useState<{
    open: boolean; itemId: string; caseId: string; caseTitle: string;
  }>({ open: false, itemId: '', caseId: '', caseTitle: '' });

  // Batch dispatch modal state
  const [batchOpen, setBatchOpen] = useState(false);

  // ── Derived data ──

  const displayPlanTasks = useMemo(
    () => planTasks, // API 已经按 assignee_id 过滤
    [planTasks],
  );

  const autoTasksForDispatch = useMemo(
    () => displayPlanTasks.filter(t => t.type === 'auto' && t.status !== 'done'),
    [displayPlanTasks],
  );

  const groupedItems = useMemo(() => {
    return items.reduce<Record<string, WorkItem[]>>((acc, item) => {
      const type = item.type_code;
      if (!acc[type]) acc[type] = [];
      acc[type].push(item);
      return acc;
    }, {});
  }, [items]);

  const typeOrder = ['PLAN_TASK', 'REQUIREMENT', 'TEST_CASE'];

  // ── Data fetching ──

  const fetchMyWorkflowItems = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.listMyWorkItems(userId);
      setItems(response.data || []);
    } catch (err) {
      setError('获取工作流任务列表失败');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const fetchPlanTasks = useCallback(async () => {
    if (!userId) return;
    setPlanTasksLoading(true);
    setPlanTasksError(null);
    try {
      const response = await api.listMyPlanItems(userId);
      setPlanTasks((response.data || []).map(transformApiItem));
    } catch (err) {
      setPlanTasksError('获取计划任务列表失败');
    } finally {
      setPlanTasksLoading(false);
    }
  }, [userId]);

  useEffect(() => { fetchMyWorkflowItems(); }, [fetchMyWorkflowItems]);
  useEffect(() => { fetchPlanTasks(); }, [fetchPlanTasks]);

  // ── Refresh all ──

  const handleRefreshAll = useCallback(() => {
    void fetchMyWorkflowItems();
    void fetchPlanTasks();
  }, [fetchMyWorkflowItems, fetchPlanTasks]);

  // ── Workflow item handlers ──

  const loadItemDetail = async (item: WorkItem) => {
    setLoadingDetail(true);
    setItemDetail(null);
    try {
      if (item.type_code === 'REQUIREMENT' && item.req_id) {
        const res = await api.getRequirement(item.req_id);
        setItemDetail(res.data);
      } else if (item.type_code === 'TEST_CASE') {
        const caseId = (item as WorkItem & { case_id?: string }).case_id;
        if (caseId) {
          const res = await api.getTestCase(caseId);
          setItemDetail(res.data);
        }
      }
    } catch { /* ignore */ } finally { setLoadingDetail(false); }
  };

  const handleToggleExpand = async (itemId: string) => {
    if (expandedId === itemId) { setExpandedId(null); setItemDetail(null); return; }
    setExpandedId(itemId);
    const item = items.find(i => i.item_id === itemId);
    if (item) await loadItemDetail(item);
  };

  const handleTaskWorkflowSuccess = async () => {
    await fetchMyWorkflowItems();
    setWorkflowRefreshSignal(n => n + 1);
  };

  const getTypeCode = (type: string): WorkflowTypeCode =>
    type === 'TEST_CASE' ? 'TEST_CASE' : 'REQUIREMENT';

  // ── Plan task handlers ──

  /** 乐观更新本地状态 + 同步后端 */
  const updatePlanTaskStatus = useCallback(async (taskId: string, status: PlanTask['status']) => {
    // 乐观更新
    setPlanTasks(prev => prev.map(t => t.id === taskId ? { ...t, status } : t));
    // 同步后端
    try {
      const task = planTasks.find(t => t.id === taskId);
      if (task) {
        await api.updatePlanItem(task.planId, taskId, { status });
      }
    } catch {
      // 失败时回滚
      setPlanTasks(prev => prev.map(t =>
        t.id === taskId && t.status === status
          ? { ...t, status: planTasks.find(pt => pt.id === taskId)?.status || 'pending' }
          : t,
      ));
    }
  }, [planTasks]);

  const handleOpenResultModal = useCallback((task: PlanTask) => {
    setResultModalTask(task);
  }, []);

  const handleCloseResultModal = useCallback(() => {
    setResultModalTask(null);
  }, []);

  const handleSubmitResult = useCallback(async (taskId: string, result: PlanTaskResult) => {
    try {
      await api.submitPlanItemResult(taskId, {
        passed: result.passed ?? true,
        notes: result.notes ?? '',
        severity: result.severity ?? 'normal',
        actual: result.actual ?? '',
        expected: result.expected ?? '',
        env: result.env ?? '',
        test_data: result.testData ?? '',
        bug_id: result.bugId ?? '',
        actual_duration: result.actualDuration ?? '',
        attachments: result.attachments ?? [],
        executed_at: result.executedAt
          ? new Date(result.executedAt).toISOString()
          : new Date().toISOString(),
      });
      // 成功后刷新列表
      await fetchPlanTasks();
    } catch (err) {
      console.error('提交结果失败:', err);
    }
  }, [fetchPlanTasks]);

  const handleOpenDispatchModal = useCallback((task: PlanTask) => {
    setDispatchModal({
      open: true,
      itemId: task.id,
      caseId: task.caseId,
      caseTitle: task.caseTitle,
    });
  }, []);

  const handleCloseDispatchModal = useCallback(() => {
    setDispatchModal({ open: false, itemId: '', caseId: '', caseTitle: '' });
  }, []);

  const handleDispatchSuccess = useCallback(async () => {
    const { itemId } = dispatchModal;
    // 更新本地状态为 running
    setPlanTasks(prev => prev.map(t =>
      t.id === itemId ? { ...t, status: 'running' } : t,
    ));
    // 刷新列表
    await fetchPlanTasks();
  }, [dispatchModal, fetchPlanTasks]);

  const handleOpenBatchDispatch = useCallback(() => {
    setBatchOpen(true);
  }, []);

  const handleCloseBatchDispatch = useCallback(() => {
    setBatchOpen(false);
  }, []);

  const handleBatchSubmit = useCallback(async (caseIds: string[]) => {
    // 找到对应的 item_ids
    const itemIds = displayPlanTasks
      .filter(t => caseIds.includes(t.caseId))
      .map(t => t.id);

    if (itemIds.length === 0) return;

    // 乐观更新
    setPlanTasks(prev => prev.map(t =>
      caseIds.includes(t.caseId) ? { ...t, status: 'running' } : t,
    ));

    try {
      await api.batchDispatchPlanItems({ item_ids: itemIds });
      await fetchPlanTasks();
    } catch (err) {
      console.error('批量下发失败:', err);
      await fetchPlanTasks(); // 回滚用刷新
    }
  }, [displayPlanTasks, fetchPlanTasks]);

  // ── Pending count for stats ──
  const pendingCount = useMemo(() => {
    const workflowPending = items.filter(
      item => item.current_state && !['RELEASED', 'DONE', 'CLOSED', 'ARCHIVED'].includes(item.current_state),
    ).length;
    const planPending = displayPlanTasks.filter(t => t.status !== 'done').length;
    return workflowPending + planPending;
  }, [items, displayPlanTasks]);

  return (
    <div className="page-content">
      <PageToolbar
        meta={(
          <>
            <StatPill label="待处理" value={pendingCount} />
            <StatPill label="用户" value={userId} tone="info" />
          </>
        )}
        actions={(
          <button type="button" className="btn btn--secondary btn--sm" onClick={handleRefreshAll} disabled={loading || planTasksLoading}>
            刷新
          </button>
        )}
      />

      <div className="info-banner">
        我的任务汇总了工作流指派和执行计划分配的待办事项。
        计划任务可直接回填测试结果。
      </div>

      {error && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          {error} <button type="button" className="btn btn--ghost btn--sm" onClick={() => setError(null)}>×</button>
        </div>
      )}

      {planTasksError && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          {planTasksError} <button type="button" className="btn btn--ghost btn--sm" onClick={() => setPlanTasksError(null)}>×</button>
        </div>
      )}

      {loading && planTasksLoading ? (
        <div className="loading-overlay"><div className="loading-spinner" /></div>
      ) : items.length === 0 && displayPlanTasks.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">✅</div>
          <p className="empty-state__text">暂无待处理的任务</p>
        </div>
      ) : (
        <div style={myTasksStyles.list}>
          {/* ── Plan Tasks ── */}
          {displayPlanTasks.length > 0 && (
            <PlanTaskTable
              planTasks={displayPlanTasks}
              isDemo={false}
              hasAutoCasesForDispatch={autoTasksForDispatch.length > 0}
              onStatusUpdate={updatePlanTaskStatus}
              onOpenResultModal={handleOpenResultModal}
              onOpenDispatchModal={handleOpenDispatchModal}
              onBatchDispatch={handleOpenBatchDispatch}
            />
          )}

          {/* ── Workflow items ── */}
          {typeOrder.filter(t => t !== 'PLAN_TASK').map(type => {
            const typeItems = groupedItems[type];
            if (!typeItems?.length) return null;
            return (
              <div key={type} style={myTasksStyles.group}>
                <div style={myTasksStyles.groupHeader}>
                  <span style={groupBadgeStyle(TYPE_COLORS[type] || { bg: '#f5f5f5', color: '#666' })}>
                    {TYPE_LABELS[type] || type}
                  </span>
                  <span style={myTasksStyles.groupCount}>{typeItems.length} 项</span>
                </div>
                {typeItems.map(item => {
                  const isExpanded = expandedId === item.item_id;
                  const typeCode = getTypeCode(item.type_code);
                  return (
                    <div key={item.item_id}>
                      {/* Compact row */}
                      <div
                        onClick={() => { void handleToggleExpand(item.item_id); }}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px',
                          borderBottom: '0.5px solid var(--border-subtle)',
                          cursor: 'pointer', fontSize: 13, transition: 'background 0.1s',
                          background: isExpanded
                            ? 'color-mix(in srgb, var(--accent-primary) 4%, transparent)'
                            : undefined,
                        }}
                      >
                        {/* Expand arrow */}
                        <span style={{
                          fontSize: 9, color: isExpanded ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                          transition: 'transform 0.15s',
                          transform: isExpanded ? 'rotate(90deg)' : 'none',
                          flexShrink: 0,
                        }}>
                          ▶
                        </span>

                        {/* Title */}
                        <span style={{
                          flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap', fontWeight: isExpanded ? 600 : 500,
                        }}>
                          {item.title}
                        </span>

                        {/* State badge */}
                        <span className="status-badge" style={{
                          ...getWorkflowStateStyle(item.current_state),
                          fontSize: 10, padding: '2px 8px', flexShrink: 0,
                        }}>
                          {getStateLabel(item.current_state, typeCode)}
                        </span>

                        {/* Time */}
                        <span style={{
                          fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', flexShrink: 0,
                        }}>
                          {new Date(item.updated_at).toLocaleString('zh-CN', {
                            month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
                          })}
                        </span>

                        {/* Workflow actions */}
                        <WorkflowActionToolbar
                          workflowItemId={item.item_id}
                          typeCode={typeCode}
                          defaultPriority={itemDetail && 'priority' in itemDetail ? String(itemDetail.priority || '') : ''}
                          onTransitionSuccess={handleTaskWorkflowSuccess}
                          compact
                        />
                      </div>

                      {/* Expanded section */}
                      {isExpanded && (
                        <div style={{
                          padding: '10px 12px 12px 28px', borderBottom: '0.5px solid var(--border-subtle)',
                          background: 'var(--bg-primary)',
                        }}>
                          {loadingDetail ? (
                            <div style={myTasksStyles.loadingSmall}>
                              <div className="loading-spinner" style={{ width: 20, height: 20 }} />
                            </div>
                          ) : (
                            <>
                              {item.content && <p style={myTasksStyles.contentPreview}>{item.content}</p>}
                              {itemDetail && 'description' in itemDetail && itemDetail.description && (
                                <p style={myTasksStyles.contentPreview}>{itemDetail.description}</p>
                              )}
                            </>
                          )}
                          <WorkflowPanel
                            workflowItemId={item.item_id}
                            entityLabel={item.title}
                            typeCode={typeCode}
                            defaultPriority={itemDetail && 'priority' in itemDetail ? String(itemDetail.priority || '') : ''}
                            onTransitionSuccess={handleTaskWorkflowSuccess}
                            compact hideToolbar refreshSignal={workflowRefreshSignal}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/*  Result Backfill Modal                                  */}
      {/* ════════════════════════════════════════════════════════ */}
      <ResultBackfillModal
        task={resultModalTask}
        onClose={handleCloseResultModal}
        onSubmit={handleSubmitResult}
      />

      {/* ════════════════════════════════════════════════════════ */}
      {/*  Single Dispatch Modal                                 */}
      {/* ════════════════════════════════════════════════════════ */}
      <SingleDispatchModal
        open={dispatchModal.open}
        itemId={dispatchModal.itemId}
        caseId={dispatchModal.caseId}
        caseTitle={dispatchModal.caseTitle}
        onClose={handleCloseDispatchModal}
        onSuccess={handleDispatchSuccess}
      />

      {/* ════════════════════════════════════════════════════════ */}
      {/*  Dispatch Workflow (2-step: DUT select → Configure)   */}
      {/* ════════════════════════════════════════════════════════ */}
      <DispatchWorkflow
        open={batchOpen}
        autoTasks={autoTasksForDispatch}
        onClose={handleCloseBatchDispatch}
        onFinish={(caseIds) => {
          handleBatchSubmit(caseIds);
        }}
      />
    </div>
  );
};

export default MyTasksPage;
