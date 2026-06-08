import React, { useState, useCallback } from 'react';

interface SingleDispatchModalProps {
  /** 是否打开弹窗 */
  open: boolean;
  /** 用例 ID */
  caseId: string;
  /** 用例标题 */
  caseTitle: string;
  /** 关闭弹窗 */
  onClose: () => void;
  /** 下发成功后的回调 */
  onSuccess: () => void;
}

type DispatchStrategy = 'immediate' | 'scheduled';

/**
 * SingleDispatchModal — 单个自动化用例下发模态框
 * 支持立即执行和定时执行两种策略，包含执行环境、超时、重试等配置。
 */
const SingleDispatchModal: React.FC<SingleDispatchModalProps> = ({
  open, caseId, caseTitle, onClose, onSuccess,
}) => {
  const [strategy, setStrategy] = useState<DispatchStrategy>('immediate');
  const [plannedAt, setPlannedAt] = useState('');
  const [environment, setEnvironment] = useState('staging');
  const [timeout, setTimeout_] = useState(30);
  const [retry, setRetry] = useState(0);
  const [notify, setNotify] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    if (strategy === 'scheduled' && !plannedAt) {
      setError('请选择计划执行时间');
      return;
    }
    setSubmitting(true);
    setError(null);
    await new Promise(r => setTimeout(r, 1200));
    setSubmitting(false);
    setSuccess(true);
    setTimeout(() => {
      onSuccess();
      resetForm();
      onClose();
    }, 2000);
  }, [strategy, plannedAt, onSuccess, onClose]);

  const resetForm = () => {
    setStrategy('immediate');
    setPlannedAt('');
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
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-elevated)', borderRadius: 16, width: 500, maxWidth: '94vw',
        boxShadow: '0 30px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(57,208,214,0.08) 0%, rgba(163,113,247,0.08) 100%)',
          padding: '18px 22px 14px', borderBottom: '1px solid var(--border-subtle)',
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <span style={{ fontSize: 14 }}>⚡</span>
                <span style={{
                  fontSize: 12, fontFamily: 'monospace', color: 'var(--text-tertiary)',
                  background: 'var(--surface-tertiary)', padding: '1px 8px', borderRadius: 4,
                }}>
                  {caseId}
                </span>
                <span style={{
                  fontSize: 11, padding: '1px 8px', borderRadius: 4,
                  background: 'rgba(57,208,214,0.12)', color: '#39d0d6', fontWeight: 600,
                }}>
                  自动化
                </span>
              </div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, lineHeight: 1.4 }}>{caseTitle}</h3>
            </div>
            <button onClick={handleClose} style={{
              fontSize: 22, color: 'var(--text-muted)', background: 'none', border: 'none',
              cursor: 'pointer', padding: 0, lineHeight: 1,
            }}>
              ×
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{
          padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: 16,
          overflowY: 'auto', maxHeight: '50vh',
        }}>
          {/* Strategy */}
          <div>
            <span style={{
              display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 6,
            }}>
              执行策略
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[
                { key: 'immediate' as const, icon: '🚀', title: '立即执行', desc: '不排队，立即下发' },
                { key: 'scheduled' as const, icon: '⏰', title: '定时执行', desc: '指定时间自动触发' },
              ].map(opt => (
                <button
                  key={opt.key}
                  onClick={() => { setStrategy(opt.key); setError(null); }}
                  style={{
                    padding: '10px 12px',
                    border: strategy === opt.key ? '2px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                    borderRadius: 10, cursor: 'pointer', textAlign: 'left',
                    background: strategy === opt.key
                      ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)'
                      : 'var(--bg-primary)',
                  }}
                >
                  <div style={{ fontSize: 15, marginBottom: 1 }}>{opt.icon}</div>
                  <div style={{
                    fontSize: 12, fontWeight: 600,
                    color: strategy === opt.key ? 'var(--accent-primary)' : 'var(--text-primary)',
                  }}>
                    {opt.title}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 1 }}>{opt.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Scheduled time */}
          {strategy === 'scheduled' && (
            <div>
              <span style={{
                display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)',
                textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 4,
              }}>
                计划时间
              </span>
              <input
                type="datetime-local" className="form-input" value={plannedAt}
                onChange={e => { setPlannedAt(e.target.value); setError(null); }}
                style={{ width: '100%', fontSize: 13 }}
              />
            </div>
          )}

          {/* Execution config */}
          <div>
            <span style={{
              display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)',
              textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 6,
            }}>
              执行配置
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 3 }}>
                  环境
                </label>
                <select
                  className="form-input form-select" value={environment}
                  onChange={e => setEnvironment(e.target.value)}
                  style={{ width: '100%', fontSize: 12 }}
                >
                  <option value="staging">🟡 Staging</option>
                  <option value="testing">🔵 Testing</option>
                  <option value="production">🔴 Production</option>
                  <option value="dev">🟢 Dev</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 3 }}>
                  超时
                </label>
                <div style={{ display: 'flex', gap: 4 }}>
                  {[15, 30, 60].map(t => (
                    <button
                      key={t}
                      onClick={() => setTimeout_(t)}
                      style={{
                        flex: 1, padding: '5px 0', fontSize: 11,
                        border: timeout === t ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                        borderRadius: 6, cursor: 'pointer',
                        background: timeout === t ? 'color-mix(in srgb, var(--accent-primary) 8%, transparent)' : 'var(--bg-primary)',
                        color: timeout === t ? 'var(--accent-primary)' : 'var(--text-secondary)',
                        fontWeight: timeout === t ? 600 : 400,
                      }}
                    >
                      {t}min
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 3 }}>
                  重试
                </label>
                <select
                  className="form-input form-select" value={retry}
                  onChange={e => setRetry(Number(e.target.value))}
                  style={{ width: '100%', fontSize: 12 }}
                >
                  <option value={0}>不重试</option>
                  <option value={1}>1 次</option>
                  <option value={2}>2 次</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 3 }}>
                  通知
                </label>
                <select
                  className="form-input form-select" value={notify ? 'on' : 'off'}
                  onChange={e => setNotify(e.target.value === 'on')}
                  style={{ width: '100%', fontSize: 12 }}
                >
                  <option value="on">🔔 通知</option>
                  <option value="off">🔕 静默</option>
                </select>
              </div>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div style={{
              padding: '8px 12px', background: 'rgba(248,81,73,0.08)', borderRadius: 8,
              fontSize: 12, color: '#f85149', display: 'flex', alignItems: 'center', gap: 6,
            }}>
              ⚠️ {error}
            </div>
          )}

          {/* Success */}
          {success && (
            <div style={{
              padding: '12px 14px', background: 'linear-gradient(135deg, rgba(63,185,80,0.1) 0%, rgba(57,208,214,0.06) 100%)',
              borderRadius: 10, border: '1px solid rgba(63,185,80,0.2)', textAlign: 'center',
            }}>
              <div style={{ fontSize: 24, marginBottom: 4 }}>✅</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#3fb950' }}>下发成功</div>
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>
                任务ID: <span style={{ fontFamily: 'monospace', color: 'var(--accent-primary)' }}>TASK-{String(Date.now()).slice(-6)}</span>
              </div>
            </div>
          )}

          {/* History */}
          <div style={{
            padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 8,
            fontSize: 10, color: 'var(--text-tertiary)', lineHeight: 1.8,
          }}>
            <span style={{ fontWeight: 600 }}>📋 历史记录</span>
            <div>TC-003 固件版本升级测试 → <span style={{ color: '#3fb950' }}>✅ 已通过</span>（06-04）</div>
            <div>TC-005 CI/CD 管道集成测试 → <span style={{ color: '#f0883e' }}>⏳ 执行中</span>（06-05）</div>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '12px 22px', borderTop: '1px solid var(--border-subtle)',
          background: 'var(--bg-tertiary)',
        }}>
          <button
            className="btn btn--ghost btn--sm" onClick={handleClose}
            disabled={submitting}
          >
            {success ? '关闭' : '取消'}
          </button>
          <button
            className="btn btn--primary" onClick={handleSubmit}
            disabled={submitting || success}
            style={{ padding: '7px 22px', fontSize: 13, fontWeight: 600 }}
          >
            {submitting ? '下发中...' : success ? '✓ 已完成' : '🚀 确认下发'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SingleDispatchModal;
