import type { WorkflowTypeCode } from '../../constants/workflowLabels';
import React from 'react';
import {
  getStateLabel,
  WORKFLOW_STATE_PIPELINES,
} from '../../constants/workflowLabels';
import WorkflowCurrentStateBadge from './WorkflowCurrentStateBadge';

interface WorkflowStateStepperProps {
  currentState: string;
  typeCode: WorkflowTypeCode;
  compact?: boolean;
}

const WorkflowStateStepper: React.FC<WorkflowStateStepperProps> = ({
  currentState,
  typeCode,
  compact = false,
}) => {
  const pipeline = WORKFLOW_STATE_PIPELINES[typeCode];
  const currentIndex = pipeline.indexOf(currentState);

  return (
    <div style={styles.wrapper}>
      {currentState && (
        <div style={compact ? styles.currentHeaderCompact : styles.currentHeader}>
          <span style={styles.currentHeaderLabel}>当前状态</span>
          <WorkflowCurrentStateBadge
            state={currentState}
            typeCode={typeCode}
            variant={compact ? 'compact' : 'prominent'}
          />
        </div>
      )}

      <div style={styles.track}>
        {pipeline.map((state, index) => {
          const isPast = currentIndex >= 0 && index < currentIndex;
          const isCurrent = state === currentState;
          const isFuture = currentIndex >= 0 ? index > currentIndex : false;

          return (
            <div
              key={state}
              className={
                isCurrent
                  ? compact
                    ? 'workflow-stepper-step--current workflow-stepper-step--current-compact'
                    : 'workflow-stepper-step--current'
                  : undefined
              }
              style={styles.step}
            >
              <div
                className={isCurrent ? 'workflow-stepper-dot--current' : undefined}
                style={{
                  ...styles.dot,
                  ...(isCurrent ? styles.dotCurrent : {}),
                  ...(isPast ? styles.dotPast : {}),
                  ...(isFuture ? styles.dotFuture : {}),
                  ...(compact && isCurrent ? styles.dotCurrentCompact : {}),
                }}
                title={state}
              />
              <span
                style={{
                  ...styles.label,
                  ...(isCurrent ? (compact ? styles.labelCurrentCompact : styles.labelCurrent) : {}),
                  ...(isPast ? styles.labelPast : {}),
                }}
              >
                {isCurrent && <span style={styles.currentMarker}>● </span>}
                {getStateLabel(state, typeCode)}
              </span>
              {index < pipeline.length - 1 && (
                <div
                  style={{
                    ...styles.connector,
                    ...(compact ? styles.connectorCompact : {}),
                    ...(isPast ? styles.connectorPast : {}),
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
      {!pipeline.includes(currentState) && currentState && (
        <div style={styles.offPipeline}>
          当前状态{' '}
          <WorkflowCurrentStateBadge
            state={currentState}
            typeCode={typeCode}
            variant="compact"
            style={{ verticalAlign: 'middle', marginLeft: 4 }}
          />{' '}
          不在标准主路径上（可能为驳回回退等分支）
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    marginBottom: '16px',
    padding: '12px 14px',
    backgroundColor: 'var(--surface-tertiary)',
    borderRadius: 'var(--radius-md)',
    overflowX: 'auto',
  },
  currentHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '12px',
    paddingBottom: '10px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  currentHeaderCompact: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '10px',
    paddingBottom: '8px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  currentHeaderLabel: {
    fontSize: '11px',
    fontWeight: 700,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
  },
  track: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0',
    minWidth: 'max-content',
  },
  step: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    position: 'relative',
    minWidth: '72px',
    flex: '0 0 auto',
  },
  dot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: 'var(--border-subtle)',
    border: '2px solid var(--border-subtle)',
    marginBottom: '6px',
    zIndex: 1,
  },
  dotCurrent: {
    width: '16px',
    height: '16px',
    backgroundColor: 'var(--accent-primary)',
    border: '2px solid var(--accent-primary)',
    boxShadow: '0 0 0 3px color-mix(in srgb, var(--accent-primary) 28%, transparent)',
  },
  dotCurrentCompact: {
    width: '14px',
    height: '14px',
  },
  dotPast: {
    backgroundColor: 'var(--status-success)',
    border: '2px solid var(--status-success)',
  },
  dotFuture: {
    backgroundColor: 'transparent',
  },
  label: {
    fontSize: '10px',
    color: 'var(--text-tertiary)',
    textAlign: 'center',
    lineHeight: 1.3,
    maxWidth: '68px',
  },
  labelCurrent: {
    color: 'var(--accent-primary)',
    fontWeight: 700,
    fontSize: '11px',
    maxWidth: '76px',
  },
  labelCurrentCompact: {
    color: 'var(--accent-primary)',
    fontWeight: 700,
    fontSize: '10px',
  },
  currentMarker: {
    color: 'var(--accent-primary)',
    fontSize: '8px',
  },
  labelPast: {
    color: 'var(--text-secondary)',
  },
  connector: {
    position: 'absolute',
    top: '7px',
    left: 'calc(50% + 10px)',
    width: 'calc(100% - 20px)',
    height: '2px',
    backgroundColor: 'var(--border-subtle)',
    zIndex: 0,
  },
  connectorCompact: {
    top: '6px',
    left: 'calc(50% + 9px)',
    width: 'calc(100% - 18px)',
  },
  connectorPast: {
    backgroundColor: 'var(--status-success)',
  },
  offPipeline: {
    marginTop: '10px',
    fontSize: '11px',
    color: 'var(--status-warning)',
    display: 'flex',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '4px',
  },
};

export default WorkflowStateStepper;
