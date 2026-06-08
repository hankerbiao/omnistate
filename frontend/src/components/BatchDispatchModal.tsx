import React, { useState, useCallback } from 'react';
import type { PlanTask } from './myTasksTypes';
import { STATUS_COLORS } from './myTasksTypes';

interface BatchDispatchModalProps {
  /** 是否打开弹窗 */
  open: boolean;
  /** 可选的自动化用例列表 */
  autoTasks: PlanTask[];
  /** 关闭弹窗 */
  onClose: () => void;
  /** 提交批量下发 */
  onSubmit: (caseIds: string[]) => void;
}

/**
 * BatchDispatchModal — 批量下发自动化用例模态框
 * 支持选择多个自动化用例，统一设置执行配置后批量下发。
 */
const BatchDispatchModal: React.FC<BatchDispatchModalProps> = ({
  open, autoTasks, onClose, onSubmit,
}) => {
  const [caseIds, setCaseIds] = useState<string[]>(() => autoTasks.map(t => t.caseId));
  const [environment, setEnvironment] = useState('staging');
  const [timeout, setTimeout_] = useState(30);
  const [retry, setRetry] = useState(0);
  const [notify, setNotify] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 当 autoTasks 变化时同步更新 caseIds
  React.useEffect(() => {
    if (open) {
      setCaseIds(autoTasks.map(t => t.caseId));
    }
  }, [open, autoTasks]);

  const toggleCase = useCallback((caseId: string) => {
    setCaseIds(prev =>
      prev.includes(caseId)
        ? prev.filter(c => c !== caseId)
        : [...prev, caseId],
    );
  }, []);

  const toggleAll = useCallback(() => {
    const allIds = autoTasks.map(t => t.caseId);
    setCaseIds(prev => (prev.length === allIds.length ? [] : allIds));
  }, [autoTasks]);

  const handleSubmit = useCallback(async () => {
    if (caseIds.length === 0) {
      setError('请至少选择一个用例');
      return;
    }
    setSubmitting(true);
    setError(null);
    await new Promise(r => setTimeout(r, 1500));
    onSubmit(caseIds);
    setSubmitting(false);
    setSuccess(true);
    setTimeout(() => {
      resetForm();
      onClose();
    }, 2000);
  }, [caseIds, onSubmit, onClose]);

  const resetForm = () => {
    setCaseIds(autoTasks.map(t => t.caseId));
    setEnvironment('staging');
    setTimeout_(30);
    setRetry(0);
    setNotify(true);
    setSuccess(false);
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!open) return null;

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-elevated)', borderRadius: 16, width: 640, maxWidth: '94vw',
        maxHeight: '88vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 30px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)',
      }}>
        {/* Header */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(57,208,214,0.08) 0%, rgba(163,113,247,0.08) 100%)',
          padding: '18px 24px 14px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>⚡ 批量下发自动化用例</h3>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>
                已选 <strong style={{ color: 'var(--accent-primary)' }}>{caseIds.length}</strong> 个用例 · 全部下发到执行队列
              </p>
            </div>
            <button onClick={handleClose} style={{
              fontSize: 24, color: 'var(--text-muted)', background: 'none', border: 'none',
              cursor: 'pointer', padding: 0, lineHeight: 1,
            }}>
              ×
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{
          flex: 1, overflowY: 'auto', padding: '16px 24px',
          display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          {/* Batch config bar */}
          <div style={{
            display: 'flex', gap: 10, flexWrap: 'wrap', padding: '10px 14px',
            background: 'var(--bg-secondary)', borderRadius: 10,
            border: '1px solid var(--border-subtle)', alignItems: 'center',
          }}>
            <span style={{
              fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.3px',
            }}>
              批量设置
            </span>
            <div style={{ width: 1, height: 20, background: 'var(--border-subtle)' }} />
            <select
              className="form-input form-select" value={environment}
              onChange={e => setEnvironment(e.target.value)}
              style={{ width: 130, fontSize: 11 }}
            >
              <option value="staging">🟡 Staging</option>
              <option value="testing">🔵 Testing</option>
              <option value="production">🔴 Production</option>
              <option value="dev">🟢 Dev</option>
            </select>
            <div style={{ display: 'flex', gap: 3 }}>
              {[15, 30, 60].map(t => (
                <button
                  key={t}
                  onClick={() => setTimeout_(t)}
                  style={{
                    padding: '3px 8px', fontSize: 10,
                    border: timeout === t ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                    borderRadius: 5, cursor: 'pointer',
                    background: timeout === t ? 'color-mix(in srgb, var(--accent-primary) 8%, transparent)' : 'var(--bg-primary)',
                    color: timeout === t ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    fontWeight: timeout === t ? 600 : 400,
                  }}
                >
                  {t}min
                </button>
              ))}
            </div>
            <select
              className="form-input form-select" value={retry}
              onChange={e => setRetry(Number(e.target.value))}
              style={{ width: 80, fontSize: 11 }}
            >
              <option value={0}>不重试</option>
              <option value={1}>重试 1×</option>
              <option value={2}>重试 2×</option>
            </select>
            <select
              className="form-input form-select" value={notify ? 'on' : 'off'}
              onChange={e => setNotify(e.target.value === 'on')}
              style={{ width: 80, fontSize: 11 }}
            >
              <option value="on">🔔 通知</option>
              <option value="off">🔕 静默</option>
            </select>
          </div>

          {/* Case list */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', fontSize: 11, color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  checked={caseIds.length === autoTasks.length}
                  onChange={toggleAll}
                  style={{ accentColor: 'var(--accent-primary)' }}
                />
                全选
              </label>
              <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{caseIds.length} 个已选</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {autoTasks.map(task => {
                const checked = caseIds.includes(task.caseId);
                return (
                  <label
                    key={task.id}
                    onClick={() => toggleCase(task.caseId)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                      borderRadius: 8, cursor: 'pointer',
                      border: checked ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                      background: checked ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'var(--bg-primary)',
                      transition: 'all 0.1s',
                    }}
                  >
                    <input type="checkbox" checked={checked} onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--accent-cyan)', minWidth: 55 }}>
                      {task.caseId}
                    </span>
                    <span style={{ flex: 1, fontSize: 13, fontWeight: checked ? 600 : 500 }}>
                      {task.caseTitle}
                    </span>
                    <span style={{
                      fontSize: 10, padding: '1px 8px', borderRadius: 4,
                      background: 'rgba(57,208,214,0.12)', color: '#39d0d6', fontWeight: 600,
                    }}>
                      ⚡ 自动化
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{task.component}</span>
                    <span style={{
                      fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 8,
                      color: STATUS_COLORS[task.status], background: `${STATUS_COLORS[task.status]}15`,
                    }}>
                      {task.status === 'running' ? '▶ 执行中' : '○ 待执行'}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div style={{
              padding: '8px 12px', background: 'rgba(248,81,73,0.08)', borderRadius: 8,
              fontSize: 12, color: '#f85149',
            }}>
              ⚠️ {error}
            </div>
          )}

          {/* Success */}
          {success && (
            <div style={{
              padding: '14px 16px', background: 'linear-gradient(135deg, rgba(63,185,80,0.1) 0%, rgba(57,208,214,0.06) 100%)',
              borderRadius: 10, border: '1px solid rgba(63,185,80,0.2)', textAlign: 'center',
            }}>
              <div style={{ fontSize: 28, marginBottom: 4 }}>✅</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#3fb950' }}>批量下发成功</div>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 4 }}>
                {caseIds.length} 个用例已进入执行队列
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '12px 24px', borderTop: '1px solid var(--border-subtle)',
          background: 'var(--bg-tertiary)', flexShrink: 0,
        }}>
          <button
            className="btn btn--ghost btn--sm" onClick={handleClose}
            disabled={submitting}
          >
            取消
          </button>
          <button
            className="btn btn--primary" onClick={handleSubmit}
            disabled={submitting || caseIds.length === 0 || success}
            style={{ padding: '8px 24px', fontSize: 13, fontWeight: 600 }}
          >
            {submitting ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  width: 12, height: 12, border: '2px solid rgba(255,255,255,0.3)',
                  borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block',
                  animation: 'spin 0.6s linear infinite',
                }} />
                下发 {caseIds.length} 个...
              </span>
            ) : success ? '✓ 已完成' : `🚀 下发 ${caseIds.length} 个`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default BatchDispatchModal;
