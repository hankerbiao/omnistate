import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { AutomationTestCaseResponse } from '../types';
import CreateAutomationTestCaseForm from './CreateAutomationTestCaseForm';

const TestCaseList: React.FC = () => {
  const [testCases, setTestCases] = useState<AutomationTestCaseResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateAutomationForm, setShowCreateAutomationForm] = useState(false);

  const fetchTestCases = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.listAutomationTestCases({ limit: 50 });
      setTestCases(response.data || []);
    } catch (err) {
      setError('获取自动化测试用例列表失败');
      console.error('Fetch automation test cases error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTestCases();
  }, [fetchTestCases]);

  const getStatusColor = (status: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      ACTIVE: { bg: 'var(--status-success-bg)', text: 'var(--accent-green)' },
      INACTIVE: { bg: 'var(--bg-tertiary)', text: 'var(--text-muted)' },
      DRAFT: { bg: 'var(--status-info-bg)', text: 'var(--accent-blue)' },
    };
    return colors[status] || { bg: 'var(--bg-tertiary)', text: 'var(--text-secondary)' };
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>自动化测试用例</h1>
          <span style={styles.badge}>{testCases.length}</span>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.actionBtn} onClick={fetchTestCases} disabled={loading}>
            <span style={styles.btnIcon}>↻</span>
            {loading ? '加载中' : '刷新'}
          </button>
          <button style={styles.createBtn} onClick={() => setShowCreateAutomationForm(true)}>
            <span style={styles.btnIcon}>+</span>
            新建用例
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
            <span style={styles.emptyIcon}>⚡</span>
            <p>暂无自动化测试用例</p>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeader}>
                <th style={styles.th}>用例ID</th>
                <th style={styles.th}>用例名称</th>
                <th style={styles.th}>框架</th>
                <th style={styles.th}>自动化类型</th>
                <th style={styles.th}>状态</th>
                <th style={styles.th}>版本</th>
                <th style={styles.th}>标签</th>
                <th style={styles.th}>维护人</th>
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
                      <span style={styles.caseId}>{testCase.auto_case_id}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.caseTitle}>{testCase.name}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.frameworkBadge}>{testCase.framework || '-'}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.typeBadge}>{testCase.automation_type || '-'}</span>
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
                      <span style={styles.versionBadge}>v{testCase.version}</span>
                    </td>
                    <td style={styles.td}>
                      <div style={styles.tagList}>
                        {testCase.tags?.slice(0, 2).map((tag, i) => (
                          <span key={i} style={styles.tag}>{tag}</span>
                        ))}
                        {testCase.tags && testCase.tags.length > 2 && (
                          <span style={styles.moreTag}>+{testCase.tags.length - 2}</span>
                        )}
                      </div>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.ownerBadge}>{testCase.maintainer_id || '-'}</span>
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
    color: 'var(--accent-purple)',
    backgroundColor: 'rgba(163, 113, 247, 0.15)',
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
    color: 'var(--bg-primary)',
    backgroundColor: 'var(--accent-purple)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
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
  caseId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--accent-purple)',
  } as const,
  caseTitle: {
    fontWeight: 500,
  } as const,
  frameworkBadge: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    color: 'var(--accent-cyan)',
    backgroundColor: 'rgba(57, 208, 214, 0.15)',
    padding: '3px 8px',
    borderRadius: '4px',
  } as const,
  typeBadge: {
    fontSize: '12px',
    color: 'var(--accent-orange)',
    backgroundColor: 'rgba(219, 109, 40, 0.15)',
    padding: '3px 8px',
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
  versionBadge: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-tertiary)',
    padding: '2px 8px',
    borderRadius: '4px',
  } as const,
  tagList: {
    display: 'flex',
    gap: '4px',
    flexWrap: 'wrap' as const,
  } as const,
  tag: {
    fontSize: '11px',
    color: 'var(--accent-blue)',
    backgroundColor: 'rgba(88, 166, 255, 0.15)',
    padding: '2px 8px',
    borderRadius: '10px',
  } as const,
  moreTag: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    padding: '2px 6px',
  } as const,
  ownerBadge: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
  } as const,
  timeText: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
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
    borderTopColor: 'var(--accent-purple)',
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