import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import type { TestCaseChangeLog } from '../types';
import {
  CHANGE_LOG_ACTION_LABELS,
  TEST_CASE_FIELD_LABELS,
  formatChangeValue,
} from '../constants/testCaseFieldLabels';

interface TestCaseChangeLogPanelProps {
  caseId: string;
  /** 外部递增时刷新（如编辑保存后） */
  refreshSignal?: number;
}

const TestCaseChangeLogPanel: React.FC<TestCaseChangeLogPanelProps> = ({
  caseId,
  refreshSignal = 0,
}) => {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<TestCaseChangeLog[]>([]);
  const [total, setTotal] = useState(0);
  const [openEntryId, setOpenEntryId] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getTestCaseChangeLogs(caseId, { limit: 50, offset: 0 });
      const data = res.data;
      const items = data?.items || [];
      setLogs(items);
      setTotal(data?.total ?? 0);
      setLoaded(true);
      setOpenEntryId((prev) => prev ?? items[0]?.id ?? null);
    } catch (err) {
      console.error(err);
      setError('加载变更记录失败');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    const next = !open;
    setOpen(next);
    if (next && !loaded) {
      void fetchLogs();
    }
  };

  useEffect(() => {
    if (open && refreshSignal > 0) {
      void fetchLogs();
    }
  }, [refreshSignal, open, fetchLogs]);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  const styles = changeLogPanelStyles; // alias for brevity in panel shell

  return (
    <div style={styles.wrap} ref={wrapRef} onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        className={`btn btn--ghost btn--sm${open ? ' btn--active' : ''}`}
        style={styles.triggerBtn}
        onClick={handleToggle}
        title="查看字段变更历史"
        aria-expanded={open}
      >
        变更记录
        {loaded && total > 0 && (
          <span style={styles.badge}>{total}</span>
        )}
      </button>

      {open && (
        <div style={styles.popover} role="dialog" aria-label="变更记录">
          <div style={styles.popoverHeader}>
            <span style={styles.popoverTitle}>变更记录</span>
            {loaded && !loading && (
              <span style={styles.popoverMeta}>{total} 条</span>
            )}
            <button
              type="button"
              style={styles.refreshBtn}
              onClick={() => { void fetchLogs(); }}
              disabled={loading}
              title="刷新"
            >
              ↻
            </button>
          </div>

          <div style={styles.popoverBody}>
            {error && <div style={styles.error}>{error}</div>}
            {loading && !loaded ? (
              <div style={styles.loading}>
                <div className="loading-spinner" style={{ width: 22, height: 22 }} />
              </div>
            ) : logs.length === 0 ? (
              <p style={styles.empty}>
                暂无变更记录（自功能上线后的编辑将自动记录）
              </p>
            ) : (
              <ChangeLogTimeline
                logs={logs}
                openEntryId={openEntryId}
                onToggleEntry={(id) => setOpenEntryId((prev) => (prev === id ? null : id))}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const changeLogPanelStyles: Record<string, React.CSSProperties> = {
  wrap: {
    position: 'relative',
    flexShrink: 0,
  },
  triggerBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    whiteSpace: 'nowrap',
  },
  badge: {
    fontSize: 10,
    fontWeight: 600,
    padding: '1px 6px',
    borderRadius: 999,
    backgroundColor: 'var(--surface-tertiary)',
    color: 'var(--text-secondary)',
  },
  popover: {
    position: 'absolute',
    top: 'calc(100% + 8px)',
    right: 0,
    width: 420,
    maxWidth: 'min(420px, 90vw)',
    maxHeight: 'min(480px, 70vh)',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: 'var(--bg-elevated)',
    border: '1px solid var(--border-default)',
    borderRadius: 10,
    boxShadow: '0 12px 40px rgba(0,0,0,0.18)',
    zIndex: 10,
    overflow: 'hidden',
  },
  popoverHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '12px 14px',
    borderBottom: '1px solid var(--border-muted)',
    backgroundColor: 'var(--bg-secondary)',
    flexShrink: 0,
  },
  popoverTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  popoverMeta: {
    fontSize: 12,
    color: 'var(--text-muted)',
  },
  refreshBtn: {
    marginLeft: 'auto',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: 14,
    color: 'var(--text-muted)',
    padding: '2px 6px',
  },
  popoverBody: {
    padding: 12,
    overflowY: 'auto',
    flex: 1,
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    padding: 32,
  },
  empty: {
    margin: 0,
    fontSize: 13,
    color: 'var(--text-muted)',
    textAlign: 'center',
    padding: '24px 12px',
  },
  error: {
    fontSize: 12,
    color: 'var(--status-error)',
    marginBottom: 12,
  },
  timeline: {
    display: 'flex',
    flexDirection: 'column',
    gap: 0,
  },
  entry: {
    display: 'flex',
    gap: 12,
  },
  entryRail: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    width: 16,
    flexShrink: 0,
    paddingTop: 6,
  },
  entryDot: {
    borderRadius: '50%',
    flexShrink: 0,
  },
  entryLine: {
    flex: 1,
    width: 2,
    backgroundColor: 'var(--border-subtle)',
    marginTop: 4,
    minHeight: 16,
  },
  entryBody: {
    flex: 1,
    minWidth: 0,
    paddingBottom: 14,
  },
  entryHeaderBtn: {
    width: '100%',
    textAlign: 'left',
    background: 'none',
    border: 'none',
    padding: 0,
    cursor: 'pointer',
  },
  entryHeaderTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  actionBadge: {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--accent-primary)',
  },
  entryTime: {
    fontSize: 11,
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
  },
  entryMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    fontSize: 12,
    color: 'var(--text-secondary)',
  },
  changeCount: {
    color: 'var(--text-muted)',
  },
  chevron: {
    marginLeft: 'auto',
    fontSize: 10,
    color: 'var(--text-muted)',
  },
  remark: {
    marginTop: 6,
    fontSize: 12,
    color: 'var(--text-secondary)',
    fontStyle: 'italic',
  },
  diffTable: {
    marginTop: 10,
    border: '1px solid var(--border-muted)',
    borderRadius: 6,
    overflow: 'hidden',
  },
  diffRow: {
    display: 'grid',
    gridTemplateColumns: '100px 1fr',
    gap: 10,
    padding: '8px 10px',
    borderBottom: '1px solid var(--border-muted)',
    fontSize: 12,
    alignItems: 'start',
  },
  diffLabel: {
    color: 'var(--text-muted)',
    fontWeight: 500,
  },
  diffValues: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 6,
    wordBreak: 'break-word',
  },
  oldValue: {
    color: 'var(--text-muted)',
    textDecoration: 'line-through',
  },
  arrow: {
    color: 'var(--text-tertiary)',
    fontSize: 11,
  },
  newValue: {
    color: 'var(--text-primary)',
    fontWeight: 500,
  },
  removedTag: {
    fontSize: 11,
    color: 'var(--status-error)',
  },
};

export interface ChangeLogTimelineProps {
  logs: TestCaseChangeLog[];
  openEntryId: string | null;
  onToggleEntry: (id: string) => void;
}

export const ChangeLogTimeline: React.FC<ChangeLogTimelineProps> = ({
  logs,
  openEntryId,
  onToggleEntry,
}) => (
  <div style={changeLogPanelStyles.timeline}>
    {logs.map((log, index) => {
      const isOpen = openEntryId === log.id;
      const changeCount = log.changes.length;
      return (
        <div key={log.id} style={changeLogPanelStyles.entry}>
          <div style={changeLogPanelStyles.entryRail}>
            <div
              style={{
                ...changeLogPanelStyles.entryDot,
                backgroundColor: index === 0 ? 'var(--accent-primary)' : 'var(--border-subtle)',
                width: index === 0 ? 10 : 8,
                height: index === 0 ? 10 : 8,
              }}
            />
            {index < logs.length - 1 && <div style={changeLogPanelStyles.entryLine} />}
          </div>
          <div style={changeLogPanelStyles.entryBody}>
            <button
              type="button"
              style={changeLogPanelStyles.entryHeaderBtn}
              onClick={() => onToggleEntry(log.id)}
            >
              <div style={changeLogPanelStyles.entryHeaderTop}>
                <span style={changeLogPanelStyles.actionBadge}>
                  {CHANGE_LOG_ACTION_LABELS[log.action] || log.action}
                </span>
                <span style={changeLogPanelStyles.entryTime}>
                  {new Date(log.created_at).toLocaleString('zh-CN')}
                </span>
              </div>
              <div style={changeLogPanelStyles.entryMeta}>
                <span>{log.operator_name || log.operator_id}</span>
                {changeCount > 0 && (
                  <span style={changeLogPanelStyles.changeCount}>修改 {changeCount} 项</span>
                )}
                <span style={changeLogPanelStyles.chevron}>{isOpen ? '▼' : '▶'}</span>
              </div>
              {log.remark && (
                <div style={changeLogPanelStyles.remark}>版本说明：{log.remark}</div>
              )}
            </button>

            {isOpen && changeCount > 0 && (
              <div style={changeLogPanelStyles.diffTable}>
                {log.changes.map((change) => (
                  <div key={`${log.id}-${change.field}`} style={changeLogPanelStyles.diffRow}>
                    <span style={changeLogPanelStyles.diffLabel}>
                      {TEST_CASE_FIELD_LABELS[change.field] || change.field}
                    </span>
                    <div style={changeLogPanelStyles.diffValues}>
                      {change.change_type !== 'added' && (
                        <span style={changeLogPanelStyles.oldValue}>
                          {formatChangeValue(change.field, change.old_value)}
                        </span>
                      )}
                      {change.change_type === 'modified' && (
                        <span style={changeLogPanelStyles.arrow}>→</span>
                      )}
                      {change.change_type !== 'removed' && (
                        <span style={changeLogPanelStyles.newValue}>
                          {formatChangeValue(change.field, change.new_value)}
                        </span>
                      )}
                      {change.change_type === 'removed' && (
                        <span style={changeLogPanelStyles.removedTag}>已移除</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      );
    })}
  </div>
);

export default TestCaseChangeLogPanel;
