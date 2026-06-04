import type { WorkflowTypeCode } from '../../constants/workflowLabels';
import React from 'react';
import {
  getStateLabel,
  WORKFLOW_STATE_PIPELINES,
} from '../../constants/workflowLabels';

interface WorkflowStateStepperProps {
  currentState: string;
  typeCode: WorkflowTypeCode;
}

const WorkflowStateStepper: React.FC<WorkflowStateStepperProps> = ({
  currentState,
  typeCode,
}) => {
  const pipeline = WORKFLOW_STATE_PIPELINES[typeCode];
  const currentIndex = pipeline.indexOf(currentState);

  return (
    <div style={styles.wrapper}>
      <div style={styles.track}>
        {pipeline.map((state, index) => {
          const isPast = currentIndex >= 0 && index < currentIndex;
          const isCurrent = state === currentState;
          const isFuture = currentIndex >= 0 ? index > currentIndex : false;

          return (
            <div key={state} style={styles.step}>
              <div
                style={{
                  ...styles.dot,
                  ...(isCurrent ? styles.dotCurrent : {}),
                  ...(isPast ? styles.dotPast : {}),
                  ...(isFuture ? styles.dotFuture : {}),
                }}
                title={state}
              />
              <span
                style={{
                  ...styles.label,
                  ...(isCurrent ? styles.labelCurrent : {}),
                  ...(isPast ? styles.labelPast : {}),
                }}
              >
                {getStateLabel(state, typeCode)}
              </span>
              {index < pipeline.length - 1 && (
                <div
                  style={{
                    ...styles.connector,
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
          当前状态 <strong>{getStateLabel(currentState, typeCode)}</strong> 不在标准主路径上（可能为驳回回退等分支）
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
    width: '14px',
    height: '14px',
    backgroundColor: 'var(--accent-primary)',
    borderColor: 'var(--accent-primary)',
    boxShadow: '0 0 0 3px rgba(59, 130, 246, 0.25)',
  },
  dotPast: {
    backgroundColor: 'var(--status-success)',
    borderColor: 'var(--status-success)',
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
    fontWeight: 600,
  },
  labelPast: {
    color: 'var(--text-secondary)',
  },
  connector: {
    position: 'absolute',
    top: '5px',
    left: 'calc(50% + 8px)',
    width: 'calc(100% - 16px)',
    height: '2px',
    backgroundColor: 'var(--border-subtle)',
    zIndex: 0,
  },
  connectorPast: {
    backgroundColor: 'var(--status-success)',
  },
  offPipeline: {
    marginTop: '10px',
    fontSize: '11px',
    color: 'var(--status-warning)',
  },
};

export default WorkflowStateStepper;
