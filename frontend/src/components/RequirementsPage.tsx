import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import type { RequirementResponse, TestCaseResponse, WorkflowTransition } from '../types';
import CreateRequirementForm from './CreateRequirementForm';
import CreateTestCaseForm from './CreateTestCaseForm';
import TestCaseDetailModal from './TestCaseDetailModal';
import RequirementDetailModal from './RequirementDetailModal';

type ActiveTab = 'workflow' | 'testcases';

// 需求/用例状态中文映射
const STATUS_LABELS: Record<string, string> = {
  DRAFT: '草稿',
  PENDING_REVIEW: '待审核',
  PENDING_DEVELOP: '待开发',
  DEVELOPING: '开发中',
  PENDING_TEST: '待测试',
  PENDING_UAT: '待验收',
  PENDING_RELEASE: '待发布',
  RELEASED: '已发布',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  CLOSED: '已关闭',
  ACTIVE: '激活',
  INACTIVE: '未激活',
  DEPRECATED: '已弃用',
  ASSIGNED: '已指派',
  DEVELOPING: '编写中',
  DONE: '已完成',
};

const RequirementsPage: React.FC = () => {
  const [requirements, setRequirements] = useState<RequirementResponse[]>([]);
  const [testCases, setTestCases] = useState<TestCaseResponse[]>([]);
  const [loadingRequirements, setLoadingRequirements] = useState(false);
  const [loadingTestCases, setLoadingTestCases] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRequirementId, setSelectedRequirementId] = useState<string | null>(null);
  const [showCreateRequirement, setShowCreateRequirement] = useState(false);
  const [showCreateTestCase, setShowCreateTestCase] = useState(false);
  const [selectedTestCase, setSelectedTestCase] = useState<TestCaseResponse | null>(null);
  const [editingTestCase, setEditingTestCase] = useState<TestCaseResponse | null>(null);
  const [workflowState, setWorkflowState] = useState<string>('');
  const [workflowTransitions, setWorkflowTransitions] = useState<WorkflowTransition[]>([]);
  const [loadingWorkflow, setLoadingWorkflow] = useState(false);
  const [transitioningAction, setTransitioningAction] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('workflow');
  const [transitionModal, setTransitionModal] = useState<{ open: boolean; transition?: WorkflowTransition }>({ open: false });
  const [transitionFormData, setTransitionFormData] = useState<Record<string, string>>({});
  const [ownerSuggestions, setOwnerSuggestions] = useState<{ user_id: string; username: string }[]>([]);
  const [ownerSearchQuery, setOwnerSearchQuery] = useState('');
  const [showOwnerDropdown, setShowOwnerDropdown] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ open: boolean; reqId?: string; title?: string }>({ open: false });
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState(false);
  const [deleteCaseConfirm, setDeleteCaseConfirm] = useState<{ open: boolean; caseId?: string; title?: string }>({ open: false });
  const [selectedRequirementDetail, setSelectedRequirementDetail] = useState<RequirementResponse | null>(null);
  const [workflowTestCase, setWorkflowTestCase] = useState<TestCaseResponse | null>(null);
  const [caseWorkflowState, setCaseWorkflowState] = useState('');
  const [caseWorkflowTransitions, setCaseWorkflowTransitions] = useState<WorkflowTransition[]>([]);
  const [loadingCaseWorkflow, setLoadingCaseWorkflow] = useState(false);
  const [transitionContext, setTransitionContext] = useState<{
    workflowItemId: string;
    refresh: () => Promise<void>;
  } | null>(null);

  const selectedRequirement = useMemo(
    () => requirements.find((item) => item.req_id === selectedRequirementId) || null,
    [requirements, selectedRequirementId],
  );

  const fetchRequirements = useCallback(async (nextSelectedId?: string) => {
    setLoadingRequirements(true);
    setError(null);

    try {
      const response = await api.listRequirements({ limit: 50 });
      const data = response.data || [];
      setRequirements(data);

      setSelectedRequirementId((current) => {
        const preferred = nextSelectedId || current;
        if (preferred && data.some((item) => item.req_id === preferred)) {
          return preferred;
        }
        return data[0]?.req_id || null;
      });
    } catch (err) {
      setError('获取需求列表失败');
      console.error('Fetch requirements error:', err);
    } finally {
      setLoadingRequirements(false);
    }
  }, []);

  const fetchTestCases = useCallback(async (requirementId: string) => {
    setLoadingTestCases(true);
    setError(null);

    try {
      const response = await api.listTestCases({ ref_req_id: requirementId, limit: 50 });
      setTestCases(response.data || []);
    } catch (err) {
      setError('获取测试用例失败');
      console.error('Fetch test cases error:', err);
    } finally {
      setLoadingTestCases(false);
    }
  }, []);

  const fetchWorkflowTransitions = useCallback(async (workflowItemId: string) => {
    setLoadingWorkflow(true);
    try {
      const response = await api.getWorkflowTransitions(workflowItemId);
      setWorkflowState(response.data.current_state);
      setWorkflowTransitions(response.data.available_transitions || []);
    } catch (err) {
      setWorkflowState('');
      setWorkflowTransitions([]);
      setError('获取工作流信息失败');
      console.error('Fetch workflow transitions error:', err);
    } finally {
      setLoadingWorkflow(false);
    }
  }, []);

  const fetchCaseWorkflow = useCallback(async (workflowItemId: string) => {
    setLoadingCaseWorkflow(true);
    try {
      const response = await api.getWorkflowTransitions(workflowItemId);
      setCaseWorkflowState(response.data.current_state);
      setCaseWorkflowTransitions(response.data.available_transitions || []);
    } catch (err) {
      setCaseWorkflowState('');
      setCaseWorkflowTransitions([]);
      setError('获取测试用例工作流失败');
      console.error('Fetch test case workflow error:', err);
    } finally {
      setLoadingCaseWorkflow(false);
    }
  }, []);

  // 搜索用户作为目标处理人
  const searchUsers = useCallback(async (query: string) => {
    if (!query.trim()) {
      // 无搜索词时加载所有用户
      try {
        const response = await api.listUsers({ limit: 50 });
        setOwnerSuggestions(response.data || []);
      } catch (err) {
        console.error('Search users error:', err);
      }
      return;
    }

    try {
      const response = await api.listUsers({ search: query, limit: 20 });
      setOwnerSuggestions(response.data || []);
    } catch (err) {
      console.error('Search users error:', err);
    }
  }, []);

  // 选择目标用户
  const handleSelectOwner = useCallback((user: { user_id: string; username: string }) => {
    setTransitionFormData(prev => ({ ...prev, target_owner_id: user.user_id }));
    setOwnerSearchQuery(user.username);
    setShowOwnerDropdown(false);
  }, []);

  useEffect(() => {
    fetchRequirements();
  }, [fetchRequirements]);

  useEffect(() => {
    if (!selectedRequirementId) {
      setTestCases([]);
      setWorkflowTestCase(null);
      return;
    }
    fetchTestCases(selectedRequirementId);
    setWorkflowTestCase(null);
  }, [fetchTestCases, selectedRequirementId]);

  useEffect(() => {
    if (!selectedRequirement?.workflow_item_id) {
      setWorkflowState('');
      setWorkflowTransitions([]);
      return;
    }
    fetchWorkflowTransitions(selectedRequirement.workflow_item_id);
  }, [fetchWorkflowTransitions, selectedRequirement?.workflow_item_id]);

  useEffect(() => {
    if (!workflowTestCase?.workflow_item_id) {
      setCaseWorkflowState('');
      setCaseWorkflowTransitions([]);
      return;
    }
    fetchCaseWorkflow(workflowTestCase.workflow_item_id);
  }, [fetchCaseWorkflow, workflowTestCase?.workflow_item_id, workflowTestCase?.case_id]);

  useEffect(() => {
    if (!workflowTestCase?.case_id) return;
    const updated = testCases.find((item) => item.case_id === workflowTestCase.case_id);
    if (updated && updated.status !== workflowTestCase.status) {
      setWorkflowTestCase(updated);
    }
  }, [testCases, workflowTestCase?.case_id, workflowTestCase?.status]);

  const handleRequirementCreated = (requirement: RequirementResponse) => {
    fetchRequirements(requirement.req_id);
  };

  const handleTestCaseCreated = () => {
    if (selectedRequirementId) {
      fetchTestCases(selectedRequirementId);
    }
  };

  const selectTestCaseForWorkflow = useCallback(async (testCase: TestCaseResponse) => {
    setWorkflowTestCase(testCase);
    if (testCase.workflow_item_id) {
      return;
    }
    try {
      const response = await api.getTestCase(testCase.case_id);
      if (response.data?.workflow_item_id) {
        setWorkflowTestCase(response.data);
      }
    } catch (err) {
      console.error('Fetch test case detail for workflow error:', err);
    }
  }, []);

  const getPriorityStyle = (priority: string) => {
    const styleMap: Record<string, { bg: string; color: string }> = {
      P0: { bg: 'var(--status-error-bg)', color: 'var(--status-error)' },
      P1: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
      P2: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      P3: { bg: 'var(--surface-tertiary)', color: 'var(--text-tertiary)' },
    };
    return styleMap[priority] || { bg: 'var(--surface-tertiary)', color: 'var(--text-secondary)' };
  };

  const getWorkflowStateStyle = (state: string) => {
    const styleMap: Record<string, { bg: string; color: string }> = {
      DRAFT: { bg: 'var(--surface-tertiary)', color: 'var(--text-tertiary)' },
      ASSIGNED: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      PENDING_REVIEW: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
      PENDING_DEVELOP: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      DEVELOPING: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      PENDING_TEST: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      PENDING_UAT: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      PENDING_RELEASE: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
      RELEASED: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
      DONE: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
    };
    return styleMap[state] || { bg: 'var(--surface-tertiary)', color: 'var(--text-secondary)' };
  };

  const getActionLabel = (action: string) => {
    const labelMap: Record<string, string> = {
      SUBMIT: '提交评审',
      APPROVE: '通过',
      REJECT: '驳回',
      START: '开始开发',
      FINISH: '完成开发',
      PASS: '通过',
      PUBLISH: '发布',
      ASSIGN: '指派编写人',
      START_WRITE: '开始编写',
      SUBMIT_REVIEW: '提交评审',
    };
    return labelMap[action] || action;
  };

  const getFieldLabel = (field: string) => {
    const labelMap: Record<string, string> = {
      target_owner_id: '目标处理人',
      priority: '优先级',
      comment: '备注',
    };
    return labelMap[field] || field;
  };

  const openTransitionModal = (
    transition: WorkflowTransition,
    context: { workflowItemId: string; refresh: () => Promise<void> },
  ) => {
    const initialData: Record<string, string> = {};
    for (const field of transition.required_fields) {
      if (field === 'priority') {
        initialData[field] = selectedRequirement?.priority || workflowTestCase?.priority || '';
      } else if (field === 'target_owner_id') {
        initialData[field] = '';
        searchUsers('');
      }
    }
    setOwnerSearchQuery('');
    setTransitionFormData(initialData);
    setTransitionContext(context);
    setTransitionModal({ open: true, transition });
  };

  const handleTransitionSubmit = async () => {
    if (!transitionContext?.workflowItemId || !transitionModal.transition) return;

    for (const field of transitionModal.transition.required_fields) {
      if (!transitionFormData[field]?.trim()) {
        setError(`${getFieldLabel(field)}不能为空`);
        return;
      }
    }

    setTransitioningAction(transitionModal.transition.action);
    setError(null);
    try {
      await api.transitionWorkflow(transitionContext.workflowItemId, {
        action: transitionModal.transition.action,
        form_data: transitionFormData,
      });
      await transitionContext.refresh();
      setTransitionModal({ open: false });
      setTransitionContext(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '工作流流转失败');
      console.error('Workflow transition error:', err);
    } finally {
      setTransitioningAction(null);
    }
  };

  const refreshRequirementWorkflow = async () => {
    if (!selectedRequirement?.workflow_item_id || !selectedRequirement.req_id) return;
    await fetchRequirements(selectedRequirement.req_id);
    await fetchWorkflowTransitions(selectedRequirement.workflow_item_id);
  };

  const refreshTestCaseWorkflow = async () => {
    if (!selectedRequirementId || !workflowTestCase?.workflow_item_id) return;
    await fetchTestCases(selectedRequirementId);
    await fetchCaseWorkflow(workflowTestCase.workflow_item_id);
  };

  const onlineCount = requirements.filter(r => r.status === 'RELEASED').length;

  const handleDeleteRequirement = async () => {
    if (!deleteConfirm.reqId || !selectedRequirement?.workflow_item_id) return;

    setDeleting(true);
    setError(null);
    try {
      await api.deleteRequirement(deleteConfirm.reqId);
      setDeleteConfirm({ open: false });
      // 重新获取列表
      await fetchRequirements();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除需求失败');
      console.error('Delete requirement error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const openDeleteConfirm = (reqId: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirm({ open: true, reqId, title });
  };

  // 批量选择
  const toggleSelect = (reqId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(reqId)) {
        next.delete(reqId);
      } else {
        next.add(reqId);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === requirements.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(requirements.map(r => r.req_id)));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;

    setDeleting(true);
    setError(null);
    try {
      // 逐个删除
      const deletePromises = Array.from(selectedIds).map(id => api.deleteRequirement(id));
      await Promise.all(deletePromises);
      setBatchDeleteConfirm(false);
      setSelectedIds(new Set());
      await fetchRequirements();
    } catch (err) {
      setError(err instanceof Error ? err.message : '批量删除失败');
      console.error('Batch delete error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteTestCase = async () => {
    if (!deleteCaseConfirm.caseId || !selectedRequirementId) return;

    setDeleting(true);
    setError(null);
    try {
      await api.deleteTestCase(deleteCaseConfirm.caseId);
      setDeleteCaseConfirm({ open: false });
      await fetchTestCases(selectedRequirementId);
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除测试用例失败');
      console.error('Delete test case error:', err);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="workspace">
      {/* Left Panel - Requirements List */}
      <div style={styles.leftPanel}>
        <div style={styles.panelHeader}>
          <div>
            <h2 style={styles.panelTitle}>需求列表</h2>
            <span style={styles.panelHint}>
              {selectedIds.size > 0
                ? `已选择 ${selectedIds.size} 项`
                : `${requirements.length} 个需求，已发布 ${onlineCount}`}
            </span>
          </div>
          <div style={styles.panelActions}>
            {selectedIds.size > 0 && (
              <button
                className="btn btn--sm"
                style={{ backgroundColor: 'var(--status-error)', color: 'white' }}
                onClick={() => setBatchDeleteConfirm(true)}
              >
                删除 ({selectedIds.size})
              </button>
            )}
            <button className="btn btn--ghost btn--sm" onClick={() => fetchRequirements()} disabled={loadingRequirements}>
              ↻
            </button>
            <button className="btn btn--primary btn--sm" onClick={() => setShowCreateRequirement(true)}>
              + 新建
            </button>
          </div>
        </div>

        {loadingRequirements ? (
          <div className="loading-overlay">
            <div className="loading-spinner" />
          </div>
        ) : requirements.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon">📋</div>
            <p className="empty-state__text">暂无需求，点击上方"新建"创建</p>
          </div>
        ) : (
          <div style={styles.list}>
            {/* Select All Header */}
            <div style={styles.selectAllRow}>
              <label style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={selectedIds.size === requirements.length && requirements.length > 0}
                  onChange={toggleSelectAll}
                  style={styles.checkbox}
                />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>全选</span>
              </label>
            </div>
            {requirements.map((requirement) => {
              const priorityStyle = getPriorityStyle(requirement.priority);
              const isSelected = selectedRequirementId === requirement.req_id;
              const isChecked = selectedIds.has(requirement.req_id);
              return (
                <div
                  key={requirement.req_id}
                  className={`requirement-item ${isSelected ? 'requirement-item--selected' : ''} ${isChecked ? 'requirement-item--checked' : ''}`}
                  onClick={() => {
                    setSelectedRequirementId(requirement.req_id);
                    setSelectedRequirementDetail(requirement);
                  }}
                >
                  <div style={styles.itemHeader}>
                    <div style={styles.itemHeaderLeft}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelect(requirement.req_id)}
                        onClick={(e) => e.stopPropagation()}
                        style={styles.checkbox}
                      />
                      <span style={styles.itemId}>{requirement.req_id}</span>
                    </div>
                    <div style={styles.itemHeaderRight}>
                      <span
                        className="status-badge"
                        style={{ backgroundColor: priorityStyle.bg, color: priorityStyle.color }}
                      >
                        {requirement.priority}
                      </span>
                      <button
                        style={styles.deleteBtn}
                        onClick={(e) => openDeleteConfirm(requirement.req_id, requirement.title, e)}
                        title="删除"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  <div style={styles.itemTitle}>{requirement.title}</div>
                  <div style={styles.itemMeta}>
                    <span
                      className="status-badge status-badge--neutral"
                      style={{ fontSize: '10px' }}
                    >
                      {STATUS_LABELS[requirement.status] || requirement.status}
                    </span>
                    <span style={styles.metaTime}>
                      {new Date(requirement.created_at).toLocaleDateString('zh-CN')}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Right Panel - Detail Workspace */}
      <div style={styles.rightPanel}>
        {selectedRequirement ? (
          <>
            <div style={styles.detailHeader}>
              <div>
                <h2 style={styles.detailTitle}>{selectedRequirement.title}</h2>
                <div style={styles.detailMeta}>
                  <span className="mono" style={styles.detailId}>{selectedRequirement.req_id}</span>
                  <span
                    className="status-badge"
                    style={{
                      ...getWorkflowStateStyle(workflowState || selectedRequirement.status),
                    }}
                  >
                    {workflowState || selectedRequirement.status}
                  </span>
                  <span
                    className="status-badge"
                    style={getPriorityStyle(selectedRequirement.priority)}
                  >
                    {selectedRequirement.priority}
                  </span>
                </div>
                {selectedRequirement.description && (
                  <p style={styles.description}>{selectedRequirement.description}</p>
                )}
              </div>
            </div>

            {/* Tabs */}
            <div className="tabs">
              <button
                className={`tab ${activeTab === 'workflow' ? 'tab--active' : ''}`}
                onClick={() => setActiveTab('workflow')}
              >
                工作流
              </button>
              <button
                className={`tab ${activeTab === 'testcases' ? 'tab--active' : ''}`}
                onClick={() => setActiveTab('testcases')}
              >
                测试用例 ({testCases.length})
              </button>
            </div>

            {/* Tab Content */}
            <div style={styles.tabContent}>
              {activeTab === 'workflow' ? (
                <div className="data-panel">
                  {!selectedRequirement.workflow_item_id ? (
                    <div className="empty-state">
                      <div className="empty-state__icon">⚙</div>
                      <p className="empty-state__text">当前需求没有关联工作流</p>
                    </div>
                  ) : loadingWorkflow ? (
                    <div className="loading-overlay">
                      <div className="loading-spinner" />
                    </div>
                  ) : (
                    <>
                      <div className="data-panel-header">
                        <h3 className="data-panel-title">工作流状态</h3>
                      </div>
                      <div style={styles.workflowInfo}>
                        <div style={styles.workflowInfoItem}>
                          <span style={styles.workflowInfoLabel}>工作流ID</span>
                          <span style={styles.workflowInfoValue} className="mono">
                            {selectedRequirement.workflow_item_id}
                          </span>
                        </div>
                        <div style={styles.workflowInfoItem}>
                          <span style={styles.workflowInfoLabel}>当前状态</span>
                          <span
                            className="status-badge"
                            style={getWorkflowStateStyle(workflowState || selectedRequirement.status)}
                          >
                            {workflowState || selectedRequirement.status}
                          </span>
                        </div>
                        <div style={styles.workflowInfoItem}>
                          <span style={styles.workflowInfoLabel}>创建人</span>
                          <span style={styles.workflowInfoValue}>
                            {selectedRequirement.creator_name || selectedRequirement.creator || '-'}
                          </span>
                        </div>
                        <div style={styles.workflowInfoItem}>
                          <span style={styles.workflowInfoLabel}>当前负责人</span>
                          <span style={styles.workflowInfoValue}>
                            {selectedRequirement.current_owner_name || selectedRequirement.current_owner || '-'}
                          </span>
                        </div>
                        <div style={styles.workflowInfoItem}>
                          <span style={styles.workflowInfoLabel}>创建时间</span>
                          <span style={styles.workflowInfoValue}>
                            {selectedRequirement.created_at
                              ? new Date(selectedRequirement.created_at).toLocaleString('zh-CN')
                              : '-'}
                          </span>
                        </div>
                        <div style={styles.workflowInfoItem}>
                          <span style={styles.workflowInfoLabel}>更新时间</span>
                          <span style={styles.workflowInfoValue}>
                            {selectedRequirement.updated_at
                              ? new Date(selectedRequirement.updated_at).toLocaleString('zh-CN')
                              : '-'}
                          </span>
                        </div>
                      </div>

                      <div style={styles.workflowActions}>
                        <h4 style={styles.sectionTitle}>可用操作</h4>
                        {workflowTransitions.length === 0 ? (
                          <div className="empty-state" style={{ padding: '24px' }}>
                            <p className="empty-state__text">当前状态没有可执行的操作</p>
                          </div>
                        ) : (
                          <div style={styles.actionGrid}>
                            {workflowTransitions.map((transition) => (
                              <button
                                key={`${transition.action}-${transition.to_state}`}
                                className="btn btn--secondary"
                                onClick={() => openTransitionModal(transition, {
                                  workflowItemId: selectedRequirement.workflow_item_id!,
                                  refresh: refreshRequirementWorkflow,
                                })}
                                disabled={Boolean(transitioningAction)}
                              >
                                <span style={styles.actionName}>{getActionLabel(transition.action)}</span>
                                <span style={styles.actionArrow}>→ {STATUS_LABELS[transition.to_state] || transition.to_state}</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div className="data-panel">
                  <div className="data-panel-header">
                    <h3 className="data-panel-title">关联测试用例</h3>
                    <button
                      className="btn btn--primary btn--sm"
                      onClick={() => setShowCreateTestCase(true)}
                    >
                      + 创建用例
                    </button>
                  </div>

                  {loadingTestCases ? (
                    <div className="loading-overlay">
                      <div className="loading-spinner" />
                    </div>
                  ) : testCases.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-state__icon">🧪</div>
                      <p className="empty-state__text">暂无测试用例，点击上方按钮创建</p>
                    </div>
                  ) : (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th style={{ width: '120px' }}>用例ID</th>
                          <th>名称</th>
                          <th style={{ width: '60px' }}>优先级</th>
                          <th style={{ width: '80px' }}>状态</th>
                          <th style={{ width: '90px' }}>创建时间</th>
                          <th style={{ width: '120px' }}>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {testCases.map((testCase) => {
                          const isSelected = workflowTestCase?.case_id === testCase.case_id;
                          return (
                          <tr
                            key={testCase.id}
                            onClick={() => { void selectTestCaseForWorkflow(testCase); }}
                            style={{
                              cursor: 'pointer',
                              backgroundColor: isSelected ? 'var(--surface-hover)' : undefined,
                            }}
                          >
                            <td className="mono">{testCase.case_id}</td>
                            <td>{testCase.title}</td>
                            <td>
                              <span
                                className="status-badge status-badge--neutral"
                                style={getPriorityStyle(testCase.priority || 'P3')}
                              >
                                {testCase.priority || '-'}
                              </span>
                            </td>
                            <td>
                              <span
                                className="status-badge status-badge--neutral"
                                style={getWorkflowStateStyle(testCase.status)}
                              >
                                {STATUS_LABELS[testCase.status] || testCase.status}
                              </span>
                            </td>
                            <td className="mono">
                              {new Date(testCase.created_at).toLocaleDateString('zh-CN')}
                            </td>
                            <td>
                              <div style={styles.caseActionCell} onClick={(e) => e.stopPropagation()}>
                                <button
                                  type="button"
                                  style={styles.caseActionBtn}
                                  onClick={() => setSelectedTestCase(testCase)}
                                  title="详情"
                                >
                                  详情
                                </button>
                                <button
                                  type="button"
                                  style={styles.deleteBtn}
                                  onClick={() => {
                                    setDeleteCaseConfirm({ open: true, caseId: testCase.case_id, title: testCase.title });
                                  }}
                                  title="删除"
                                >
                                  ×
                                </button>
                              </div>
                            </td>
                          </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}

                  {workflowTestCase && (
                    <div style={styles.caseWorkflowPanel}>
                      <div className="data-panel-header">
                        <h3 className="data-panel-title">
                          用例流转 · {workflowTestCase.case_id}
                        </h3>
                        <span
                          className="status-badge"
                          style={getWorkflowStateStyle(caseWorkflowState || workflowTestCase.status)}
                        >
                          {STATUS_LABELS[caseWorkflowState || workflowTestCase.status]
                            || caseWorkflowState
                            || workflowTestCase.status}
                        </span>
                      </div>

                      {!workflowTestCase.workflow_item_id ? (
                        <p style={styles.caseWorkflowHint}>
                          {workflowTestCase.status === '未开始'
                            ? '该用例在数据库中未绑定工作流（多为历史数据）。请重新创建用例，或联系管理员执行数据修复。'
                            : '未能加载工作流 ID，请刷新页面后重试；若仍无效请重启后端服务。'}
                          <br />
                          <span style={styles.caseWorkflowHintSub}>
                            说明：与 admin 无关——流转权限认当前负责人，不认管理员角色。
                          </span>
                        </p>
                      ) : loadingCaseWorkflow ? (
                        <div className="loading-overlay" style={{ minHeight: '80px' }}>
                          <div className="loading-spinner" />
                        </div>
                      ) : caseWorkflowTransitions.length === 0 ? (
                        <p style={styles.caseWorkflowHint}>
                          当前状态没有您可执行的操作。测试用例流转认工作项的创建人/当前负责人，admin 角色本身不能代流转；若您刚指派了负责人，需由新负责人操作或先改派回自己。
                        </p>
                      ) : (
                        <div style={styles.actionGrid}>
                          {caseWorkflowTransitions.map((transition) => (
                            <button
                              key={`case-${transition.action}-${transition.to_state}`}
                              type="button"
                              className="btn btn--secondary"
                              onClick={() => openTransitionModal(transition, {
                                workflowItemId: workflowTestCase.workflow_item_id!,
                                refresh: refreshTestCaseWorkflow,
                              })}
                              disabled={Boolean(transitioningAction)}
                            >
                              <span style={styles.actionName}>{getActionLabel(transition.action)}</span>
                              <span style={styles.actionArrow}>
                                → {STATUS_LABELS[transition.to_state] || transition.to_state}
                              </span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="empty-state" style={{ height: '100%' }}>
            <div className="empty-state__icon">👈</div>
            <p className="empty-state__text">从左侧选择一条需求查看详情</p>
          </div>
        )}
      </div>

      {error && (
        <div style={styles.errorToast}>
          <span>⚠</span> {error}
          <button onClick={() => setError(null)} style={styles.errorClose}>×</button>
        </div>
      )}

      {showCreateRequirement && (
        <CreateRequirementForm
          onClose={() => setShowCreateRequirement(false)}
          onSuccess={handleRequirementCreated}
        />
      )}

      {showCreateTestCase && selectedRequirement && (
        <CreateTestCaseForm
          onClose={() => setShowCreateTestCase(false)}
          onSuccess={handleTestCaseCreated}
          defaultRequirementId={selectedRequirement.req_id}
          lockRequirementId
        />
      )}

      {selectedTestCase && (
        <TestCaseDetailModal
          testCase={selectedTestCase}
          onClose={() => setSelectedTestCase(null)}
          onEdit={() => {
            setEditingTestCase(selectedTestCase);
            setSelectedTestCase(null);
          }}
        />
      )}

      {editingTestCase && (
        <CreateTestCaseForm
          editTestCase={editingTestCase}
          onClose={() => setEditingTestCase(null)}
          onSuccess={handleTestCaseCreated}
          lockRequirementId
        />
      )}

      {selectedRequirementDetail && (
        <RequirementDetailModal
          requirement={selectedRequirementDetail}
          onClose={() => setSelectedRequirementDetail(null)}
        />
      )}

      {/* Transition Modal */}
      {transitionModal.open && transitionModal.transition && (
        <div className="modal-overlay" onClick={() => { setTransitionModal({ open: false }); setTransitionContext(null); }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">{getActionLabel(transitionModal.transition.action)}</h3>
              <button className="modal__close" onClick={() => { setTransitionModal({ open: false }); setTransitionContext(null); }}>×</button>
            </div>
            <div className="modal__body">
              <p style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: '13px' }}>
                状态将变为: <strong>{transitionModal.transition.to_state}</strong>
              </p>
              {transitionModal.transition.required_fields.map(field => (
                <div key={field} style={{ marginBottom: '16px' }}>
                  <label style={styles.formLabel}>{getFieldLabel(field)} *</label>
                  {field === 'priority' ? (
                    <select
                      className="form-input form-select"
                      value={transitionFormData[field] || ''}
                      onChange={e => setTransitionFormData({ ...transitionFormData, [field]: e.target.value })}
                    >
                      <option value="">请选择</option>
                      <option value="P0">P0 - 紧急</option>
                      <option value="P1">P1 - 高</option>
                      <option value="P2">P2 - 中</option>
                      <option value="P3">P3 - 低</option>
                    </select>
                  ) : field === 'target_owner_id' ? (
                    <div style={{ position: 'relative' }}>
                      <input
                        className="form-input"
                        type="text"
                        value={ownerSearchQuery}
                        onChange={e => {
                          setOwnerSearchQuery(e.target.value);
                          searchUsers(e.target.value);
                          setShowOwnerDropdown(true);
                        }}
                        onFocus={() => {
                          searchUsers(ownerSearchQuery);
                          setShowOwnerDropdown(true);
                        }}
                        placeholder="搜索用户..."
                        autoComplete="off"
                      />
                      {showOwnerDropdown && ownerSuggestions.length > 0 && (
                        <div style={styles.ownerDropdown}>
                          {ownerSuggestions.map(user => (
                            <div
                              key={user.user_id}
                              style={styles.ownerDropdownItem}
                              onClick={() => handleSelectOwner(user)}
                              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--surface-hover)')}
                              onMouseLeave={e => (e.currentTarget.style.backgroundColor = '')}
                            >
                              <span style={{ fontWeight: 500 }}>{user.username}</span>
                              <span style={styles.ownerId}>{user.user_id}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {showOwnerDropdown && ownerSuggestions.length === 0 && ownerSearchQuery && (
                        <div style={styles.ownerDropdown}>
                          <div style={{ ...styles.ownerDropdownItem, color: 'var(--text-tertiary)', cursor: 'default' }}>
                            未找到匹配用户
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <input
                      className="form-input"
                      type="text"
                      value={transitionFormData[field] || ''}
                      onChange={e => setTransitionFormData({ ...transitionFormData, [field]: e.target.value })}
                      placeholder={`请输入${getFieldLabel(field)}`}
                    />
                  )}
                </div>
              ))}
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => { setTransitionModal({ open: false }); setTransitionContext(null); }}>
                取消
              </button>
              <button
                className="btn btn--primary"
                onClick={handleTransitionSubmit}
                disabled={Boolean(transitioningAction)}
              >
                {transitioningAction ? '处理中...' : '确认'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {deleteConfirm.open && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm({ open: false })}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">确认删除</h3>
              <button className="modal__close" onClick={() => setDeleteConfirm({ open: false })}>×</button>
            </div>
            <div className="modal__body">
              <p style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>
                确定要删除需求 <strong>"{deleteConfirm.title}"</strong> 吗？
              </p>
              <p style={{ color: 'var(--status-error)', fontSize: '13px' }}>
                此操作不可恢复，相关测试用例也将一并删除。
              </p>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setDeleteConfirm({ open: false })}>
                取消
              </button>
              <button
                className="btn"
                style={{ backgroundColor: 'var(--status-error)', color: 'white' }}
                onClick={handleDeleteRequirement}
                disabled={deleting}
              >
                {deleting ? '删除中...' : '删除'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Delete Confirm Modal */}
      {batchDeleteConfirm && (
        <div className="modal-overlay" onClick={() => setBatchDeleteConfirm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">确认批量删除</h3>
              <button className="modal__close" onClick={() => setBatchDeleteConfirm(false)}>×</button>
            </div>
            <div className="modal__body">
              <p style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>
                确定要删除选中的 <strong>{selectedIds.size}</strong> 个需求吗？
              </p>
              <p style={{ color: 'var(--status-error)', fontSize: '13px' }}>
                此操作不可恢复，相关测试用例也将一并删除。
              </p>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setBatchDeleteConfirm(false)}>
                取消
              </button>
              <button
                className="btn"
                style={{ backgroundColor: 'var(--status-error)', color: 'white' }}
                onClick={handleBatchDelete}
                disabled={deleting}
              >
                {deleting ? '删除中...' : `删除 ${selectedIds.size} 项`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Test Case Confirm Modal */}
      {deleteCaseConfirm.open && (
        <div className="modal-overlay" onClick={() => setDeleteCaseConfirm({ open: false })}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">确认删除测试用例</h3>
              <button className="modal__close" onClick={() => setDeleteCaseConfirm({ open: false })}>×</button>
            </div>
            <div className="modal__body">
              <p style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>
                确定要删除测试用例 <strong>"{deleteCaseConfirm.title}"</strong> 吗？
              </p>
              <p style={{ color: 'var(--status-error)', fontSize: '13px' }}>
                此操作不可恢复。
              </p>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setDeleteCaseConfirm({ open: false })}>
                取消
              </button>
              <button
                className="btn"
                style={{ backgroundColor: 'var(--status-error)', color: 'white' }}
                onClick={handleDeleteTestCase}
                disabled={deleting}
              >
                {deleting ? '删除中...' : '删除'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .requirement-item {
          padding: 14px 16px;
          margin-bottom: 8px;
          background-color: var(--surface-primary);
          border: 1px solid var(--border-subtle);
          border-radius: var(--radius-md);
          cursor: pointer;
          transition: all var(--transition-fast);
        }
        .requirement-item:hover {
          border-color: var(--border-default);
          background-color: var(--surface-hover);
        }
        .requirement-item--selected {
          border-color: var(--accent-primary);
          background-color: rgba(37, 99, 235, 0.04);
        }
        .requirement-item--checked {
          background-color: rgba(37, 99, 235, 0.08);
        }
        .requirement-item button:hover {
          color: var(--status-error);
          background-color: var(--status-error-bg);
        }
      `}</style>
    </div>
  );
};

const styles = {
  leftPanel: {
    width: '340px',
    minWidth: '340px',
    height: 'calc(100vh - 56px - 48px)',
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: 'var(--surface-primary)',
    borderRight: '1px solid var(--border-subtle)',
    overflow: 'hidden',
  },
  rightPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  panelTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  },
  panelHint: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    marginTop: '2px',
    display: 'block',
  },
  panelActions: {
    display: 'flex',
    gap: '8px',
  },
  list: {
    flex: 1,
    overflow: 'auto',
    padding: '12px',
  },
  selectAllRow: {
    display: 'flex',
    alignItems: 'center',
    padding: '8px 4px',
    marginBottom: '8px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    cursor: 'pointer',
  },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
    accentColor: 'var(--accent-primary)',
  },
  itemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  itemHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  itemHeaderRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  itemId: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-primary)',
  },
  itemTitle: {
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text-primary)',
    marginBottom: '8px',
    lineHeight: 1.4,
  },
  itemMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  metaTime: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  },
  detailHeader: {
    padding: '20px 24px',
    backgroundColor: 'var(--surface-primary)',
    borderBottom: '1px solid var(--border-subtle)',
  },
  detailTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: '0 0 12px 0',
  },
  detailMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  detailId: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
  },
  description: {
    marginTop: '12px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap' as const,
  },
  tabContent: {
    flex: 1,
    overflow: 'auto',
    padding: '24px',
  },
  workflowInfo: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  workflowInfoItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  },
  workflowInfoLabel: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    fontWeight: 500,
  },
  workflowInfoValue: {
    fontSize: '13px',
    color: 'var(--text-primary)',
  },
  workflowActions: {
    paddingTop: '16px',
    borderTop: '1px solid var(--border-subtle)',
  },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: '12px',
  },
  actionGrid: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '10px',
  },
  actionName: {
    fontWeight: 600,
    color: 'var(--accent-primary)',
  },
  actionArrow: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    marginLeft: '8px',
  },
  caseActionCell: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  caseActionBtn: {
    padding: '2px 8px',
    fontSize: '12px',
    color: 'var(--accent-primary)',
    backgroundColor: 'transparent',
    border: '1px solid var(--border-default)',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  caseWorkflowPanel: {
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid var(--border-subtle)',
  },
  caseWorkflowHint: {
    margin: '8px 0 0',
    fontSize: '13px',
    color: 'var(--text-tertiary)',
    lineHeight: 1.6,
  },
  caseWorkflowHintSub: {
    fontSize: '12px',
    color: 'var(--text-muted)',
  },
  formLabel: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    marginBottom: '6px',
  },
  errorToast: {
    position: 'fixed' as const,
    bottom: '24px',
    right: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '12px 16px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--status-error)',
    fontSize: '13px',
    zIndex: 1000,
  },
  errorClose: {
    padding: '0 4px',
    fontSize: '16px',
    background: 'none',
    border: 'none',
    color: 'var(--status-error)',
    cursor: 'pointer',
  },
  ownerDropdown: {
    position: 'absolute' as const,
    top: '100%',
    left: 0,
    right: 0,
    maxHeight: '200px',
    overflowY: 'auto' as const,
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    zIndex: 100,
    marginTop: '4px',
  },
  ownerDropdownItem: {
    padding: '10px 12px',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid var(--border-subtle)',
  },
  ownerId: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    fontFamily: "'JetBrains Mono', monospace",
  },
  deleteBtn: {
    width: '20px',
    height: '20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    background: 'transparent',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
    padding: 0,
  },
};

export default RequirementsPage;