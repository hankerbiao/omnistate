import { useState, useEffect } from 'react';
import type { AutomationTestCaseResponse, ExecutionStatsResponse } from '../types';
import { api } from '../services/api';

interface Props {
  testCase: AutomationTestCaseResponse;
  onClose: () => void;
}

/** 单行键值对 */
function Field({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div style={st.field}>
      <span style={st.fieldLabel}>{label}</span>
      <span style={{ ...st.fieldValue, fontFamily: mono ? "'JetBrains Mono', monospace" : 'inherit' }}>{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={st.section}>
      <div style={st.sectionTitle}>{title}</div>
      <div style={st.sectionBody}>{children}</div>
    </div>
  );
}

export default function AutomationCaseDetailModal({ testCase: tc, onClose }: Props) {
  const isProd = tc.status === 'active' || tc.status === 'released';
  const [execStats, setExecStats] = useState<ExecutionStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  useEffect(() => {
    setStatsLoading(true);
    api.getCaseExecutionStats(tc.auto_case_id)
      .then(res => setExecStats(res.data))
      .catch(() => setExecStats(null))
      .finally(() => setStatsLoading(false));
  }, [tc.auto_case_id]);

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--overlay-bg)', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'center', backdropFilter: 'blur(2px)' }}
      onClick={onClose}>
      <div style={st.modal} onClick={e => e.stopPropagation()}>
        {/* ── Header ── */}
        <div style={st.header}>
          <div style={st.headerLeft}>
            <span style={st.badge}>AUTO</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: 'var(--text-tertiary)' }}>{tc.auto_case_id}</span>
            <span style={{
              ...st.statusBadge,
              backgroundColor: isProd ? 'rgba(63,185,80,0.12)' : 'rgba(88,166,255,0.12)',
              color: isProd ? '#3fb950' : '#58a6ff',
            }}>{tc.status}</span>
          </div>
          <button onClick={onClose} style={st.closeBtn}>x</button>
        </div>

        <div style={st.title}>{tc.name}</div>

        {/* ── Body: 2-column ── */}
        <div style={st.body}>
          {/* ── Left sidebar ── */}
          <div style={st.left}>
            {tc.maintainer_id && (
              <Field label="维护人" value={<span style={{ fontWeight: 500 }}>{tc.maintainer_id}</span>} />
            )}
            {tc.reviewer_id && (
              <Field label="评审人" value={<span style={{ fontWeight: 500 }}>{tc.reviewer_id}</span>} />
            )}
            {tc.version && <Field label="版本" value={tc.version} />}
            {tc.framework && <Field label="框架" value={tc.framework} />}
            {tc.automation_type && <Field label="类型" value={tc.automation_type} />}
            {tc.tags && tc.tags.length > 0 && (
              <div style={st.field}>
                <span style={st.fieldLabel}>标签</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {tc.tags.map(t => (
                    <span key={t} style={{ fontSize: 11, padding: '1px 7px', borderRadius: 999, background: 'var(--surface-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>{t}</span>
                  ))}
                </div>
              </div>
            )}
            <Section title="元数据">
              <Field label="创建时间" value={new Date(tc.created_at).toLocaleString('zh-CN')} />
              <Field label="更新时间" value={new Date(tc.updated_at).toLocaleString('zh-CN')} />
              {tc.report_meta?.timeout != null && (
                <Field label="超时(秒)" value={tc.report_meta.timeout} />
              )}
            </Section>
          </div>

          {/* ── Right main ── */}
          <div style={st.right}>
            {tc.description && (
              <Section title="描述">
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{tc.description}</div>
              </Section>
            )}

            <Section title="脚本信息">
              {tc.repo_url && <Field label="仓库" value={tc.repo_url} mono />}
              {tc.repo_branch && <Field label="分支" value={tc.repo_branch} />}
              {tc.script_path && <Field label="脚本路径" value={tc.script_path} mono />}
              {tc.script_name && <Field label="脚本名称" value={tc.script_name} />}
              {tc.entry_command && <Field label="入口命令" value={tc.entry_command} mono />}
              {tc.script_entity_id && <Field label="脚本实体ID" value={tc.script_entity_id} mono />}
            </Section>

            {(tc.param_spec && tc.param_spec.length > 0) && (
              <Section title="参数规格">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-tertiary)' }}>
                      <th style={{ padding: '4px 6px', textAlign: 'left', fontWeight: 500 }}>参数</th>
                      <th style={{ padding: '4px 6px', textAlign: 'left', fontWeight: 500 }}>类型</th>
                      <th style={{ padding: '4px 6px', textAlign: 'left', fontWeight: 500 }}>是否必填</th>
                      <th style={{ padding: '4px 6px', textAlign: 'left', fontWeight: 500 }}>默认值</th>
                      <th style={{ padding: '4px 6px', textAlign: 'left', fontWeight: 500 }}>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tc.param_spec.map((p, i) => (
                      <tr key={i} style={{ borderBottom: '0.5px solid var(--border-subtle)' }}>
                        <td style={{ padding: '5px 6px', fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{p.name}</td>
                        <td style={{ padding: '5px 6px', color: 'var(--text-secondary)' }}>{p.type || '-'}</td>
                        <td style={{ padding: '5px 6px', color: 'var(--text-secondary)' }}>{p.required ? '是' : '否'}</td>
                        <td style={{ padding: '5px 6px', color: 'var(--text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
                          {p.default != null ? String(p.default) : '-'}
                        </td>
                        <td style={{ padding: '5px 6px', color: 'var(--text-secondary)' }}>{p.description || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Section>
            )}

            {(tc.runtime_env && Object.keys(tc.runtime_env).length > 0) && (
              <Section title="运行环境">
                {Object.entries(tc.runtime_env).map(([k, v]) => (
                  <Field key={k} label={k} value={typeof v === 'object' ? JSON.stringify(v) : String(v)} mono />
                ))}
              </Section>
            )}

            <Section title="执行统计">
              {statsLoading ? (
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', padding: 8 }}>加载中...</div>
              ) : execStats ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 6 }}>
                    {[
                      { label: '总次数', value: execStats.total, color: '#3b82f6' },
                      { label: '通过', value: execStats.passed, color: '#16a34a' },
                      { label: '失败', value: execStats.failed, color: '#dc2626' },
                      { label: '通过率', value: `${execStats.pass_rate}%`, color: execStats.pass_rate >= 80 ? '#16a34a' : '#d97706' },
                    ].map(({ label, value, color }) => (
                      <div key={label} style={{ textAlign: 'center', background: 'var(--surface-secondary)', borderRadius: 8, padding: '8px 6px', border: '1px solid var(--border-subtle)' }}>
                        <div style={{ fontSize: 18, fontWeight: 700, color, lineHeight: 1.2 }}>{value}</div>
                        <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 2 }}>{label}</div>
                      </div>
                    ))}
                  </div>
                  {execStats.recent.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                      <div style={{ fontSize: 10, color: 'var(--text-tertiary)', fontWeight: 600 }}>最近执行</div>
                      {execStats.recent.slice(0, 5).map(r => (
                        <div key={r.result_id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-secondary)' }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0, background: r.passed ? '#16a34a' : '#dc2626' }} />
                          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.notes || (r.passed ? '通过' : '失败')}</span>
                          <span style={{ whiteSpace: 'nowrap' }}>{new Date(r.executed_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', padding: 8 }}>暂无执行数据</div>
              )}
            </Section>
          </div>
        </div>
      </div>
    </div>
  );
}

const st: Record<string, React.CSSProperties> = {
  modal: {
    background: 'var(--surface-primary)',
    borderRadius: 12,
    width: 680,
    maxWidth: '94vw',
    maxHeight: '88vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 25px 80px rgba(0,0,0,0.35)',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '14px 20px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  badge: {
    fontSize: 10,
    fontWeight: 700,
    padding: '2px 8px',
    borderRadius: 6,
    background: 'rgba(6,182,212,0.12)',
    color: 'var(--accent-secondary)',
    letterSpacing: '0.03em',
  },
  statusBadge: {
    fontSize: 10,
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 6,
  },
  closeBtn: {
    fontSize: 18,
    color: 'var(--text-tertiary)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '0 4px',
    lineHeight: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: 600,
    color: 'var(--text-primary)',
    padding: '14px 20px 0',
    lineHeight: 1.4,
  },
  body: {
    display: 'flex',
    gap: 0,
    flex: 1,
    overflow: 'hidden',
    marginTop: 14,
  },
  left: {
    width: 220,
    flexShrink: 0,
    padding: '0 16px 16px 20px',
    overflowY: 'auto',
    borderRight: '1px solid var(--border-subtle)',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  right: {
    flex: 1,
    padding: '0 20px 16px 16px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    borderBottom: '1px solid var(--border-subtle)',
    paddingBottom: 4,
  },
  sectionBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
  },
  fieldLabel: {
    fontSize: 11,
    color: 'var(--text-tertiary)',
  },
  fieldValue: {
    fontSize: 13,
    color: 'var(--text-primary)',
    wordBreak: 'break-all',
  },
};
