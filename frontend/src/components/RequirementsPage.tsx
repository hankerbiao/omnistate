import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import type { RequirementResponse, TestCaseResponse } from '../types';
import CreateRequirementForm from './CreateRequirementForm';
import CreateTestCaseForm from './CreateTestCaseForm';

const RequirementsPage: React.FC = () => {
  const [requirements, setRequirements] = useState<RequirementResponse[]>([]);
  const [testCases, setTestCases] = useState<TestCaseResponse[]>([]);
  const [loadingRequirements, setLoadingRequirements] = useState(false);
  const [loadingTestCases, setLoadingTestCases] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRequirementId, setSelectedRequirementId] = useState<string | null>(null);
  const [showCreateRequirement, setShowCreateRequirement] = useState(false);
  const [showCreateTestCase, setShowCreateTestCase] = useState(false);

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
                  <tr key={testCase.id} style={styles.tr}>
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
  } as const,
  td: {
    padding: '14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
  } as const,
};

export default RequirementsPage;
