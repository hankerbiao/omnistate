import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import type { RequirementResponse, TestCaseResponse, WorkflowTransition } from '../types';
import CreateRequirementForm from './CreateRequirementForm';
import CreateTestCaseForm from './CreateTestCaseForm';
import TestCaseDetailModal from './TestCaseDetailModal';

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
      setError('获取需求关联测试用例失败');
      console.error('Fetch requirement test cases error:', err);
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
      P0: { bg: 'var(--status-error-bg)', color: 'var(--accent-red)' },
      P1: { bg: 'var(--status-warning-bg)', color: 'var(--accent-yellow)' },
      P2: { bg: 'var(--status-info-bg)', color: 'var(--accent-blue)' },
      P3: { bg: 'var(--bg-tertiary)', color: 'var(--text-muted)' },
    };
    return styleMap[priority] || { bg: 'var(--bg-tertiary)', color: 'var(--text-secondary)' };
  };

  const getWorkflowStateStyle = (state: string) => {
    const styleMap: Record<string, { bg: string; color: string }> = {
      DRAFT: { bg: 'var(--bg-tertiary)', color: 'var(--text-muted)' },
      PENDING_REVIEW: { bg: 'var(--status-warning-bg)', color: 'var(--accent-yellow)' },
      PENDING_DEVELOP: { bg: 'var(--status-info-bg)', color: 'var(--accent-blue)' },
      DEVELOPING: { bg: 'rgba(57, 208, 214, 0.12)', color: 'var(--accent-cyan)' },
      PENDING_TEST: { bg: 'rgba(163, 113, 247, 0.14)', color: 'var(--accent-purple)' },
      PENDING_UAT: { bg: 'rgba(57, 208, 214, 0.12)', color: 'var(--accent-cyan)' },
      PENDING_RELEASE: { bg: 'rgba(34, 197, 94, 0.12)', color: '#4ade80' },
      RELEASED: { bg: 'rgba(34, 197, 94, 0.16)', color: '#22c55e' },
    };
    return styleMap[state] || { bg: 'var(--bg-tertiary)', color: 'var(--text-secondary)' };
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

  const buildTransitionFormData = (transition: WorkflowTransition): Record<string, unknown> | null => {
    const formData: Record<string, unknown> = {};
    for (const field of transition.required_fields) {
      const defaultValue = field === 'priority' ? selectedRequirement?.priority || '' : '';
      const value = window.prompt(`请输入${getFieldLabel(field)}`, defaultValue);
      if (value === null) {
        return null;
      }
      if (!value.trim()) {
        setError(`${getFieldLabel(field)}不能为空`);
        return null;
      }
      formData[field] = value.trim();
    }
    return formData;
  };

  const handleWorkflowTransition = async (transition: WorkflowTransition) => {
    if (!selectedRequirement?.workflow_item_id) {
      setError('当前需求缺少工作流事项ID');
      return;
    }

    const formData = buildTransitionFormData(transition);
    if (formData === null) {
      return;
    }

    setTransitioningAction(transition.action);
    setError(null);
    try {
      await api.transitionWorkflow(selectedRequirement.workflow_item_id, {
        action: transition.action,
        form_data: formData,
      });
      await fetchRequirements(selectedRequirement.req_id);
      await fetchWorkflowTransitions(selectedRequirement.workflow_item_id);
    } catch (err) {
      setError('工作流流转失败');
      console.error('Workflow transition error:', err);
    } finally {
      setTransitioningAction(null);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>测试需求</h1>
          <p style={styles.subtitle}>先创建需求，再在需求上下文里创建测试用例。</p>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.secondaryButton} onClick={() => fetchRequirements()} disabled={loadingRequirements}>
            {loadingRequirements ? '加载中' : '刷新'}
          </button>
          <button style={styles.primaryButton} onClick={() => setShowCreateRequirement(true)}>
            新建需求
          </button>
        </div>
      </div>

      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      <div style={styles.panel}>
        <div style={styles.panelHeader}>
          <div>
            <h2 style={styles.panelTitle}>需求列表</h2>
            <span style={styles.panelHint}>点击一条需求，查看并创建其下属测试用例</span>
          </div>
          <span style={styles.counterBadge}>{requirements.length}</span>
        </div>

        {loadingRequirements ? (
          <div style={styles.loadingState}>加载需求中...</div>
        ) : requirements.length === 0 ? (
          <div style={styles.emptyState}>暂无需求，先创建一条测试需求。</div>
        ) : (
          <div style={styles.requirementList}>
            {requirements.map((requirement) => {
              const priorityStyle = getPriorityStyle(requirement.priority);
              const isSelected = selectedRequirementId === requirement.req_id;
              return (
                <button
                  key={requirement.req_id}
                  type="button"
                  style={{
                    ...styles.requirementCard,
                    ...(isSelected ? styles.requirementCardActive : {}),
                  }}
                  onClick={() => setSelectedRequirementId(requirement.req_id)}
                >
                  <div style={styles.requirementCardTop}>
                    <span style={styles.requirementId}>{requirement.req_id}</span>
                    <span
                      style={{
                        ...styles.priorityBadge,
                        backgroundColor: priorityStyle.bg,
                        color: priorityStyle.color,
                      }}
                    >
                      {requirement.priority}
                    </span>
                  </div>
                  <div style={styles.requirementTitle}>{requirement.title}</div>
                  <div style={styles.requirementMeta}>
                    <span>{requirement.status}</span>
                    <span>{new Date(requirement.created_at).toLocaleString('zh-CN')}</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div style={styles.panel}>
        <div style={styles.panelHeader}>
          <div>
            <h2 style={styles.panelTitle}>需求工作流</h2>
            <span style={styles.panelHint}>
              {selectedRequirement
                ? `当前需求：${selectedRequirement.req_id}`
                : '请先选择一个需求'}
            </span>
          </div>
          {selectedRequirement && (
            <span
              style={{
                ...styles.workflowStateBadge,
                backgroundColor: getWorkflowStateStyle(workflowState || selectedRequirement.status).bg,
                color: getWorkflowStateStyle(workflowState || selectedRequirement.status).color,
              }}
            >
              {workflowState || selectedRequirement.status || '-'}
            </span>
          )}
        </div>

        {!selectedRequirement ? (
          <div style={styles.emptyState}>选中需求后，这里会展示工作流状态和可执行流转。</div>
        ) : !selectedRequirement.workflow_item_id ? (
          <div style={styles.emptyState}>当前需求没有关联工作流事项。</div>
        ) : loadingWorkflow ? (
          <div style={styles.loadingState}>加载工作流中...</div>
        ) : (
          <div style={styles.workflowBody}>
            <div style={styles.workflowInfoGrid}>
              <div style={styles.workflowInfoItem}>
                <span style={styles.workflowInfoLabel}>工作流事项</span>
                <span style={styles.workflowInfoValue}>{selectedRequirement.workflow_item_id}</span>
              </div>
              <div style={styles.workflowInfoItem}>
                <span style={styles.workflowInfoLabel}>当前状态</span>
                <span style={styles.workflowInfoValue}>{workflowState || selectedRequirement.status || '-'}</span>
              </div>
            </div>

            {workflowTransitions.length === 0 ? (
              <div style={styles.workflowEmpty}>当前状态没有可执行流转。</div>
            ) : (
              <div style={styles.workflowActionList}>
                {workflowTransitions.map((transition) => (
                  <button
                    key={`${transition.action}-${transition.to_state}`}
                    type="button"
                    style={styles.workflowActionButton}
                    onClick={() => handleWorkflowTransition(transition)}
                    disabled={Boolean(transitioningAction)}
                  >
                    <span style={styles.workflowActionName}>
                      {transitioningAction === transition.action ? '处理中...' : getActionLabel(transition.action)}
                    </span>
                    <span style={styles.workflowActionMeta}>
                      {workflowState || selectedRequirement.status} → {transition.to_state}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div style={styles.panel}>
        <div style={styles.panelHeader}>
          <div>
            <h2 style={styles.panelTitle}>关联测试用例</h2>
            <span style={styles.panelHint}>
              {selectedRequirement
                ? `当前需求：${selectedRequirement.req_id} / ${selectedRequirement.title}`
                : '请先选择一个需求'}
            </span>
          </div>
          <button
            style={{
              ...styles.primaryButton,
              ...(selectedRequirement ? {} : styles.buttonDisabled),
            }}
            onClick={() => setShowCreateTestCase(true)}
            disabled={!selectedRequirement}
          >
            为当前需求创建测试用例
          </button>
        </div>

        {!selectedRequirement ? (
          <div style={styles.emptyState}>选中需求后，这里会展示该需求下的测试用例。</div>
        ) : loadingTestCases ? (
          <div style={styles.loadingState}>加载测试用例中...</div>
        ) : testCases.length === 0 ? (
          <div style={styles.emptyState}>当前需求下暂无测试用例。</div>
        ) : (
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>用例ID</th>
                  <th style={styles.th}>名称</th>
                  <th style={styles.th}>优先级</th>
                  <th style={styles.th}>状态</th>
                  <th style={styles.th}>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {testCases.map((testCase) => (
                  <tr
                    key={testCase.id}
                    style={styles.tr}
                    onClick={() => setSelectedTestCase(testCase)}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.cursor = 'pointer';
                      e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.cursor = 'default';
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <td style={styles.td}>{testCase.case_id}</td>
                    <td style={styles.td}>{testCase.title}</td>
                    <td style={styles.td}>{testCase.priority || '-'}</td>
                    <td style={styles.td}>{testCase.status}</td>
                    <td style={styles.td}>{new Date(testCase.created_at).toLocaleString('zh-CN')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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
    </div>
  );
};

const styles = {
  container: {
    padding: '32px',
    maxWidth: '1400px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '24px',
  } as const,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '16px',
  } as const,
  title: {
    margin: 0,
    fontSize: '28px',
    fontWeight: 700,
    color: 'var(--text-primary)',
  } as const,
  subtitle: {
    margin: '8px 0 0',
    fontSize: '14px',
    color: 'var(--text-muted)',
  } as const,
  headerActions: {
    display: 'flex',
    gap: '10px',
  } as const,
  primaryButton: {
    padding: '10px 16px',
    backgroundColor: 'var(--accent-cyan)',
    color: 'var(--bg-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    fontWeight: 600,
    cursor: 'pointer',
  } as const,
  secondaryButton: {
    padding: '10px 16px',
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  buttonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  } as const,
  errorBanner: {
    padding: '12px 16px',
    backgroundColor: 'var(--status-error-bg)',
    color: 'var(--accent-red)',
    border: '1px solid rgba(255, 107, 107, 0.25)',
    borderRadius: 'var(--radius-md)',
  } as const,
  panel: {
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    padding: '20px',
  } as const,
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '18px',
  } as const,
  panelTitle: {
    margin: 0,
    fontSize: '18px',
    color: 'var(--text-primary)',
  } as const,
  panelHint: {
    display: 'inline-block',
    marginTop: '6px',
    fontSize: '13px',
    color: 'var(--text-muted)',
  } as const,
  counterBadge: {
    minWidth: '32px',
    padding: '6px 10px',
    textAlign: 'center' as const,
    borderRadius: '999px',
    backgroundColor: 'var(--bg-tertiary)',
    color: 'var(--text-secondary)',
    fontSize: '13px',
  } as const,
  loadingState: {
    padding: '32px',
    textAlign: 'center' as const,
    color: 'var(--text-muted)',
  } as const,
  emptyState: {
    padding: '32px',
    textAlign: 'center' as const,
    color: 'var(--text-muted)',
    backgroundColor: 'var(--bg-primary)',
    borderRadius: 'var(--radius-md)',
    border: '1px dashed var(--border-default)',
  } as const,
  requirementList: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '14px',
  } as const,
  requirementCard: {
    textAlign: 'left' as const,
    padding: '16px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-primary)',
    cursor: 'pointer',
  } as const,
  requirementCardActive: {
    borderColor: 'var(--accent-cyan)',
    boxShadow: '0 0 0 1px rgba(57, 208, 214, 0.25)',
  } as const,
  requirementCardTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '12px',
  } as const,
  requirementId: {
    fontSize: '13px',
    color: 'var(--accent-cyan)',
    fontFamily: 'monospace',
  } as const,
  priorityBadge: {
    padding: '4px 8px',
    borderRadius: '999px',
    fontSize: '12px',
    fontWeight: 600,
  } as const,
  requirementTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '10px',
  } as const,
  requirementMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '10px',
    fontSize: '12px',
    color: 'var(--text-muted)',
  } as const,
  tableWrapper: {
    overflowX: 'auto' as const,
  } as const,
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
  } as const,
  th: {
    textAlign: 'left' as const,
    padding: '12px 14px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    borderBottom: '1px solid var(--border-default)',
  } as const,
  tr: {
    borderBottom: '1px solid rgba(255,255,255,0.04)',
    cursor: 'pointer',
    transition: 'background-color var(--transition-fast)',
  } as const,
  td: {
    padding: '14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
  } as const,
};

export default RequirementsPage;
