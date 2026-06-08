import type { CSSProperties } from 'react';
import { getWorkflowStateStyle } from '../../constants/workflowLabels';

export type WorkflowStateBadgeVariant = 'default' | 'compact' | 'prominent';

/** Maps workflow state tokens to valid React inline badge styles. */
export function buildWorkflowStateBadgeStyle(
  state: string,
  variant: WorkflowStateBadgeVariant = 'default',
): CSSProperties {
  const { bg, color } = getWorkflowStateStyle(state);
  const base: CSSProperties = {
    backgroundColor: bg,
    color,
  };

  switch (variant) {
    case 'compact':
      return {
        ...base,
        fontSize: 11,
        fontWeight: 700,
        padding: '3px 10px',
        border: `1px solid ${color}`,
        boxShadow: '0 0 0 2px color-mix(in srgb, currentColor 14%, transparent)',
      };
    case 'prominent':
      return {
        ...base,
        fontSize: 12,
        fontWeight: 700,
        padding: '4px 12px',
        border: `1px solid ${color}`,
        boxShadow: '0 0 0 3px color-mix(in srgb, currentColor 18%, transparent)',
        letterSpacing: '0.02em',
      };
    default:
      return base;
  }
}
