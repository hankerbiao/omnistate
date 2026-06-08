import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useWorkflow, type UseWorkflowResult } from '../../hooks/useWorkflow';
import {
  getStateLabel,
  getActionButtonStyle,
  WORKFLOW_ACTION_LABELS,
  type WorkflowTypeCode,
} from '../../constants/workflowLabels';
import type { WorkflowTransition } from '../../types';
import { SWITCHABLE_USERS } from '../../config/users';
import WorkflowTransitionModal from './WorkflowTransitionModal';
import WorkflowCurrentStateBadge from './WorkflowCurrentStateBadge';

export interface WorkflowActionToolbarProps {
  workflowItemId?: string | null;
  typeCode?: WorkflowTypeCode;
  defaultPriority?: string;
  onTransitionSuccess?: () => void;
  compact?: boolean;
  showRefresh?: boolean;
  showReassign?: boolean;
  /** 左侧展示当前状态徽章 */
  showStateBadge?: boolean;
  /** 为 true 时刷新/改派收入 ⋯ 菜单（由 overflowMenuRender 或内置 WorkflowOverflowMenu 渲染） */
  overflowMenu?: boolean;
  /** 共享 workflow 实例，避免重复请求 */
  workflow?: UseWorkflowResult;
}

export interface WorkflowOverflowMenuProps {
  workflowItemId?: string | null;
  onTransitionSuccess?: () => void;
  showRefresh?: boolean;
  showReassign?: boolean;
  workflow?: UseWorkflowResult;
}

export const WorkflowOverflowMenu: React.FC<WorkflowOverflowMenuProps> = ({
  workflowItemId,
  onTransitionSuccess,
  showRefresh = true,
  showReassign = true,
  workflow: externalWorkflow,
}) => {
  const internalWf = useWorkflow(externalWorkflow ? null : workflowItemId);
  const wf = externalWorkflow ?? internalWf;
  const wrapRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showReassignForm, setShowReassignForm] = useState(false);
  const [reassignUserId, setReassignUserId] = useState('');
  const [reassignRemark, setReassignRemark] = useState('');

  useEffect(() => {
    if (!menuOpen && !showReassignForm) return;
    const onDocClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
        setShowReassignForm(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [menuOpen, showReassignForm]);

  if (!workflowItemId) return null;
  if (!showRefresh && !showReassign) return null;

  const handleRefresh = () => {
    void wf.refresh();
    void wf.refreshLogs();
    setMenuOpen(false);
  };

  const handleReassignClick = () => {
    setShowReassignForm(true);
    setMenuOpen(false);
  };

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

  return (
    <div style={overflowStyles.wrap} ref={wrapRef} onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        className={`btn btn--ghost btn--sm${menuOpen ? ' btn--active' : ''}`}
        onClick={() => setMenuOpen((v) => !v)}
        title="更多操作"
        aria-expanded={menuOpen}
        aria-haspopup="menu"
      >
        ⋯
      </button>

      {menuOpen && (
        <div style={overflowStyles.menu} role="menu">
          {showRefresh && (
            <button
              type="button"
              style={overflowStyles.menuItem}
              role="menuitem"
              onClick={handleRefresh}
              disabled={wf.loading}
            >
              刷新
            </button>
          )}
          {showReassign && (
            <button
              type="button"
              style={overflowStyles.menuItem}
              role="menuitem"
              onClick={handleReassignClick}
            >
              改派
            </button>
          )}
        </div>
      )}

      {showReassignForm && (
        <div style={overflowStyles.reassignPopover}>
          <div style={overflowStyles.reassignTitle}>改派负责人</div>
          <div style={overflowStyles.quickChips}>
            {SWITCHABLE_USERS.map((user) => (
              <button
                key={user.userId}
                type="button"
                style={{
                  ...overflowStyles.chip,
                  ...(reassignUserId === user.userId ? overflowStyles.chipActive : {}),
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
            style={{ marginTop: 8 }}
          />
          <input
            className="form-input"
            placeholder="备注（可选）"
            value={reassignRemark}
            onChange={(e) => setReassignRemark(e.target.value)}
            style={{ marginTop: 8 }}
          />
          <div style={overflowStyles.reassignActions}>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setShowReassignForm(false)}
            >
              取消
            </button>
            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={handleReassign}
              disabled={wf.reassigning || !reassignUserId.trim()}
            >
              {wf.reassigning ? '改派中…' : '确认改派'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const WorkflowActionToolbar: React.FC<WorkflowActionToolbarProps> = ({
  workflowItemId,
  typeCode = 'REQUIREMENT',
  defaultPriority = '',
  onTransitionSuccess,
  compact = false,
  showRefresh = true,
  showReassign = true,
  showStateBadge = false,
  overflowMenu = false,
  workflow: externalWorkflow,
}) => {
  const internalWf = useWorkflow(externalWorkflow ? null : workflowItemId);
  const wf = externalWorkflow ?? internalWf;
  const [transitionModal, setTransitionModal] = useState<{
    open: boolean;
    transition?: WorkflowTransition;
  }>({ open: false });
  const [showReassignForm, setShowReassignForm] = useState(false);
  const [reassignUserId, setReassignUserId] = useState('');
  const [reassignRemark, setReassignRemark] = useState('');

  const handleTransition = useCallback(
    async (formData: Record<string, string>) => {
      if (!transitionModal.transition) return false;
      const ok = await wf.executeTransition(transitionModal.transition.action, formData);
      if (ok) onTransitionSuccess?.();
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

  if (!workflowItemId) return null;

  const stateBadgeVariant = compact ? 'compact' : 'prominent';
  const inlineRefresh = showRefresh && !overflowMenu;
  const inlineReassign = showReassign && !overflowMenu;

  return (
    <div style={styles.wrapper}>
      {(wf.error || wf.successMessage) && (
        <div style={wf.error ? styles.errorBanner : styles.successBanner}>
          <span>{wf.error || wf.successMessage}</span>
          <button type="button" style={styles.dismissBtn} onClick={wf.clearMessages}>×</button>
        </div>
      )}

      <div style={styles.toolbar} onClick={(e) => e.stopPropagation()}>
        {showStateBadge && wf.currentState && (
          <WorkflowCurrentStateBadge
            state={wf.currentState}
            typeCode={typeCode}
            variant={stateBadgeVariant}
            style={{ flexShrink: 0 }}
          />
        )}

        <div style={styles.actions}>
          {wf.loading && !wf.transitions.length ? (
            <span style={styles.loadingHint}>加载操作…</span>
          ) : wf.transitions.length === 0 ? (
            <span style={styles.noActionsHint} title="切换 Topbar 角色或使用改派">
              无可用操作
            </span>
          ) : (
            wf.transitions.map((transition) => {
              const btnStyle = getActionButtonStyle(transition.action);
              return (
                <button
                  key={`${transition.action}-${transition.to_state}`}
                  type="button"
                  className="btn btn--sm"
                  style={{
                    ...styles.actionBtn,
                    backgroundColor: btnStyle.bg,
                    color: btnStyle.color,
                    border: `1px solid ${btnStyle.border}`,
                    padding: compact ? '4px 10px' : '6px 12px',
                    fontSize: compact ? 12 : 13,
                  }}
                  title={`→ ${getStateLabel(transition.to_state, typeCode)}`}
                  onClick={() => setTransitionModal({ open: true, transition })}
                  disabled={wf.transitioning}
                >
                  {WORKFLOW_ACTION_LABELS[transition.action] || transition.action}
                </button>
              );
            })
          )}

          {inlineRefresh && (
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => { wf.refresh(); wf.refreshLogs(); }}
              disabled={wf.loading}
              title="刷新"
              aria-label="刷新工作流"
            >
              ↻
            </button>
          )}

          {inlineReassign && (
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setShowReassignForm((v) => !v)}
              title="改派负责人"
            >
              改派
            </button>
          )}
        </div>
      </div>

      {inlineReassign && showReassignForm && (
        <div style={styles.reassignForm} onClick={(e) => e.stopPropagation()}>
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
            style={{ marginTop: 8 }}
          />
          <input
            className="form-input"
            placeholder="备注（可选）"
            value={reassignRemark}
            onChange={(e) => setReassignRemark(e.target.value)}
            style={{ marginTop: 8 }}
          />
          <button
            type="button"
            className="btn btn--primary btn--sm"
            style={{ marginTop: 8 }}
            onClick={handleReassign}
            disabled={wf.reassigning || !reassignUserId.trim()}
          >
            {wf.reassigning ? '改派中…' : '确认改派'}
          </button>
        </div>
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

const overflowStyles: Record<string, React.CSSProperties> = {
  wrap: {
    position: 'relative',
    flexShrink: 0,
  },
  menu: {
    position: 'absolute',
    top: 'calc(100% + 6px)',
    right: 0,
    minWidth: 120,
    backgroundColor: 'var(--bg-elevated)',
    border: '1px solid var(--border-default)',
    borderRadius: 8,
    boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
    zIndex: 20,
    overflow: 'hidden',
    padding: '4px 0',
  },
  menuItem: {
    display: 'block',
    width: '100%',
    textAlign: 'left',
    padding: '8px 14px',
    fontSize: 13,
    color: 'var(--text-primary)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
  },
  reassignPopover: {
    position: 'absolute',
    top: 'calc(100% + 6px)',
    right: 0,
    width: 320,
    maxWidth: 'min(320px, 90vw)',
    padding: 12,
    backgroundColor: 'var(--bg-elevated)',
    border: '1px solid var(--border-default)',
    borderRadius: 10,
    boxShadow: '0 12px 40px rgba(0,0,0,0.18)',
    zIndex: 20,
  },
  reassignTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: 8,
  },
  reassignActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 8,
    marginTop: 12,
  },
  quickChips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  },
  chip: {
    padding: '4px 10px',
    fontSize: 12,
    borderRadius: 999,
    border: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-primary)',
    cursor: 'pointer',
  },
  chipActive: {
    border: '1px solid var(--accent-primary)',
    backgroundColor: 'var(--surface-hover)',
    color: 'var(--accent-primary)',
  },
};

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: 8,
    minWidth: 0,
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 8,
    flexWrap: 'wrap',
    minWidth: 0,
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 6,
    flexWrap: 'wrap',
  },
  actionBtn: {
    border: '1px solid',
    fontWeight: 600,
    whiteSpace: 'nowrap',
    cursor: 'pointer',
  },
  loadingHint: {
    fontSize: 12,
    color: 'var(--text-tertiary)',
  },
  noActionsHint: {
    fontSize: 12,
    color: 'var(--text-muted)',
    fontStyle: 'italic',
  },
  errorBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 10px',
    backgroundColor: 'var(--status-error-bg)',
    color: 'var(--status-error)',
    borderRadius: 'var(--radius-md)',
    fontSize: 12,
    width: '100%',
    maxWidth: 420,
  },
  successBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 10px',
    backgroundColor: 'var(--status-success-bg)',
    color: 'var(--status-success)',
    borderRadius: 'var(--radius-md)',
    fontSize: 12,
    width: '100%',
    maxWidth: 420,
  },
  dismissBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: 16,
    padding: '0 4px',
  },
  reassignForm: {
    padding: 12,
    backgroundColor: 'var(--surface-tertiary)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-subtle)',
    width: '100%',
    maxWidth: 360,
  },
  quickChips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  },
  chip: {
    padding: '4px 10px',
    fontSize: 12,
    borderRadius: 999,
    border: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-primary)',
    cursor: 'pointer',
  },
  chipActive: {
    border: '1px solid var(--accent-primary)',
    backgroundColor: 'var(--surface-hover)',
    color: 'var(--accent-primary)',
  },
};

export default WorkflowActionToolbar;
