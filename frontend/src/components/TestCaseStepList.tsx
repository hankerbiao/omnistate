import React, { useState } from 'react';
import type { TestCaseStep } from '../types';

interface TestCaseStepListProps {
  steps: TestCaseStep[];
  cleanupSteps?: TestCaseStep[];
  emptyMessage?: string;
  showEditHint?: boolean;
}

function StepBlock({ step, index }: { step: TestCaseStep; index: number }) {
  return (
    <div style={styles.stepBlock}>
      <div style={styles.stepHeader}>
        <span style={styles.stepBadge}>{index + 1}</span>
        <span style={styles.stepName}>{step.name}</span>
      </div>
      <div style={styles.fieldsRow}>
        <div style={styles.actionField}>
          <span style={styles.fieldLabel}>动作</span>
          <p style={styles.fieldText}>{step.action}</p>
        </div>
        <div style={styles.expectedField}>
          <span style={styles.fieldLabel}>期望</span>
          <p style={styles.fieldText}>{step.expected}</p>
        </div>
      </div>
    </div>
  );
}

function CleanupStepBlock({ step, index }: { step: TestCaseStep; index: number }) {
  return (
    <div style={styles.cleanupStepBlock}>
      <div style={styles.cleanupStepHeader}>
        <span style={styles.cleanupStepBadge}>{index + 1}</span>
        <span style={styles.cleanupStepName}>{step.name}</span>
        <span style={styles.cleanupStepTag}>清理</span>
      </div>
      <div style={styles.fieldsRow}>
        <div style={styles.cleanupActionField}>
          <span style={styles.fieldLabel}>动作</span>
          <p style={styles.cleanupFieldText}>{step.action}</p>
        </div>
        <div style={styles.cleanupExpectedField}>
          <span style={styles.fieldLabel}>期望</span>
          <p style={styles.cleanupFieldText}>{step.expected}</p>
        </div>
      </div>
    </div>
  );
}

const TestCaseStepList: React.FC<TestCaseStepListProps> = ({
  steps,
  cleanupSteps = [],
  emptyMessage = '尚未配置执行步骤',
  showEditHint = false,
}) => {
  const [cleanupExpanded, setCleanupExpanded] = useState(cleanupSteps.length > 0);

  if (steps.length === 0) {
    return (
      <div style={styles.emptyState}>
        <p style={styles.emptyText}>{emptyMessage}</p>
        {showEditHint && (
          <p style={styles.emptyHint}>点击右上角「编辑」添加执行步骤</p>
        )}
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.sectionHeader}>
        <span style={styles.sectionTitle}>执行步骤 ({steps.length})</span>
      </div>
      <div style={styles.list}>
        {steps.map((step, index) => (
          <StepBlock key={step.step_id} step={step} index={index} />
        ))}
      </div>

      {cleanupSteps.length > 0 && (
        <div style={styles.cleanupSection}>
          <button
            type="button"
            style={styles.cleanupToggle}
            onClick={() => setCleanupExpanded(v => !v)}
            aria-expanded={cleanupExpanded}
          >
            <span style={styles.cleanupChevron} aria-hidden>
              {cleanupExpanded ? '▾' : '▸'}
            </span>
            清理步骤 ({cleanupSteps.length})
          </button>
          {cleanupExpanded && (
            <div style={styles.list}>
              {cleanupSteps.map((step, index) => (
                <CleanupStepBlock key={step.step_id} step={step} index={index} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-3)',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-2)',
  },
  stepBlock: {
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-3)',
    backgroundColor: 'var(--surface-primary)',
  },
  stepHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    marginBottom: 'var(--space-2)',
  },
  stepBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 24,
    height: 24,
    borderRadius: '50%',
    backgroundColor: 'var(--accent-primary)',
    color: 'white',
    fontSize: 11,
    fontWeight: 600,
    flexShrink: 0,
  },
  stepName: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  // ── 动作 + 期望并排 ──
  fieldsRow: {
    display: 'flex',
    gap: 'var(--space-3)',
  },
  actionField: {
    flex: 1,
    minWidth: 0,
  },
  expectedField: {
    flex: 1,
    minWidth: 0,
    padding: 'var(--space-2) var(--space-3)',
    backgroundColor: 'var(--status-success-bg)',
    borderLeft: '3px solid var(--status-success)',
    borderRadius: 'var(--radius-sm)',
  },
  fieldLabel: {
    display: 'block',
    fontSize: 10,
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: 3,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.3px',
  },
  fieldText: {
    margin: 0,
    fontSize: 13,
    color: 'var(--text-primary)',
    whiteSpace: 'pre-wrap',
    lineHeight: 1.5,
  },
  cleanupSection: {
    marginTop: 'var(--space-2)',
    borderTop: '1px solid var(--border-subtle)',
    paddingTop: 'var(--space-3)',
  },
  cleanupToggle: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    border: 'none',
    background: 'transparent',
    padding: 'var(--space-2) 0',
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary)',
    cursor: 'pointer',
    marginBottom: 'var(--space-2)',
  },
  cleanupChevron: {
    fontSize: 12,
    color: 'var(--text-secondary)',
  },
  // ── 清理步骤（警告风格） ──
  cleanupStepBlock: {
    border: '1px solid var(--status-warning)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-3)',
    backgroundColor: 'var(--status-warning-bg)',
  },
  cleanupStepHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    marginBottom: 'var(--space-2)',
  },
  cleanupStepBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 24,
    height: 24,
    borderRadius: '50%',
    backgroundColor: 'var(--status-warning)',
    color: 'white',
    fontSize: 11,
    fontWeight: 600,
    flexShrink: 0,
  },
  cleanupStepName: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--status-warning)',
    flex: 1,
  },
  cleanupStepTag: {
    fontSize: 10,
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 999,
    backgroundColor: 'var(--status-warning)',
    color: 'white',
  },
  cleanupActionField: {
    flex: 1,
    minWidth: 0,
  },
  cleanupExpectedField: {
    flex: 1,
    minWidth: 0,
    padding: 'var(--space-2) var(--space-3)',
    backgroundColor: 'var(--status-warning-bg)',
    borderLeft: '3px solid var(--status-warning)',
    borderRadius: 'var(--radius-sm)',
  },
  cleanupFieldText: {
    margin: 0,
    fontSize: 13,
    color: 'var(--text-primary)',
    whiteSpace: 'pre-wrap',
    lineHeight: 1.5,
  },
  emptyState: {
    padding: 'var(--space-8) var(--space-4)',
    textAlign: 'center',
    border: '1px dashed var(--border-default)',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--surface-secondary)',
  },
  emptyText: {
    margin: 0,
    fontSize: 14,
    color: 'var(--text-secondary)',
  },
  emptyHint: {
    margin: 'var(--space-2) 0 0',
    fontSize: 12,
    color: 'var(--text-tertiary)',
  },
};

export default TestCaseStepList;
