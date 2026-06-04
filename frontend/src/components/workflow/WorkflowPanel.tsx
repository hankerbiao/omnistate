import React, { useCallback, useState } from 'react';
import { useWorkflow } from '../../hooks/useWorkflow';
import {
  getStateLabel,
  getWorkflowStateStyle,
  getActionButtonStyle,
  WORKFLOW_ACTION_LABELS,
  type WorkflowTypeCode,
} from '../../constants/workflowLabels';
import type { WorkflowTransition } from '../../types';
import { SWITCHABLE_USERS } from '../../config/users';
import WorkflowStateStepper from './WorkflowStateStepper';
import WorkflowLogsPanel from './WorkflowLogsPanel';
import WorkflowTransitionModal from './WorkflowTransitionModal';

export interface WorkflowPanelProps {
  workflowItemId?: string | null;
  entityLabel?: string;
  typeCode?: WorkflowTypeCode;
  defaultPriority?: string;
  creatorName?: string;
  currentOwnerName?: string;
  createdAt?: string;
  updatedAt?: string;
  onTransitionSuccess?: () => void;
  compact?: boolean;
  showStepper?: boolean;
  showReassign?: boolean;
  showLogs?: boolean;
}

const WorkflowPanel: React.FC<WorkflowPanelProps> = ({
  workflowItemId,
  entityLabel,
  typeCode = 'REQUIREMENT',
  defaultPriority = '',
  creatorName,
  currentOwnerName,
  createdAt,
  updatedAt,
  onTransitionSuccess,
  compact = false,
  showStepper = true,
  showReassign = true,
  showLogs = true,
}) => {
  const wf = useWorkflow(workflowItemId);
  const [transitionModal, setTransitionModal] = useState<{
    open: boolean;
    transition?: WorkflowTransition;
  }>({ open: false });
  const [logsCollapsed, setLogsCollapsed] = useState(false);
  const [showReassignForm, setShowReassignForm] = useState(false);
  const [reassignUserId, setReassignUserId] = useState('');
  const [reassignRemark, setReassignRemark] = useState('');

  const handleTransition = useCallback(
    async (formData: Record<string, string>) => {
      if (!transitionModal.transition) return false;
      const ok = await wf.executeTransition(transitionModal.transition.action, formData);
      if (ok) {
        onTransitionSuccess?.();
      }
      return ok;
    },
    [transitionModal.transition, wf, onTransitionSuccess],
  );

  const handleReassign = async () => {
    if (!reassignUserId.trim()) return;
    const ok = await wf.reassign(reassignUserId.trim(), reassignRemark);
    if (ok) {
      setShowReassignForm(false);
      setReassignUserId('');
      setReassignRemark('');
      onTransitionSuccess?.();
    }
  };

  if (!workflowItemId) {
    return (
      <div className="empty-state" style={{ padding: compact ? '16px' : '32px' }}>
        <div className="empty-state__icon">⚙</div>
        <p className="empty-state__text">未绑定工作流</p>
        <p style={styles.hint}>
          请重新创建实体，或检查后端 workflow 关联是否正常。
        </p>
      </div>
    );
  }

  if (wf.loading && !wf.currentState) {
    return (
      <div className="loading-overlay" style={{ minHeight: compact ? '80px' : '120px' }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  const stateStyle = getWorkflowStateStyle(wf.currentState);

  return (
    <div style={compact ? styles.compactRoot : styles.root}>
      {entityLabel && (
        <div style={styles.entityLabel}>{entityLabel}</div>
      )}

      {(wf.error || wf.successMessage) && (
        <div style={wf.error ? styles.errorBanner : styles.successBanner}>
          <span>{wf.error || wf.successMessage}</span>
          <button type="button" style={styles.dismissBtn} onClick={wf.clearMessages}>×</button>
        </div>
      )}

      {showStepper && (
        <WorkflowStateStepper currentState={wf.currentState} typeCode={typeCode} />
      )}

      <div style={styles.metaGrid}>
        <MetaItem label="工作流 ID" value={workflowItemId} mono />
        <MetaItem
          label="当前状态"
          value={
            <span className="status-badge" style={stateStyle}>
              {getStateLabel(wf.currentState, typeCode)}
            </span>
          }
        />
        <MetaItem label="创建人" value={creatorName || wf.creator || '-'} />
        <MetaItem label="当前负责人" value={currentOwnerName || wf.currentOwner || '-'} />
        {!compact && createdAt && (
          <MetaItem label="创建时间" value={new Date(createdAt).toLocaleString('zh-CN')} />
        )}
        {!compact && updatedAt && (
          <MetaItem label="更新时间" value={new Date(updatedAt).toLocaleString('zh-CN')} />
        )}
      </div>

      <div style={styles.permissionHint}>
        流转权限认<strong>创建人</strong> / <strong>当前负责人</strong>，admin 不能代操作。
        无可用按钮时请 Topbar 切换对应角色，或使用下方改派。
      </div>

      <div style={styles.actionsSection}>
        <div style={styles.actionsHeader}>
          <h4 style={styles.sectionTitle}>可用操作</h4>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => { wf.refresh(); wf.refreshLogs(); }}
            disabled={wf.loading}
          >
            ↻ 刷新
          </button>
        </div>

        {wf.transitions.length === 0 ? (
          <div style={styles.noActions}>
            当前身份下没有可执行的操作
          </div>
        ) : (
          <div style={styles.actionGrid}>
            {wf.transitions.map((transition) => {
              const btnStyle = getActionButtonStyle(transition.action);
              return (
                <button
                  key={`${transition.action}-${transition.to_state}`}
                  type="button"
                  style={{
                    ...styles.actionBtn,
                    backgroundColor: btnStyle.bg,
                    color: btnStyle.color,
                    borderColor: btnStyle.border,
                  }}
                  onClick={() => setTransitionModal({ open: true, transition })}
                  disabled={wf.transitioning}
                >
                  <span style={styles.actionName}>
                    {WORKFLOW_ACTION_LABELS[transition.action] || transition.action}
                  </span>
                  <span style={styles.actionArrow}>
                    → {getStateLabel(transition.to_state, typeCode)}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {showReassign && (
        <div style={styles.reassignSection}>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setShowReassignForm((v) => !v)}
          >
            {showReassignForm ? '收起改派' : '↪ 改派负责人（测试用）'}
          </button>
          {showReassignForm && (
            <div style={styles.reassignForm}>
              <div style={styles.quickChips}>
                {SWITCHABLE_USERS.map((user) => (
                  <button
                    key={user.userId}
                    type="button"
                    style={{
                      ...styles.chip,
                      ...(reassignUserId === user.userId ? styles.chipActive : {}),
                    }}
                    onClick={() => setReassignUserId(user.userId)}
                  >
                    {user.label}
                  </button>
                ))}
              </div>
              <input
                className="form-input"
                placeholder="或输入 user_id"
                value={reassignUserId}
                onChange={(e) => setReassignUserId(e.target.value)}
                style={{ marginTop: '8px' }}
              />
              <input
                className="form-input"
                placeholder="备注（可选）"
                value={reassignRemark}
                onChange={(e) => setReassignRemark(e.target.value)}
                style={{ marginTop: '8px' }}
              />
              <button
                type="button"
                className="btn btn--primary btn--sm"
                style={{ marginTop: '8px' }}
                onClick={handleReassign}
                disabled={wf.reassigning || !reassignUserId.trim()}
              >
                {wf.reassigning ? '改派中...' : '确认改派'}
              </button>
            </div>
          )}
        </div>
      )}

      {showLogs && (
        <WorkflowLogsPanel
          logs={wf.logs}
          loading={wf.logsLoading}
          typeCode={typeCode}
          collapsed={logsCollapsed}
          onToggle={() => setLogsCollapsed((v) => !v)}
        />
      )}

      <WorkflowTransitionModal
        open={transitionModal.open}
        transition={transitionModal.transition ?? null}
        typeCode={typeCode}
        defaultPriority={defaultPriority}
        onClose={() => setTransitionModal({ open: false })}
        onSubmit={handleTransition}
        submitting={wf.transitioning}
      />
    </div>
  );
};

const MetaItem: React.FC<{ label: string; value: React.ReactNode; mono?: boolean }> = ({
  label,
  value,
  mono,
}) => (
  <div style={styles.metaItem}>
    <span style={styles.metaLabel}>{label}</span>
    <span style={mono ? { ...styles.metaValue, fontFamily: 'monospace', fontSize: '11px' } : styles.metaValue}>
      {value}
    </span>
  </div>
);

const styles: Record<string, React.CSSProperties> = {
  root: {},
  compactRoot: {
    fontSize: '13px',
  },
  entityLabel: {
    fontSize: '14px',
    fontWeight: 600,
    marginBottom: '12px',
    color: 'var(--text-primary)',
  },
  hint: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    marginTop: '8px',
  },
  errorBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 12px',
    marginBottom: '12px',
    backgroundColor: 'var(--status-error-bg)',
    color: 'var(--status-error)',
    borderRadius: 'var(--radius-md)',
    fontSize: '13px',
  },
  successBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 12px',
    marginBottom: '12px',
    backgroundColor: 'var(--status-success-bg)',
    color: 'var(--status-success)',
    borderRadius: 'var(--radius-md)',
    fontSize: '13px',
  },
  dismissBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '16px',
    padding: '0 4px',
  },
  metaGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
    gap: '12px',
    marginBottom: '12px',
  },
  metaItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  metaLabel: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase',
    letterSpacing: '0.3px',
  },
  metaValue: {
    fontSize: '13px',
    color: 'var(--text-primary)',
  },
  permissionHint: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    padding: '8px 10px',
    backgroundColor: 'var(--surface-tertiary)',
    borderRadius: 'var(--radius-md)',
    marginBottom: '16px',
    lineHeight: 1.5,
  },
  actionsSection: {
    marginBottom: '12px',
  },
  actionsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  sectionTitle: {
    margin: 0,
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  noActions: {
    padding: '20px',
    textAlign: 'center',
    color: 'var(--text-tertiary)',
    fontSize: '13px',
    backgroundColor: 'var(--surface-tertiary)',
    borderRadius: 'var(--radius-md)',
  },
  actionGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
    gap: '8px',
  },
  actionBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '4px',
    padding: '10px 12px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid',
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'opacity 0.15s',
  },
  actionName: {
    fontSize: '13px',
    fontWeight: 600,
  },
  actionArrow: {
    fontSize: '11px',
    opacity: 0.85,
  },
  reassignSection: {
    marginBottom: '8px',
  },
  reassignForm: {
    marginTop: '10px',
    padding: '12px',
    backgroundColor: 'var(--surface-tertiary)',
    borderRadius: 'var(--radius-md)',
  },
  quickChips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  chip: {
    padding: '4px 10px',
    fontSize: '12px',
    borderRadius: '999px',
    border: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-primary)',
    cursor: 'pointer',
  },
  chipActive: {
    borderColor: 'var(--accent-primary)',
    backgroundColor: 'var(--surface-hover)',
    color: 'var(--accent-primary)',
  },
};

export default WorkflowPanel;
