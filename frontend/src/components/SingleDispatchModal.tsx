import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { PlanItemDispatchRequest, AutomationConfigField } from '../types';

interface Props {
  open: boolean;
  itemId: string;
  caseId: string;
  caseTitle: string;
  onClose: () => void;
  onSuccess: () => void;
}

type Strategy = 'immediate' | 'scheduled';

const SingleDispatchModal: React.FC<Props> = ({
  open, itemId, caseId, caseTitle, onClose, onSuccess,
}) => {
  const [strategy, setStrategy] = useState<Strategy>('immediate');
  const [plannedAt, setPlannedAt] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto case details
  const [autoCase, setAutoCase] = useState<{
    repo_url?: string | null;
    branch?: string | null;
    timeout?: number | null;
    param_spec?: AutomationConfigField[];
  } | null>(null);
  const [loadingCase, setLoadingCase] = useState(false);
  const [paramValues, setParamValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) return;
    setLoadingCase(true);
    setError(null);
    setAutoCase(null);
    setParamValues({});
    api.listAutomationTestCases({ limit: 200 })
      .then(res => {
        const found = (res.data || []).find((tc: any) => tc.auto_case_id === caseId);
        if (found) {
          setAutoCase({
            repo_url: found.repo_url,
            branch: found.repo_branch || found.code_snapshot?.branch,
            timeout: found.report_meta?.timeout,
            param_spec: found.param_spec,
          });
          // Init default values from param_spec
          if (found.param_spec) {
            const init: Record<string, string> = {};
            for (const p of found.param_spec) {
              init[p.name] = p.default != null ? String(p.default) : '';
            }
            setParamValues(init);
          }
        }
      })
      .catch(() => setError('获取用例详情失败'))
      .finally(() => setLoadingCase(false));
  }, [open, caseId]);

  const resetForm = () => {
    setStrategy('immediate');
    setPlannedAt('');
    setSubmitting(false);
    setSuccess(false);
    setError(null);
    setAutoCase(null);
    setParamValues({});
  };

  const renderConfigField = (p: AutomationConfigField) => {
    const val = paramValues[p.name] ?? '';
    const setVal = (v: string) => setParamValues(prev => ({ ...prev, [p.name]: v }));

    const fieldStyle = { padding: '4px 8px', fontSize: 12, width: '100%', boxSizing: 'border-box' as const };

    // Select with options
    if (p.options && p.options.length > 0) {
      return (
        <select className="form-input form-select" style={fieldStyle} value={val} onChange={e => setVal(e.target.value)}>
          <option value="">{p.required ? '请选择' : '可选'}</option>
          {p.options.map((opt: any) => (
            <option key={opt.value} value={String(opt.value)}>{opt.label || opt.value}</option>
          ))}
        </select>
      );
    }

    // Boolean
    if (p.type === 'bool' || p.type === 'boolean') {
      return (
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12 }}>
          <input type="checkbox" checked={val === 'true'} onChange={e => setVal(e.target.checked ? 'true' : 'false')} />
          {val === 'true' ? '是' : '否'}
        </label>
      );
    }

    // Number
    if (p.type === 'int' || p.type === 'float' || p.type === 'number') {
      return <input type="number" className="form-input" style={fieldStyle} value={val} onChange={e => setVal(e.target.value)} placeholder={p.description || ''} />;
    }

    // Text / default
    return <input type="text" className="form-input" style={fieldStyle} value={val} onChange={e => setVal(e.target.value)} placeholder={p.description || p.label || ''} />;
  };

  const handleSubmit = useCallback(async () => {
    if (strategy === 'scheduled' && !plannedAt) {
      setError('请选择计划执行时间');
      return;
    }

    setSubmitting(true);
    setError(null);

    const request: PlanItemDispatchRequest = {
      schedule_type: strategy === 'scheduled' ? 'SCHEDULED' : 'IMMEDIATE',
      planned_at: strategy === 'scheduled' && plannedAt
        ? new Date(plannedAt).toISOString()
        : undefined,
      repo_url: autoCase?.repo_url || undefined,
      branch: autoCase?.branch || undefined,
      timeout: autoCase?.timeout || undefined,
    };

    // Per-case parameters
    if (autoCase?.param_spec && autoCase.param_spec.length > 0) {
      const parameters: Record<string, string> = {};
      for (const p of autoCase.param_spec) {
        const val = paramValues[p.name];
        if (val) parameters[p.name] = val;
      }
      if (Object.keys(parameters).length > 0) {
        request.parameters = parameters;
      }
    }

    try {
      await api.dispatchPlanItem(itemId, request);
      setSubmitting(false);
      setSuccess(true);
      setTimeout(() => {
        onSuccess();
        resetForm();
        onClose();
      }, 2000);
    } catch (err) {
      setSubmitting(false);
      setError(err instanceof Error ? err.message : '下发失败，请重试');
    }
  }, [strategy, plannedAt, autoCase, paramValues, itemId, onSuccess, onClose]);

  const handleClose = () => { resetForm(); onClose(); };

  if (!open) return null;

  const hasParams = autoCase?.param_spec && autoCase.param_spec.length > 0;

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-elevated)', borderRadius: 16, width: 560, maxWidth: '94vw',
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
                <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-tertiary)', background: 'var(--surface-tertiary)', padding: '1px 8px', borderRadius: 4 }}>{caseId}</span>
                <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 4, background: 'rgba(57,208,214,0.12)', color: '#39d0d6', fontWeight: 600 }}>自动化</span>
              </div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, lineHeight: 1.4 }}>{caseTitle}</h3>
            </div>
            <button onClick={handleClose} style={{ fontSize: 22, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, lineHeight: 1 }}>×</button>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: 16, overflowY: 'auto', maxHeight: '60vh' }}>
          {loadingCase ? (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>加载用例配置...</div>
          ) : (
            <>
              {/* ── Strategy ── */}
              <div>
                <span style={{ display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 6 }}>执行策略</span>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {[
                    { key: 'immediate' as const, icon: '🚀', title: '立即执行', desc: '不排队，立即下发' },
                    { key: 'scheduled' as const, icon: '⏰', title: '定时执行', desc: '指定时间自动触发' },
                  ].map(opt => (
                    <button key={opt.key} onClick={() => { setStrategy(opt.key); setError(null); }} style={{
                      padding: '10px 12px',
                      border: strategy === opt.key ? '2px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                      borderRadius: 10, cursor: 'pointer', textAlign: 'left',
                      background: strategy === opt.key ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--bg-primary)',
                    }}>
                      <div style={{ fontSize: 15, marginBottom: 1 }}>{opt.icon}</div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: strategy === opt.key ? 'var(--accent-primary)' : 'var(--text-primary)' }}>{opt.title}</div>
                      <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 1 }}>{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {strategy === 'scheduled' && (
                <div>
                  <span style={{ display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 4 }}>计划时间</span>
                  <input type="datetime-local" className="form-input" value={plannedAt} onChange={e => { setPlannedAt(e.target.value); setError(null); }} style={{ width: '100%', fontSize: 13 }} />
                </div>
              )}

              {/* ── Execution config from auto case ── */}
              {autoCase && (
                <div>
                  <span style={{ display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 6 }}>执行配置</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {autoCase.repo_url && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-tertiary)', width: 70, flexShrink: 0 }}>仓库地址</span>
                        <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{autoCase.repo_url}</span>
                      </div>
                    )}
                    {autoCase.branch && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-tertiary)', width: 70, flexShrink: 0 }}>分支</span>
                        <span style={{ fontSize: 12, color: 'var(--text-primary)' }}>{autoCase.branch}</span>
                      </div>
                    )}
                    {autoCase.timeout != null && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-tertiary)', width: 70, flexShrink: 0 }}>超时(秒)</span>
                        <span style={{ fontSize: 12, color: 'var(--text-primary)' }}>{autoCase.timeout}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── Per-case parameters from param_spec ── */}
              {hasParams && (
                <div>
                  <span style={{ display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 6 }}>参数配置</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {autoCase!.param_spec!.map(p => (
                      <div key={p.name} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-tertiary)', width: 90, flexShrink: 0, paddingTop: 5 }}>{p.label || p.name}{p.required ? ' *' : ''}</span>
                        <div style={{ flex: 1 }}>{renderConfigField(p)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Error */}
              {error && (
                <div style={{ padding: '8px 12px', background: 'rgba(248,81,73,0.08)', borderRadius: 8, fontSize: 12, color: '#f85149', display: 'flex', alignItems: 'center', gap: 6 }}>
                  ⚠️ {error}
                </div>
              )}

              {/* Success */}
              {success && (
                <div style={{ padding: '12px 14px', background: 'linear-gradient(135deg, rgba(63,185,80,0.1) 0%, rgba(57,208,214,0.06) 100%)', borderRadius: 10, border: '1px solid rgba(63,185,80,0.2)', textAlign: 'center' }}>
                  <div style={{ fontSize: 24, marginBottom: 4 }}>✅</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#3fb950' }}>下发成功</div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>任务已提交到执行引擎</div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 22px', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-tertiary)' }}>
          <button className="btn btn--ghost btn--sm" onClick={handleClose} disabled={submitting}>
            {success ? '关闭' : '取消'}
          </button>
          <button className="btn btn--primary" onClick={handleSubmit} disabled={submitting || success || loadingCase} style={{ padding: '7px 22px', fontSize: 13, fontWeight: 600 }}>
            {submitting ? '下发中...' : success ? '✓ 已完成' : '🚀 确认下发'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SingleDispatchModal;
