import React, { useCallback, useEffect, useState, useMemo } from 'react';
import { api } from '../services/api';
import type { WorkItem, TestCaseResponse, RequirementResponse } from '../types';
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
import { MOCK_PLAN_TASKS, TYPE_LABELS, TYPE_COLORS, groupBadgeStyle, myTasksStyles } from './myTasksTypes';

interface MyTasksPageProps {
  userId: string;
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
  const [planTasks, setPlanTasks] = useState<PlanTask[]>(() => MOCK_PLAN_TASKS);

  // Modal state: which task is being edited for result backfill
  const [resultModalTask, setResultModalTask] = useState<PlanTask | null>(null);

  // Single dispatch modal state
  const [dispatchModal, setDispatchModal] = useState<{
    open: boolean; caseId: string; caseTitle: string;
  }>({ open: false, caseId: '', caseTitle: '' });

  // Batch dispatch modal state
  const [batchOpen, setBatchOpen] = useState(false);

  // ── Derived data ──

  const userPlanTasks = useMemo(
    () => planTasks.filter(t => t.assignee === userId),
    [planTasks, userId],
  );
  // Mock fallback: 如果当前用户没有指派的计划任务，展示团队任务作为演示
  const displayPlanTasks = useMemo(
    () => (userPlanTasks.length > 0 ? userPlanTasks : planTasks.map(t => ({ ...t, assignee: userId, _demo: true }))),
    [userPlanTasks, planTasks, userId],
  );

  const isDemo = !!(displayPlanTasks as any[])[0]?._demo;

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

  const fetchMyTasks = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.listMyWorkItems(userId);
      setItems(response.data || []);
    } catch (err) {
      setError('获取任务列表失败');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { fetchMyTasks(); }, [fetchMyTasks]);

  // ── Handlers ──

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
    await fetchMyTasks();
    setWorkflowRefreshSignal(n => n + 1);
  };

  const getTypeCode = (type: string): WorkflowTypeCode =>
    type === 'TEST_CASE' ? 'TEST_CASE' : 'REQUIREMENT';

  // ── Plan task handlers ──

  const updatePlanTaskStatus = useCallback((taskId: string, status: PlanTask['status']) => {
    setPlanTasks(prev => prev.map(t => t.id === taskId ? { ...t, status } : t));
  }, []);

  const handleOpenResultModal = useCallback((task: PlanTask) => {
    setResultModalTask(task);
  }, []);

  const handleCloseResultModal = useCallback(() => {
    setResultModalTask(null);
  }, []);

  const handleSubmitResult = useCallback((taskId: string, result: PlanTaskResult) => {
    setPlanTasks(prev => prev.map(t =>
      t.id === taskId
        ? { ...t, status: 'done', result }
        : t,
    ));
  }, []);

  const handleOpenDispatchModal = useCallback((task: PlanTask) => {
    setDispatchModal({ open: true, caseId: task.caseId, caseTitle: task.caseTitle });
  }, []);

  const handleCloseDispatchModal = useCallback(() => {
    setDispatchModal({ open: false, caseId: '', caseTitle: '' });
  }, []);

  const handleDispatchSuccess = useCallback(() => {
    // Mark the dispatched case as running
    setPlanTasks(prev => prev.map(t =>
      t.caseId === dispatchModal.caseId ? { ...t, status: 'running' } : t,
    ));
  }, [dispatchModal.caseId]);

  const handleOpenBatchDispatch = useCallback(() => {
    setBatchOpen(true);
  }, []);

  const handleCloseBatchDispatch = useCallback(() => {
    setBatchOpen(false);
  }, []);

  const handleBatchSubmit = useCallback((caseIds: string[]) => {
    // Mark all selected cases as running
    setPlanTasks(prev => prev.map(t =>
      caseIds.includes(t.caseId) ? { ...t, status: 'running' } : t,
    ));
  }, []);

  return (
    <div className="page-content">
      <PageToolbar
        meta={(
          <>
            <StatPill label="待处理" value={items.length + displayPlanTasks.filter(t => t.status !== 'done').length} />
            <StatPill label="用户" value={userId} tone="info" />
          </>
        )}
        actions={(
          <button type="button" className="btn btn--secondary btn--sm" onClick={fetchMyTasks} disabled={loading}>
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

      {loading ? (
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
              isDemo={isDemo}
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
