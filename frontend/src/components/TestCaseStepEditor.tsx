import React from 'react';
import type { TestCaseStep } from '../types';

interface TestCaseStepEditorProps {
  steps: TestCaseStep[];
  onChange: (steps: TestCaseStep[]) => void;
  emptyHint?: string;
}

function createEmptyStep(): TestCaseStep {
  return {
    step_id: crypto.randomUUID(),
    name: '',
    action: '',
    expected: '',
  };
}

const TestCaseStepEditor: React.FC<TestCaseStepEditorProps> = ({
  steps,
  onChange,
  emptyHint = '点击下方按钮添加第一步',
}) => {
  const updateStep = (index: number, patch: Partial<TestCaseStep>) => {
    onChange(steps.map((step, i) => (i === index ? { ...step, ...patch } : step)));
  };

  const removeStep = (index: number) => {
    onChange(steps.filter((_, i) => i !== index));
  };

  const moveStep = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= steps.length) return;
    const next = [...steps];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  const addStep = () => {
    onChange([...steps, createEmptyStep()]);
  };

  return (
    <div style={styles.container}>
      {steps.length === 0 ? (
        <div style={styles.emptyState}>
          <p style={styles.emptyText}>{emptyHint}</p>
          <button type="button" className="btn btn--primary btn--sm" onClick={addStep}>
            + 添加第一步
          </button>
        </div>
      ) : (
        <div style={styles.list}>
          {steps.map((step, index) => (
            <div key={step.step_id} style={styles.card}>
              <div style={styles.cardHeader}>
                <div style={styles.cardHeaderLeft}>
                  <span style={styles.stepBadge}>{index + 1}</span>
                  <div style={styles.reorderGroup}>
                    <button
                      type="button"
                      style={styles.reorderBtn}
                      onClick={() => moveStep(index, -1)}
                      disabled={index === 0}
                      aria-label={`上移第 ${index + 1} 步`}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      style={styles.reorderBtn}
                      onClick={() => moveStep(index, 1)}
                      disabled={index === steps.length - 1}
                      aria-label={`下移第 ${index + 1} 步`}
                    >
                      ↓
                    </button>
                  </div>
                </div>
                <button
                  type="button"
                  style={styles.deleteBtn}
                  onClick={() => removeStep(index)}
                  aria-label={`删除第 ${index + 1} 步`}
                >
                  删除
                </button>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>步骤标题</label>
                <input
                  type="text"
                  className="form-input"
                  value={step.name}
                  onChange={e => updateStep(index, { name: e.target.value })}
                  placeholder="如：安装内存、读取 SPD"
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>动作</label>
                <textarea
                  className="form-input"
                  value={step.action}
                  onChange={e => updateStep(index, { action: e.target.value })}
                  placeholder="描述具体操作步骤"
                  rows={3}
                  style={styles.textarea}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>期望</label>
                <textarea
                  className="form-input"
                  value={step.expected}
                  onChange={e => updateStep(index, { expected: e.target.value })}
                  placeholder="描述可观测的通过标准"
                  rows={3}
                  style={{ ...styles.textarea, ...styles.expectedTextarea }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {steps.length > 0 && (
        <button type="button" className="btn btn--secondary btn--sm" onClick={addStep} style={styles.addBtn}>
          + 添加步骤
        </button>
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
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-3)',
  },
  card: {
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-4)',
    backgroundColor: 'var(--surface-primary)',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 'var(--space-3)',
  },
  cardHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
  },
  stepBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 28,
    height: 28,
    borderRadius: '50%',
    backgroundColor: 'var(--accent-primary)',
    color: 'white',
    fontSize: 12,
    fontWeight: 600,
  },
  reorderGroup: {
    display: 'flex',
    gap: 4,
  },
  reorderBtn: {
    minWidth: 44,
    minHeight: 44,
    padding: '0 10px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    backgroundColor: 'var(--surface-secondary)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    fontSize: 14,
  },
  deleteBtn: {
    border: 'none',
    background: 'transparent',
    color: 'var(--status-error)',
    cursor: 'pointer',
    fontSize: 12,
    padding: 'var(--space-2)',
  },
  formGroup: {
    marginBottom: 'var(--space-3)',
  },
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 500,
    color: 'var(--text-secondary)',
    marginBottom: 'var(--space-1)',
  },
  textarea: {
    resize: 'vertical' as const,
    minHeight: 72,
    fontFamily: 'inherit',
  },
  expectedTextarea: {
    backgroundColor: 'var(--status-success-bg)',
    borderLeft: '3px solid var(--status-success)',
  },
  emptyState: {
    border: '1px dashed var(--border-default)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-6)',
    textAlign: 'center',
    backgroundColor: 'var(--surface-secondary)',
  },
  emptyText: {
    margin: '0 0 var(--space-3)',
    fontSize: 13,
    color: 'var(--text-secondary)',
  },
  addBtn: {
    alignSelf: 'flex-start',
  },
};

export default TestCaseStepEditor;
