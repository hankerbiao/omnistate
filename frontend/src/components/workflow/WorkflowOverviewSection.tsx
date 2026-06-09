import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../../services/api';
import type { RequirementResponse, TestCaseResponse } from '../../types';
import {
  getWorkflowStateStyle,
  REQUIREMENT_STATUS_FILTER_OPTIONS,
  TEST_CASE_STATUS_FILTER_OPTIONS,
  type WorkflowTypeCode,
} from '../../constants/workflowLabels';

export interface WorkflowNavigateTarget {
  page: 'requirements' | 'manualTestCases' | 'myTasks';
  status?: string;
}

interface WorkflowOverviewSectionProps {
  onNavigate?: (target: WorkflowNavigateTarget) => void;
}

function countByStatus<T extends { status: string }>(items: T[]): Record<string, number> {
  return items.reduce<Record<string, number>>((acc, item) => {
    const key = item.status || '未知';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

const WorkflowOverviewSection: React.FC<WorkflowOverviewSectionProps> = ({ onNavigate }) => {
  const [requirements, setRequirements] = useState<RequirementResponse[]>([]);
  const [testCases, setTestCases] = useState<TestCaseResponse[]>([]);
  const [myTaskCount, setMyTaskCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reqRes, caseRes, userRes] = await Promise.all([
        api.listRequirements({ limit: 200 }),
        api.listTestCases({ limit: 200 }),
        api.getCurrentUser(),
      ]);
      setRequirements(reqRes.data || []);
      setTestCases(caseRes.data || []);
      const userId = userRes.data?.user_id;
      if (userId) {
        const tasksRes = await api.listMyWorkItems(userId);
        setMyTaskCount(tasksRes.data?.length || 0);
      }
    } catch (err) {
      setError('加载工作流统计失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const reqCounts = useMemo(() => countByStatus(requirements), [requirements]);
  const caseCounts = useMemo(() => countByStatus(testCases), [testCases]);

  const renderStatusGrid = (
    typeCode: WorkflowTypeCode,
    page: 'requirements' | 'manualTestCases',
    options: { value: string; label: string }[],
    counts: Record<string, number>,
  ) => (
    <div style={styles.grid}>
      {options.filter((o) => o.value).map((opt) => {
        const count = counts[opt.value] || 0;
        const style = getWorkflowStateStyle(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            style={{
              ...styles.chip,
              border: `1px solid ${style.color}`,
              opacity: count === 0 ? 0.45 : 1,
            }}
            onClick={() => onNavigate?.({ page, status: opt.value })}
            disabled={!onNavigate}
            title={onNavigate ? `查看${opt.label}的${typeCode === 'REQUIREMENT' ? '需求' : '用例'}` : undefined}
          >
            <span className="status-badge" style={{ ...style, fontSize: '10px', padding: '2px 6px' }}>
              {opt.label}
            </span>
            <span style={styles.chipCount}>{count}</span>
          </button>
        );
      })}
    </div>
  );

  return (
    <div style={styles.section}>
      <div style={styles.header}>
        <div>
          <h3 style={styles.title}>工作流实况</h3>
          <p style={styles.subtitle}>
            来自后端实时数据 · 点击状态卡片跳转筛选
            {!loading && (
              <span style={styles.liveBadge}> LIVE</span>
            )}
          </p>
        </div>
        <div style={styles.headerActions}>
          <button type="button" className="btn btn--ghost btn--sm" onClick={load} disabled={loading}>
            ↻
          </button>
          {onNavigate && (
            <>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => onNavigate({ page: 'myTasks' })}
              >
                我的任务 ({myTaskCount})
              </button>
              <button
                type="button"
                className="btn btn--primary btn--sm"
                onClick={() => onNavigate({ page: 'requirements' })}
              >
                测试用例编写需求
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div style={styles.error}>{error}</div>
      )}

      {loading ? (
        <div style={styles.loading}>
          <div className="loading-spinner" />
        </div>
      ) : (
        <div style={styles.columns}>
          <div style={styles.column}>
            <div style={styles.columnHeader}>
              <span style={styles.columnTitle}>需求</span>
              <span style={styles.columnTotal}>{requirements.length} 条</span>
            </div>
            {renderStatusGrid(
              'REQUIREMENT',
              'requirements',
              REQUIREMENT_STATUS_FILTER_OPTIONS,
              reqCounts,
            )}
          </div>
          <div style={styles.column}>
            <div style={styles.columnHeader}>
              <span style={styles.columnTitle}>测试用例</span>
              <span style={styles.columnTotal}>{testCases.length} 条</span>
            </div>
            {renderStatusGrid(
              'TEST_CASE',
              'manualTestCases',
              TEST_CASE_STATUS_FILTER_OPTIONS,
              caseCounts,
            )}
          </div>
        </div>
      )}

      {!loading && requirements.length + testCases.length > 0 && (
        <div style={styles.summaryRow}>
          <SummaryPill label="需求草稿" value={reqCounts.DRAFT || 0} />
          <SummaryPill label="待审核需求" value={reqCounts.PENDING_REVIEW || 0} />
          <SummaryPill label="用例编写中" value={caseCounts.DEVELOPING || 0} />
          <SummaryPill label="待审核用例" value={caseCounts.PENDING_REVIEW || 0} />
          <SummaryPill label="已发布需求" value={reqCounts.RELEASED || 0} highlight />
        </div>
      )}
    </div>
  );
};

const SummaryPill: React.FC<{ label: string; value: number; highlight?: boolean }> = ({
  label,
  value,
  highlight,
}) => (
  <div
    style={{
      ...styles.pill,
      ...(highlight && value > 0 ? styles.pillHighlight : {}),
    }}
  >
    <span style={styles.pillLabel}>{label}</span>
    <span style={styles.pillValue}>{value}</span>
  </div>
);

const styles: Record<string, React.CSSProperties> = {
  section: {
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-subtle)',
    borderRadius: '12px',
    padding: '20px 24px',
    marginBottom: '20px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    marginBottom: '16px',
    flexWrap: 'wrap',
  },
  title: {
    margin: 0,
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '12px',
    color: 'var(--text-tertiary)',
  },
  liveBadge: {
    color: 'var(--status-success)',
    fontWeight: 700,
    fontSize: '10px',
  },
  headerActions: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  },
  error: {
    padding: '8px 12px',
    backgroundColor: 'var(--status-error-bg)',
    color: 'var(--status-error)',
    borderRadius: '8px',
    fontSize: '13px',
    marginBottom: '12px',
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    padding: '32px',
  },
  columns: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '20px',
  },
  column: {},
  columnHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  columnTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  columnTotal: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
  },
  grid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  chip: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 10px',
    borderRadius: '8px',
    border: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-secondary)',
    cursor: 'pointer',
    transition: 'transform 0.1s, box-shadow 0.1s',
  },
  chipCount: {
    fontSize: '14px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    minWidth: '20px',
    textAlign: 'right',
  },
  summaryRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '10px',
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid var(--border-subtle)',
  },
  pill: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    borderRadius: '999px',
    backgroundColor: 'var(--surface-tertiary)',
    fontSize: '12px',
  },
  pillHighlight: {
    backgroundColor: 'var(--status-success-bg)',
  },
  pillLabel: {
    color: 'var(--text-secondary)',
  },
  pillValue: {
    fontWeight: 700,
    color: 'var(--text-primary)',
  },
};

export default WorkflowOverviewSection;
