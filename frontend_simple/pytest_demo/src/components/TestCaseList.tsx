import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { TestCaseResponse } from '../types';
import CreateTestCaseForm from './CreateTestCaseForm';
import CreateAutomationTestCaseForm from './CreateAutomationTestCaseForm';

interface TestCaseListProps {
  onLogout?: () => void;
}

const TestCaseList: React.FC<TestCaseListProps> = () => {
  const [testCases, setTestCases] = useState<TestCaseResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showCreateAutomationForm, setShowCreateAutomationForm] = useState(false);
  const [selectedCaseIds, setSelectedCaseIds] = useState<Set<string>>(new Set());

  const fetchTestCases = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.listTestCases({ limit: 50 });
      setTestCases(response.data || []);
    } catch (err) {
      setError('获取测试用例列表失败');
      console.error('Fetch test cases error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTestCases();
  }, [fetchTestCases]);

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    const checked = e.target.checked;
    if (checked) {
      const allIds = new Set(testCases.map(tc => tc.id));
      setSelectedCaseIds(allIds);
    } else {
      setSelectedCaseIds(new Set());
    }
  };

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(caseId)) {
        newSet.delete(caseId);
      } else {
        newSet.add(caseId);
      }
      return newSet;
    });
  };

  const isAllSelected = testCases.length > 0 && selectedCaseIds.size === testCases.length;

  const handleExecute = async () => {
    if (selectedCaseIds.size === 0) {
      alert('请先选择要执行的测试用例');
      return;
    }

    try {
      const selectedTestCases = testCases.filter(tc => selectedCaseIds.has(tc.id));
      const cases = selectedTestCases.map(tc => ({ case_id: tc.case_id }));

      const response = await api.dispatchTask({
        framework: 'pytest',
        trigger_source: 'manual',
        cases: cases,
      });

      console.log('下发测试任务成功:', response);
      alert(`已下发 ${selectedCaseIds.size} 个测试用例，任务ID: ${response.data.task_id}`);
    } catch (err) {
      alert('下发测试用例失败');
      console.error('Dispatch test cases error:', err);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      DRAFT: { bg: 'var(--status-info-bg)', text: 'var(--accent-blue)' },
      PENDING: { bg: 'var(--status-warning-bg)', text: 'var(--accent-yellow)' },
      APPROVED: { bg: 'var(--status-success-bg)', text: 'var(--accent-green)' },
      REJECTED: { bg: 'var(--status-error-bg)', text: 'var(--accent-red)' },
    };
    return colors[status] || { bg: 'var(--bg-tertiary)', text: 'var(--text-secondary)' };
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>测试用例</h1>
          <span style={styles.badge}>{testCases.length}</span>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.actionBtn} onClick={fetchTestCases} disabled={loading}>
            <span style={styles.btnIcon}>↻</span>
            {loading ? '加载中' : '刷新'}
          </button>
          <button style={styles.createBtn} onClick={() => setShowCreateForm(true)}>
            <span style={styles.btnIcon}>+</span>
            手动用例
          </button>
          <button style={styles.autoBtn} onClick={() => setShowCreateAutomationForm(true)}>
            <span style={styles.btnIcon}>⚡</span>
            自动化用例
          </button>
          <button
            style={{
              ...styles.executeBtn,
              ...(selectedCaseIds.size === 0 ? styles.executeBtnDisabled : {}),
            }}
            onClick={handleExecute}
            disabled={selectedCaseIds.size === 0}
          >
            <span style={styles.btnIcon}>▶</span>
            执行 ({selectedCaseIds.size})
          </button>
        </div>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          <span>⚠</span> {error}
        </div>
      )}

      <div style={styles.tableWrapper}>
        {loading ? (
          <div style={styles.loadingState}>
            <div style={styles.spinner} />
            <span>加载中...</span>
          </div>
        ) : testCases.length === 0 ? (
          <div style={styles.emptyState}>
            <span style={styles.emptyIcon}>◫</span>
            <p>暂无测试用例</p>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeader}>
                <th style={{ ...styles.th, width: '48px' }}>
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={handleSelectAll}
                    style={styles.checkbox}
                  />
                </th>
                <th style={styles.th}>用例编号</th>
                <th style={styles.th}>用例名称</th>
                <th style={styles.th}>需求编号</th>
                <th style={styles.th}>状态</th>
                <th style={styles.th}>优先级</th>
                <th style={styles.th}>负责人</th>
                <th style={styles.th}>激活</th>
                <th style={styles.th}>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {testCases.map((testCase, index) => {
                const statusStyle = getStatusColor(testCase.status);
                return (
                  <tr
                    key={testCase.id}
                    style={{
                      ...styles.tr,
                      animationDelay: `${index * 30}ms`,
                    }}
                  >
                    <td style={styles.td}>
                      <input
                        type="checkbox"
                        checked={selectedCaseIds.has(testCase.id)}
                        onChange={() => handleSelectCase(testCase.id)}
                        style={styles.checkbox}
                      />
                    </td>
                    <td style={styles.td}>
                      <span style={styles.caseId}>{testCase.case_id}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.caseTitle}>{testCase.title}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.reqId}>{testCase.ref_req_id}</span>
                    </td>
                    <td style={styles.td}>
                      <span
                        style={{
                          ...styles.statusBadge,
                          backgroundColor: statusStyle.bg,
                          color: statusStyle.text,
                        }}
                      >
                        {testCase.status}
                      </span>
                    </td>
                    <td style={styles.td}>
                      {testCase.priority ? (
                        <span style={styles.priorityBadge}>{testCase.priority}</span>
                      ) : (
                        <span style={styles.mutedText}>-</span>
                      )}
                    </td>
                    <td style={styles.td}>
                      {testCase.owner_id ? (
                        <span style={styles.ownerBadge}>{testCase.owner_id}</span>
                      ) : (
                        <span style={styles.mutedText}>-</span>
                      )}
                    </td>
                    <td style={styles.td}>
                      <span
                        style={{
                          ...styles.activeBadge,
                          backgroundColor: testCase.is_active
                            ? 'var(--status-success-bg)'
                            : 'var(--bg-tertiary)',
                          color: testCase.is_active
                            ? 'var(--accent-green)'
                            : 'var(--text-muted)',
                        }}
                      >
                        {testCase.is_active ? '是' : '否'}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.timeText}>
                        {new Date(testCase.created_at).toLocaleString('zh-CN')}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {showCreateForm && (
        <CreateTestCaseForm
          onClose={() => setShowCreateForm(false)}
          onSuccess={fetchTestCases}
        />
      )}

      {showCreateAutomationForm && (
        <CreateAutomationTestCaseForm
          onClose={() => setShowCreateAutomationForm(false)}
          onSuccess={fetchTestCases}
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
    animation: 'fadeIn 0.4s ease',
  } as const,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '28px',
  } as const,
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
  } as const,
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    letterSpacing: '-0.5px',
    margin: 0,
  } as const,
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '28px',
    height: '28px',
    padding: '0 10px',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-cyan)',
    backgroundColor: 'rgba(57, 208, 214, 0.15)',
    borderRadius: '14px',
  } as const,
  headerActions: {
    display: 'flex',
    gap: '10px',
  } as const,
  actionBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  createBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-primary)',
    backgroundColor: 'var(--accent-blue)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  autoBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--bg-primary)',
    backgroundColor: 'var(--accent-purple)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  executeBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--bg-primary)',
    backgroundColor: 'var(--accent-green)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  executeBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  } as const,
  btnIcon: {
    fontSize: '14px',
  } as const,
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 18px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--accent-red)',
    fontSize: '14px',
    marginBottom: '20px',
  } as const,
  tableWrapper: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
  } as const,
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  } as const,
  tableHeader: {
    backgroundColor: 'var(--bg-tertiary)',
  } as const,
  th: {
    padding: '14px 16px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textAlign: 'left' as const,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    borderBottom: '1px solid var(--border-default)',
  } as const,
  tr: {
    borderBottom: '1px solid var(--border-muted)',
    transition: 'background-color var(--transition-fast)',
    animation: 'slideUp 0.3s ease forwards',
    opacity: 0,
  } as const,
  td: {
    padding: '14px 16px',
    fontSize: '14px',
    color: 'var(--text-primary)',
  } as const,
  checkbox: {
    width: '18px',
    height: '18px',
    cursor: 'pointer',
    accentColor: 'var(--accent-cyan)',
  } as const,
  caseId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--accent-cyan)',
  } as const,
  caseTitle: {
    fontWeight: 500,
  } as const,
  reqId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-tertiary)',
    padding: '2px 8px',
    borderRadius: '4px',
  } as const,
  statusBadge: {
    display: 'inline-flex',
    padding: '4px 10px',
    fontSize: '11px',
    fontWeight: 600,
    borderRadius: '12px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as const,
  priorityBadge: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--accent-orange)',
    backgroundColor: 'rgba(219, 109, 40, 0.15)',
    padding: '2px 8px',
    borderRadius: '4px',
  } as const,
  ownerBadge: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
  } as const,
  activeBadge: {
    display: 'inline-flex',
    padding: '4px 10px',
    fontSize: '11px',
    fontWeight: 600,
    borderRadius: '12px',
  } as const,
  timeText: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  mutedText: {
    color: 'var(--text-muted)',
  } as const,
  loadingState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    padding: '60px',
    color: 'var(--text-secondary)',
  } as const,
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid var(--border-default)',
    borderTopColor: 'var(--accent-cyan)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  } as const,
  emptyState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '60px',
    color: 'var(--text-muted)',
  } as const,
  emptyIcon: {
    fontSize: '48px',
    opacity: 0.3,
  } as const,
};

export default TestCaseList;