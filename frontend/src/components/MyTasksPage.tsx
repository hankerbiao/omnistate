import React, { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { queryKeys } from '../providers/queryKeys';
import { getErrorMessage } from '../utils/errors';
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
import { transformApiItem, groupBadgeStyle, myTasksStyles, type PlanTask, type PlanTaskResult } from './myTasksTypes';
import CreateTestCaseForm from './CreateTestCaseForm';


interface MyTasksPageProps {
  userId: string;
}

const MyTasksPage: React.FC<MyTasksPageProps> = ({ userId }) => {
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [itemDetail, setItemDetail] = useState<RequirementResponse | TestCaseResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [workflowRefreshSignal, setWorkflowRefreshSignal] = useState(0);
  const [mutationError, setMutationError] = useState<string | null>(null);

  // Modal state: which task is being edited for result backfill
  const [resultModalTask, setResultModalTask] = useState<PlanTask | null>(null);

  // Single dispatch modal state
  const [dispatchModal, setDispatchModal] = useState<{
    open: boolean; itemId: string; caseId: string; caseTitle: string;
  }>({ open: false, itemId: '', caseId: '', caseTitle: '' });

  // Batch dispatch modal state
  const [batchOpen, setBatchOpen] = useState(false);

  // Edit test case modal state (for testcase_dev items in DEVELOPING state)
  const [editingTestCase, setEditingTestCase] = useState<TestCaseResponse | null>(null);

  // Requirement test cases (shown in expanded detail)
  const [reqTestCases, setReqTestCases] = useState<TestCaseResponse[]>([]);
  const [loadingReqTestCases, setLoadingReqTestCases] = useState(false);
  const [showCreateReqTestCase, setShowCreateReqTestCase] = useState(false);
  const [creatingReqTestCaseReqId, setCreatingReqTestCaseReqId] = useState<string | null>(null);

  // ── React Query: Work items ──

  const {
    data: workItems = [],
    isLoading: workItemsLoading,
    error: workItemsError,
  } = useQuery({
    queryKey: queryKeys.workItems.my(userId),
    queryFn: async () => (await api.listMyWorkItems(userId)).data || [],
    enabled: !!userId,
  });

  // ── React Query: Plan items ──

  const {
    data: planTasks = [],
    isLoading: planItemsLoading,
    error: planItemsError,
  } = useQuery({
    queryKey: queryKeys.planItems.my(userId),
    queryFn: async () => (await api.listMyPlanItems(userId)).data?.map(transformApiItem) || [],
    enabled: !!userId,
  });

  const autoTasksForDispatch = useMemo(
    () => planTasks.filter(t => t.type === 'auto' && t.status !== 'done'),
    [planTasks],
  );

  // ── 按四种类型归类工作流事项 ──

  type TaskCategory = 'review' | 'requirement' | 'testcase_dev' | 'plan_task';

  interface TaskCategoryGroup {
    key: TaskCategory;
    label: string;
    typeLabel: string;
    color: string;
    items: WorkItem[];
  }

  const categories = useMemo<TaskCategoryGroup[]>(() => {
    // (1) 审核相关 — 待审核状态的事项
    const reviewItems = workItems.filter(
      it => it.current_state === 'PENDING_REVIEW',
    );
    // (2) 测试需求管理 — REQUIREMENT 中非审核中的
    const reqItems = workItems.filter(
      it => it.type_code === 'REQUIREMENT' && it.current_state !== 'PENDING_REVIEW',
    );
    // (3) 测试用例开发 — TEST_CASE 中非审核中的
    const tcItems = workItems.filter(
      it => it.type_code === 'TEST_CASE' && it.current_state !== 'PENDING_REVIEW',
    );

    const result: TaskCategoryGroup[] = [];

    if (planTasks.length > 0) {
      result.push({
        key: 'plan_task', label: '测试任务执行', typeLabel: '执行', color: '#39d0d6',
        items: [],
      });
    }
    if (reviewItems.length > 0) {
      result.push({
        key: 'review', label: '审核相关', typeLabel: '审核', color: '#f0883e',
        items: reviewItems,
      });
    }
    if (reqItems.length > 0) {
      result.push({
        key: 'requirement', label: '测试用例编写需求管理', typeLabel: '需求', color: '#58a6ff',
        items: reqItems,
      });
    }
    if (tcItems.length > 0) {
      result.push({
        key: 'testcase_dev', label: '测试用例开发', typeLabel: '开发', color: '#a371f7',
        items: tcItems,
      });
    }
    return result;
  }, [workItems, planTasks]);

  // ── Refresh all ──

  const handleRefreshAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: queryKeys.workItems.my(userId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.planItems.my(userId) });
  }, [queryClient, userId]);

  // ── Workflow item handlers ──

  const loadItemDetail = async (item: WorkItem) => {
    setLoadingDetail(true);
    setItemDetail(null);
    setReqTestCases([]);
    try {
      if (item.type_code === 'REQUIREMENT' && item.req_id) {
        const res = await api.getRequirement(item.req_id);
        setItemDetail(res.data);
        // 同时加载该需求下的测试用例
        setLoadingReqTestCases(true);
        try {
          const tcRes = await api.listTestCases({ ref_req_id: item.req_id, limit: 50 });
          setReqTestCases(tcRes.data || []);
        } catch { /* ignore */ }
        setLoadingReqTestCases(false);
      } else if (item.type_code === 'TEST_CASE') {
        if (item.case_id) {
          const res = await api.getTestCase(item.case_id);
          setItemDetail(res.data);
        }
      }
    } catch { /* ignore */ } finally { setLoadingDetail(false); }
  };

  const handleToggleExpand = async (itemId: string) => {
    if (expandedId === itemId) { setExpandedId(null); setItemDetail(null); return; }
    setExpandedId(itemId);
    const item = workItems.find(i => i.item_id === itemId);
    if (item) await loadItemDetail(item);
  };

  const handleTaskWorkflowSuccess = async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.workItems.my(userId) });
    setWorkflowRefreshSignal(n => n + 1);
  };

  const getTypeCode = (type: string): WorkflowTypeCode =>
    type === 'TEST_CASE' ? 'TEST_CASE' : 'REQUIREMENT';

  // ── React Query: Update plan task status with archive mutation ──

  const archiveMutation = useMutation({
    mutationFn: async ({ taskId, planId, status }: { taskId: string; planId: string; status: PlanTask['status'] }) => {
      await api.updatePlanItem(planId, taskId, { status });
      if (status === 'done' || status === 'fail') {
        await api.archiveItem(taskId);
      }
    },
    onMutate: async ({ taskId, status, planId }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.planItems.my(userId) });
      const previousPlanTasks = queryClient.getQueryData<PlanTask[]>(queryKeys.planItems.my(userId));
      queryClient.setQueryData<PlanTask[]>(queryKeys.planItems.my(userId), old =>
        status === 'done' || status === 'fail'
          ? old?.filter(t => t.id !== taskId)
          : old?.map(t => t.id === taskId ? { ...t, status } : t)
      );
      return { previousPlanTasks };
    },
    onError: (err, variables, context) => {
      if (context?.previousPlanTasks) {
        queryClient.setQueryData(queryKeys.planItems.my(userId), context.previousPlanTasks);
      }
      setMutationError(getErrorMessage(err, '更新失败'));
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.planItems.my(userId) });
    },
  });

  const updatePlanTaskStatusWithArchive = useCallback((taskId: string, planId: string, status: PlanTask['status']) => {
    archiveMutation.mutate({ taskId, planId, status });
  }, [archiveMutation]);

  const handleOpenResultModal = useCallback((task: PlanTask) => {
    setResultModalTask(task);
  }, []);

  const handleCloseResultModal = useCallback(() => {
    setResultModalTask(null);
  }, []);

  // ── React Query: Submit result mutation ──

  const submitResultMutation = useMutation({
    mutationFn: async ({ taskId, result }: { taskId: string; result: PlanTaskResult }) => {
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
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.planItems.my(userId) });
    },
    onError: (err) => {
      console.error('提交结果失败:', err);
      setMutationError(getErrorMessage(err, '提交结果失败'));
    },
  });

  const handleSubmitResult = useCallback((taskId: string, result: PlanTaskResult) => {
    submitResultMutation.mutate({ taskId, result });
  }, [submitResultMutation]);

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

  const handleDispatchSuccess = useCallback(() => {
    const { itemId } = dispatchModal;
    // 乐观更新本地状态为 running
    queryClient.setQueryData<PlanTask[]>(queryKeys.planItems.my(userId), old =>
      old?.map(t => t.id === itemId ? { ...t, status: 'running' } : t)
    );
    // 刷新列表
    queryClient.invalidateQueries({ queryKey: queryKeys.planItems.my(userId) });
  }, [queryClient, userId, dispatchModal]);

  const handleOpenBatchDispatch = useCallback(() => {
    setBatchOpen(true);
  }, []);

  const handleCloseBatchDispatch = useCallback(() => {
    setBatchOpen(false);
  }, []);

  const handleEditTestCase = useCallback(async (item: WorkItem) => {
    if (!item.case_id) {
      setMutationError('该工作项未关联测试用例，无法编辑');
      return;
    }
    try {
      const res = await api.getTestCase(item.case_id);
      setEditingTestCase(res.data);
    } catch {
      setMutationError('获取测试用例详情失败');
    }
  }, []);

  // ── React Query: Batch dispatch mutation ──

  const batchDispatchMutation = useMutation({
    mutationFn: async (caseIds: string[]) => {
      const currentTasks = queryClient.getQueryData<PlanTask[]>(queryKeys.planItems.my(userId)) || [];
      const itemIds = currentTasks
        .filter(t => caseIds.includes(t.caseId))
        .map(t => t.id);

      if (itemIds.length === 0) return;

      await api.batchDispatchPlanItems({ item_ids: itemIds });
    },
    onMutate: async (caseIds) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.planItems.my(userId) });
      const previousPlanTasks = queryClient.getQueryData<PlanTask[]>(queryKeys.planItems.my(userId));
      // 乐观更新
      queryClient.setQueryData<PlanTask[]>(queryKeys.planItems.my(userId), old =>
        old?.map(t => caseIds.includes(t.caseId) ? { ...t, status: 'running' } : t)
      );
      return { previousPlanTasks };
    },
    onError: (err, caseIds, context) => {
      if (context?.previousPlanTasks) {
        queryClient.setQueryData(queryKeys.planItems.my(userId), context.previousPlanTasks);
      }
      setMutationError(getErrorMessage(err, '批量下发失败'));
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.planItems.my(userId) });
    },
  });

  const handleBatchSubmit = useCallback((caseIds: string[]) => {
    batchDispatchMutation.mutate(caseIds);
  }, [batchDispatchMutation]);

  // ── Pending count for stats ──
  const pendingCount = useMemo(() => {
    const workflowPending = workItems.filter(
      item => item.current_state && !['RELEASED', 'DONE', 'CLOSED', 'ARCHIVED'].includes(item.current_state),
    ).length;
    const planPending = planTasks.filter(t => t.status !== 'done').length;
    return workflowPending + planPending;
  }, [workItems, planTasks]);

  // ── Error display ──
  const displayWorkItemsError = workItemsError ? '获取工作流任务列表失败' : null;
  const displayPlanItemsError = planItemsError ? '获取计划任务列表失败' : null;

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
          <button type="button" className="btn btn--secondary btn--sm" onClick={handleRefreshAll} disabled={workItemsLoading || planItemsLoading}>
            刷新
          </button>
        )}
      />

      <div className="info-banner">
        我的任务汇总了工作流指派和执行计划分配的待办事项。
        计划任务可直接回填测试结果。
      </div>

      {displayWorkItemsError && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          {displayWorkItemsError}
        </div>
      )}

      {displayPlanItemsError && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          {displayPlanItemsError}
        </div>
      )}

      {mutationError && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          {mutationError} <button type="button" className="btn btn--ghost btn--sm" onClick={() => setMutationError(null)}>×</button>
        </div>
      )}

      {workItemsLoading && planItemsLoading ? (
        <div className="loading-overlay"><div className="loading-spinner" /></div>
      ) : workItems.length === 0 && planTasks.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">✅</div>
          <p className="empty-state__text">暂无待处理的任务</p>
        </div>
      ) : (
        <div style={myTasksStyles.list}>
          {/* ── Plan Tasks ── */}
          {planTasks.length > 0 && (
            <PlanTaskTable
              planTasks={planTasks}
              isDemo={false}
              hasAutoCasesForDispatch={autoTasksForDispatch.length > 0}
              onStatusUpdate={updatePlanTaskStatusWithArchive}
              onOpenResultModal={handleOpenResultModal}
              onOpenDispatchModal={handleOpenDispatchModal}
              onBatchDispatch={handleOpenBatchDispatch}
            />
          )}

          {/* ── Workflow items by category ── */}
          {categories.map(cat => (
            <div key={cat.key} style={myTasksStyles.group}>
              <div style={myTasksStyles.groupHeader}>
                <span style={groupBadgeStyle({ bg: `${cat.color}18`, color: cat.color })}>
                  {cat.label}
                </span>
                <span style={myTasksStyles.groupCount}>{cat.items.length} 项</span>
              </div>
              {cat.items.map(item => {
                const isExpanded = expandedId === item.item_id;
                const typeCode = getTypeCode(item.type_code);
                return (
                  <div key={item.item_id}>
                    <div onClick={() => { void handleToggleExpand(item.item_id); }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px',
                        borderBottom: '0.5px solid var(--border-subtle)',
                        cursor: 'pointer', fontSize: 13, transition: 'background 0.1s',
                        background: isExpanded
                          ? 'color-mix(in srgb, var(--accent-primary) 4%, transparent)'
                          : undefined,
                      }}
                    >
                      <span style={{
                        fontSize: 9, color: isExpanded ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                        transition: 'transform 0.15s', transform: isExpanded ? 'rotate(90deg)' : 'none',
                        flexShrink: 0,
                      }}>▶</span>
                      <span style={{
                        flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap', fontWeight: isExpanded ? 600 : 500,
                      }}>{item.title}</span>
                      <span className="status-badge" style={{
                        ...getWorkflowStateStyle(item.current_state),
                        fontSize: 10, padding: '2px 8px', flexShrink: 0,
                      }}>{getStateLabel(item.current_state, typeCode)}</span>
                      <span style={{
                        fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', flexShrink: 0,
                      }}>
                        {new Date(item.updated_at).toLocaleString('zh-CN', {
                          month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
                        })}
                      </span>
                      {item.type_code === 'TEST_CASE' && (item.current_state === 'ASSIGNED' || item.current_state === 'DEVELOPING') && (
                        <button
                          type="button"
                          className="btn btn--primary btn--sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            void handleEditTestCase(item);
                          }}
                          style={{ fontSize: 10, padding: '2px 8px', flexShrink: 0 }}
                        >
                          编辑
                        </button>
                      )}
                      {item.type_code === 'REQUIREMENT' && item.current_state === 'DEVELOPING' && (
                        <button
                          type="button"
                          className="btn btn--primary btn--sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            void handleToggleExpand(item.item_id);
                          }}
                          style={{ fontSize: 10, padding: '2px 8px', flexShrink: 0 }}
                        >
                          编写
                        </button>
                      )}
                      <WorkflowActionToolbar
                        workflowItemId={item.item_id}
                        typeCode={typeCode}
                        defaultPriority={itemDetail && 'priority' in itemDetail ? String(itemDetail.priority || '') : ''}
                        onTransitionSuccess={handleTaskWorkflowSuccess}
                        compact
                        hideActions={item.type_code === 'TEST_CASE' ? ['START_WRITE'] : undefined}
                      />
                    </div>
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
                            {item.type_code === 'REQUIREMENT' && itemDetail && 'req_id' in itemDetail ? (
                              /* ── 需求详情 ── 两栏布局 ── */
                              <>
                                {/* 顶部元信息行 */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 12 }}>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>优先级 & 状态</div>
                                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                      <span style={{
                                        padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600,
                                        backgroundColor: itemDetail.priority === 'P0' ? '#fef2f2' : itemDetail.priority === 'P1' ? '#fffbeb' : '#f1f5f9',
                                        color: itemDetail.priority === 'P0' ? '#dc2626' : itemDetail.priority === 'P1' ? '#d97706' : '#64748b',
                                      }}>{itemDetail.priority || 'P2'}</span>
                                      <span style={{ ...getWorkflowStateStyle(item.current_state), padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>
                                        {getStateLabel(item.current_state, 'REQUIREMENT')}
                                      </span>
                                    </div>
                                  </div>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>分类 & 来源</div>
                                    <div style={{ display: 'flex', gap: 6 }}>
                                      {itemDetail.category && <span style={{ padding: '2px 8px', fontSize: 12, borderRadius: 4, background: '#e2e8f0' }}>{itemDetail.category}</span>}
                                      {itemDetail.source && <span style={{ padding: '2px 8px', fontSize: 12, borderRadius: 4, background: '#e2e8f0' }}>{itemDetail.source}</span>}
                                    </div>
                                  </div>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>计划时间</div>
                                    <div style={{ fontSize: 12 }}>
                                      {itemDetail.planned_start_date || itemDetail.planned_end_date
                                        ? `${itemDetail.planned_start_date || '?'} ~ ${itemDetail.planned_end_date || '?'}`
                                        : <span style={{ color: '#94a3b8' }}>未设置</span>}
                                    </div>
                                  </div>
                                </div>

                                {/* 中间两栏：人员 + 标签 | 描述 */}
                                <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 12, marginBottom: 12 }}>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                      <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>人员</div>
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: 12, color: '#475569' }}>
                                        {itemDetail.tpm_owner_name && <span>👤 TPM: {itemDetail.tpm_owner_name}</span>}
                                        {itemDetail.manual_dev_name && <span>✏️ 手动: {itemDetail.manual_dev_name}</span>}
                                        {itemDetail.auto_dev_name && <span>🤖 自动: {itemDetail.auto_dev_name}</span>}
                                        {itemDetail.creator_name && <span>📋 创建: {itemDetail.creator_name}</span>}
                                      </div>
                                    </div>
                                    {itemDetail.tags && itemDetail.tags.length > 0 && (
                                      <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                        <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>标签</div>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                          {itemDetail.tags.map((tag: string) => (
                                            <span key={tag} style={{ padding: '2px 8px', fontSize: 11, borderRadius: 999, background: '#eff6ff', color: '#3b82f6' }}>{tag}</span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    {itemDetail.description && (
                                      <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                        <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>需求描述</div>
                                        <div style={{ whiteSpace: 'pre-wrap', fontSize: 12, color: '#475569', lineHeight: 1.6, maxHeight: 160, overflowY: 'auto' }}>{itemDetail.description}</div>
                                      </div>
                                    )}
                                    {itemDetail.acceptance_criteria && (
                                      <div style={{ background: '#f0fdf4', borderRadius: 8, padding: '10px 12px', border: '1px solid #bbf7d0' }}>
                                        <div style={{ fontSize: 10, fontWeight: 600, color: '#16a34a', marginBottom: 6 }}>✅ 验收标准</div>
                                        <div style={{ whiteSpace: 'pre-wrap', fontSize: 12, color: '#15803d', lineHeight: 1.6 }}>{itemDetail.acceptance_criteria}</div>
                                      </div>
                                    )}
                                  </div>
                                </div>

                                {/* 底部：测试用例 */}
                                <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                                    <span style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                                      关联测试用例 ({reqTestCases.length})
                                    </span>
                                    <button type="button" className="btn btn--primary btn--sm"
                                      onClick={(e) => { e.stopPropagation(); if (item.req_id) { setCreatingReqTestCaseReqId(item.req_id); setShowCreateReqTestCase(true); } }}
                                      style={{ fontSize: 10, padding: '2px 8px' }}
                                    >+ 创建用例</button>
                                  </div>
                                  {loadingReqTestCases ? (
                                    <div style={myTasksStyles.loadingSmall}><div className="loading-spinner" style={{ width: 16, height: 16 }} /></div>
                                  ) : reqTestCases.length > 0 ? (
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                                      {reqTestCases.map(tc => (
                                        <div key={tc.case_id} style={{ fontSize: 12, color: '#475569', padding: '6px 10px', background: '#fff', borderRadius: 6, border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: 8 }}>
                                          <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#94a3b8', whiteSpace: 'nowrap' }}>{tc.case_id}</span>
                                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tc.title}</span>
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <p style={{ fontSize: 12, color: '#94a3b8', fontStyle: 'italic' }}>暂无测试用例</p>
                                  )}
                                </div>
                              </>
                            ) : (
                              /* ── 其他类型（TEST_CASE）的预览 ── */
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                {item.content && <p style={myTasksStyles.contentPreview}>{item.content}</p>}
                                {itemDetail && 'description' in itemDetail && itemDetail.description && (
                                  <p style={myTasksStyles.contentPreview}>{itemDetail.description}</p>
                                )}
                              </div>
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
          ))}
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

      {/* ════════════════════════════════════════════════════════ */}
      {/*  Edit Test Case Modal (编写中的测试用例)               */}
      {/* ════════════════════════════════════════════════════════ */}
      {editingTestCase && (
        <CreateTestCaseForm
          editTestCase={editingTestCase}
          onClose={() => setEditingTestCase(null)}
          onSuccess={() => {
            setEditingTestCase(null);
            handleTaskWorkflowSuccess();
          }}
          lockRequirementId
        />
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/*  Create Test Case from Requirement Modal               */}
      {/* ════════════════════════════════════════════════════════ */}
      {showCreateReqTestCase && creatingReqTestCaseReqId && (
        <CreateTestCaseForm
          onClose={() => { setShowCreateReqTestCase(false); setCreatingReqTestCaseReqId(null); }}
          onSuccess={() => {
            setShowCreateReqTestCase(false);
            setCreatingReqTestCaseReqId(null);
            handleTaskWorkflowSuccess();
            // 重新加载测试用例列表
            if (creatingReqTestCaseReqId) {
              setLoadingReqTestCases(true);
              api.listTestCases({ ref_req_id: creatingReqTestCaseReqId, limit: 50 })
                .then(res => setReqTestCases(res.data || []))
                .catch(() => {})
                .finally(() => setLoadingReqTestCases(false));
            }
          }}
          defaultRequirementId={creatingReqTestCaseReqId}
          lockRequirementId
          defaultLabId=""
          defaultCatalogPrefix={[]}
        />
      )}
    </div>
  );
};

export default MyTasksPage;
