import React, { useState, useEffect } from 'react';
import { useWorkflow } from '../../hooks/useWorkflow';
import { type WorkflowTypeCode } from '../../constants/workflowLabels';
import WorkflowStateStepper from './WorkflowStateStepper';
import WorkflowLogsPanel from './WorkflowLogsPanel';
import WorkflowActionToolbar from './WorkflowActionToolbar';
import WorkflowCurrentStateBadge from './WorkflowCurrentStateBadge';

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
  /** 为 true 时不渲染右上角操作栏（由父组件在 header 中渲染 WorkflowActionToolbar） */
  hideToolbar?: boolean;
  /** 递增时触发 Panel 内工作流数据刷新（与外部 Toolbar 联动） */
  refreshSignal?: number;
  /** 是否展示 meta 信息网格（ID、负责人等） */
  showMetaGrid?: boolean;
  /** 是否展示权限说明文案 */
  showPermissionHint?: boolean;
  /** 流转历史默认是否折叠 */
  defaultLogsCollapsed?: boolean;
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
  showLogs = false,
  hideToolbar = false,
  refreshSignal,
  showMetaGrid = true,
  showPermissionHint = true,
  defaultLogsCollapsed = false,
}) => {
  const wf = useWorkflow(workflowItemId);
  const [logsCollapsed, setLogsCollapsed] = useState(defaultLogsCollapsed);

  useEffect(() => {
    if (refreshSignal !== undefined && refreshSignal > 0) {
      void wf.refresh();
      void wf.refreshLogs();
    }
    // refreshSignal 是唯一触发源；wf 方法引用稳定
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshSignal]);

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

  const stateBadgeVariant = compact ? 'compact' : 'prominent';

  return (
    <div style={compact ? styles.compactRoot : styles.root}>
      {!hideToolbar && (
        <div style={styles.topBar}>
          <div style={styles.topBarLeft}>
            {entityLabel && <span style={styles.entityLabel}>{entityLabel}</span>}
            {wf.currentState && (
              <WorkflowCurrentStateBadge
                state={wf.currentState}
                typeCode={typeCode}
                variant={stateBadgeVariant}
              />
            )}
          </div>
          <WorkflowActionToolbar
            workflowItemId={workflowItemId}
            typeCode={typeCode}
            defaultPriority={defaultPriority}
            onTransitionSuccess={onTransitionSuccess}
            compact={compact}
            showReassign={showReassign}
          />
        </div>
      )}

      {hideToolbar && entityLabel && (
        <div style={styles.entityLabelOnly}>{entityLabel}</div>
      )}

      {showStepper && (
        <WorkflowStateStepper
          currentState={wf.currentState}
          typeCode={typeCode}
          compact={compact}
        />
      )}

      {showMetaGrid && (
        <div style={styles.metaGrid}>
          <MetaItem label="工作流 ID" value={workflowItemId} mono />
          <MetaItem
            label="当前状态"
            highlight
            value={
              wf.currentState ? (
                <WorkflowCurrentStateBadge
                  state={wf.currentState}
                  typeCode={typeCode}
                  variant={stateBadgeVariant}
                />
              ) : (
                '-'
              )
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
      )}

      {showPermissionHint && (
        <div style={styles.permissionHint}>
          流转权限认<strong>创建人</strong> / <strong>当前负责人</strong>，admin 不能代操作。
          无可用按钮时请 Topbar 切换对应角色，或使用改派。
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
    </div>
  );
};

const MetaItem: React.FC<{ label: string; value: React.ReactNode; mono?: boolean; highlight?: boolean }> = ({
  label,
  value,
  mono,
  highlight,
}) => (
  <div
    className={highlight ? 'workflow-meta-item--current' : undefined}
    style={styles.metaItem}
  >
    <span style={highlight ? styles.metaLabelHighlight : styles.metaLabel}>{label}</span>
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
  topBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 14,
    paddingBottom: 12,
    borderBottom: '1px solid var(--border-subtle)',
    flexWrap: 'wrap',
  },
  topBarLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    flexWrap: 'wrap',
    minWidth: 0,
  },
  entityLabel: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  entityLabelOnly: {
    fontSize: '14px',
    fontWeight: 600,
    marginBottom: 12,
    color: 'var(--text-primary)',
  },
  hint: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    marginTop: '8px',
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
  metaLabelHighlight: {
    fontSize: '11px',
    color: 'var(--accent-primary)',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
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
};

export default WorkflowPanel;
