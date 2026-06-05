import React from 'react';
import {
  getStateLabel,
  WORKFLOW_ACTION_LABELS,
  getWorkflowStateStyle,
  type WorkflowTypeCode,
} from '../../constants/workflowLabels';
import type { WorkflowTransitionLog } from '../../types';

interface WorkflowLogsPanelProps {
  logs: WorkflowTransitionLog[];
  loading: boolean;
  typeCode?: WorkflowTypeCode;
  collapsed?: boolean;
  onToggle?: () => void;
}

export interface WorkflowLogsTimelineProps {
  logs: WorkflowTransitionLog[];
  loading: boolean;
  typeCode?: WorkflowTypeCode;
}

export const WorkflowLogsTimeline: React.FC<WorkflowLogsTimelineProps> = ({
  logs,
  loading,
  typeCode,
}) => {
  if (loading) {
    return (
      <div style={styles.loading}>
        <div className="loading-spinner" style={{ width: 20, height: 20 }} />
      </div>
    );
  }
  if (logs.length === 0) {
    return <p style={styles.empty}>暂无流转记录</p>;
  }
  return (
    <div style={styles.timeline}>
      {logs.map((log, index) => {
        const stateStyle = getWorkflowStateStyle(log.to_state);
        return (
          <div key={log.id} style={styles.item}>
            <div style={styles.itemRail}>
              <div
                style={{
                  ...styles.itemDot,
                  width: index === 0 ? '10px' : '8px',
                  height: index === 0 ? '10px' : '8px',
                  backgroundColor: index === 0 ? 'var(--accent-primary)' : 'var(--border-subtle)',
                }}
              />
              {index < logs.length - 1 && <div style={styles.itemLine} />}
            </div>
            <div style={styles.itemContent}>
              <div style={styles.itemTop}>
                <span style={styles.action}>
                  {WORKFLOW_ACTION_LABELS[log.action] || log.action}
                </span>
                <span style={styles.time}>
                  {new Date(log.created_at).toLocaleString('zh-CN')}
                </span>
              </div>
              <div style={styles.stateRow}>
                <span style={styles.stateFrom}>
                  {getStateLabel(log.from_state, typeCode)}
                </span>
                <span style={styles.arrow}>→</span>
                <span
                  className="status-badge"
                  style={{ ...stateStyle, fontSize: '11px', padding: '2px 8px' }}
                >
                  {getStateLabel(log.to_state, typeCode)}
                </span>
              </div>
              <div style={styles.meta}>
                操作人: <code style={styles.code}>{log.operator_id}</code>
                {log.payload?.comment != null && String(log.payload.comment) !== '' && (
                  <span style={styles.comment}> · {String(log.payload.comment)}</span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const WorkflowLogsPanel: React.FC<WorkflowLogsPanelProps> = ({
  logs,
  loading,
  typeCode,
  collapsed = false,
  onToggle,
}) => {
  return (
    <div style={styles.container}>
      <button type="button" style={styles.header} onClick={onToggle}>
        <span style={styles.headerTitle}>流转历史</span>
        <span style={styles.headerMeta}>
          {loading ? '加载中…' : `${logs.length} 条`}
          <span style={styles.chevron}>{collapsed ? '▶' : '▼'}</span>
        </span>
      </button>

      {!collapsed && (
        <div style={styles.body}>
          <WorkflowLogsTimeline logs={logs} loading={loading} typeCode={typeCode} />
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    borderTop: '1px solid var(--border-subtle)',
    marginTop: '16px',
    paddingTop: '12px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    background: 'none',
    border: 'none',
    padding: '4px 0',
    cursor: 'pointer',
    textAlign: 'left',
  },
  headerTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  headerMeta: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  chevron: {
    fontSize: '10px',
  },
  body: {
    marginTop: '8px',
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    padding: '16px',
  },
  empty: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    textAlign: 'center',
    padding: '12px',
  },
  timeline: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0',
  },
  item: {
    display: 'flex',
    gap: '10px',
  },
  itemRail: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    width: '12px',
    flexShrink: 0,
  },
  itemDot: {
    borderRadius: '50%',
    flexShrink: 0,
    marginTop: '4px',
  },
  itemLine: {
    flex: 1,
    width: '2px',
    backgroundColor: 'var(--border-subtle)',
    minHeight: '16px',
  },
  itemContent: {
    flex: 1,
    paddingBottom: '14px',
  },
  itemTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '4px',
  },
  action: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  time: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    flexShrink: 0,
  },
  stateRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '4px',
    fontSize: '12px',
  },
  stateFrom: {
    color: 'var(--text-secondary)',
  },
  arrow: {
    color: 'var(--text-tertiary)',
  },
  meta: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  },
  code: {
    fontFamily: 'monospace',
    fontSize: '10px',
    backgroundColor: 'var(--surface-tertiary)',
    padding: '1px 4px',
    borderRadius: '3px',
  },
  comment: {
    color: 'var(--text-secondary)',
  },
};

export default WorkflowLogsPanel;
