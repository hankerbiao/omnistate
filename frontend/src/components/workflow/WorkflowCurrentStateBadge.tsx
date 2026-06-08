import React, { type CSSProperties } from 'react';
import { getStateLabel, type WorkflowTypeCode } from '../../constants/workflowLabels';
import {
  buildWorkflowStateBadgeStyle,
  type WorkflowStateBadgeVariant,
} from './workflowStateStyles';

export interface WorkflowCurrentStateBadgeProps {
  state: string;
  typeCode: WorkflowTypeCode;
  variant?: WorkflowStateBadgeVariant;
  /** Adds subtle pulse/glow animation */
  animated?: boolean;
  className?: string;
  style?: CSSProperties;
}

const WorkflowCurrentStateBadge: React.FC<WorkflowCurrentStateBadgeProps> = ({
  state,
  typeCode,
  variant = 'prominent',
  animated = true,
  className,
  style,
}) => {
  const badgeClass = [
    'status-badge',
    animated ? 'status-badge--current' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <span
      className={badgeClass}
      style={{ ...buildWorkflowStateBadgeStyle(state, variant), ...style }}
    >
      {getStateLabel(state, typeCode)}
    </span>
  );
};

export default WorkflowCurrentStateBadge;
