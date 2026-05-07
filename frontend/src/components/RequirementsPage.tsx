import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import type { RequirementResponse, TestCaseResponse, WorkflowTransition } from '../types';
import CreateRequirementForm from './CreateRequirementForm';
import CreateTestCaseForm from './CreateTestCaseForm';
import TestCaseDetailModal from './TestCaseDetailModal';

type ActiveTab = 'workflow' | 'testcases';

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
  const [workflowState, setWorkflowState] = useState<string>('');
  const [workflowTransitions, setWorkflowTransitions] = useState<WorkflowTransition[]>([]);
  const [loadingWorkflow, setLoadingWorkflow] = useState(false);
  const [transitioningAction, setTransitioningAction] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('workflow');
  const [transitionModal, setTransitionModal] = useState<{ open: boolean; transition?: WorkflowTransition }>({ open: false });
  const [transitionFormData, setTransitionFormData] = useState<Record<string, string>>({});

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

  useEffect(() => {
    fetchRequirements();
  }, [fetchRequirements]);

  useEffect(() => {
    if (!selectedRequirementId) {
      setTestCases([]);
      return;
    }
    fetchTestCases(selectedRequirementId);
  }, [fetchTestCases, selectedRequirementId]);

  useEffect(() => {
    if (!selectedRequirement?.workflow_item_id) {
      setWorkflowState('');
      setWorkflowTransitions([]);
      return;
    }
    fetchWorkflowTransitions(selectedRequirement.workflow_item_id);
  }, [fetchWorkflowTransitions, selectedRequirement?.workflow_item_id]);

  const handleRequirementCreated = (requirement: RequirementResponse) => {
    fetchRequirements(requirement.req_id);
  };

  const handleTestCaseCreated = () => {
    if (selectedRequirementId) {
      fetchTestCases(selectedRequirementId);
    }
  };

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
      PENDING_REVIEW: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
      PENDING_DEVELOP: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      DEVELOPING: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      PENDING_TEST: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      PENDING_UAT: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      PENDING_RELEASE: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
      RELEASED: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
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

  const openTransitionModal = (transition: WorkflowTransition) => {
    const initialData: Record<string, string> = {};
    for (const field of transition.required_fields) {
      initialData[field] = field === 'priority' ? selectedRequirement?.priority || '' : '';
    }
    setTransitionFormData(initialData);
    setTransitionModal({ open: true, transition });
  };

  const handleTransitionSubmit = async () => {
    if (!selectedRequirement?.workflow_item_id || !transitionModal.transition) return;

    for (const field of transitionModal.transition.required_fields) {
      if (!transitionFormData[field]?.trim()) {
        setError(`${getFieldLabel(field)}不能为空`);
        return;
      }
    }

    setTransitioningAction(transitionModal.transition.action);
    setError(null);
    try {
      await api.transitionWorkflow(selectedRequirement.workflow_item_id, {
        action: transitionModal.transition.action,
        form_data: transitionFormData,
      });
      await fetchRequirements(selectedRequirement.req_id);
      await fetchWorkflowTransitions(selectedRequirement.workflow_item_id);
      setTransitionModal({ open: false });
    } catch (err) {
      setError('工作流流转失败');
      console.error('Workflow transition error:', err);
    } finally {
      setTransitioningAction(null);
    }
  };

  const onlineCount = requirements.filter(r => r.status === 'RELEASED').length;

  return (
    <div className="workspace">
      {/* Left Panel - Requirements List */}
      <div style={styles.leftPanel}>
        <div style={styles.panelHeader}>
          <div>
            <h2 style={styles.panelTitle}>需求列表</h2>
            <span style={styles.panelHint}>{requirements.length} 个需求，已发布 {onlineCount}</span>
          </div>
          <div style={styles.panelActions}>
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
            {requirements.map((requirement) => {
              const priorityStyle = getPriorityStyle(requirement.priority);
              const isSelected = selectedRequirementId === requirement.req_id;
              return (
                <div
                  key={requirement.req_id}
                  className={`requirement-item ${isSelected ? 'requirement-item--selected' : ''}`}
                  onClick={() => setSelectedRequirementId(requirement.req_id)}
                >
                  <div style={styles.itemHeader}>
                    <span style={styles.itemId}>{requirement.req_id}</span>
                    <span
                      className="status-badge"
                      style={{ backgroundColor: priorityStyle.bg, color: priorityStyle.color }}
                    >
                      {requirement.priority}
                    </span>
                  </div>
                  <div style={styles.itemTitle}>{requirement.title}</div>
                  <div style={styles.itemMeta}>
                    <span
                      className="status-badge status-badge--neutral"
                      style={{ fontSize: '10px' }}
                    >
                      {requirement.status}
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
                                onClick={() => openTransitionModal(transition)}
                                disabled={Boolean(transitioningAction)}
                              >
                                <span style={styles.actionName}>{getActionLabel(transition.action)}</span>
                                <span style={styles.actionArrow}>→ {transition.to_state}</span>
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
                          <th>用例ID</th>
                          <th>名称</th>
                          <th>优先级</th>
                          <th>状态</th>
                          <th>创建时间</th>
                        </tr>
                      </thead>
                      <tbody>
                        {testCases.map((testCase) => (
                          <tr
                            key={testCase.id}
                            onClick={() => setSelectedTestCase(testCase)}
                            style={{ cursor: 'pointer' }}
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
                              <span className="status-badge status-badge--neutral">
                                {testCase.status}
                              </span>
                            </td>
                            <td className="mono">
                              {new Date(testCase.created_at).toLocaleDateString('zh-CN')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
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
        />
      )}

      {/* Transition Modal */}
      {transitionModal.open && transitionModal.transition && (
        <div className="modal-overlay" onClick={() => setTransitionModal({ open: false })}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">{getActionLabel(transitionModal.transition.action)}</h3>
              <button className="modal__close" onClick={() => setTransitionModal({ open: false })}>×</button>
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
              <button className="btn btn--secondary" onClick={() => setTransitionModal({ open: false })}>
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
  itemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
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
};

export default RequirementsPage;