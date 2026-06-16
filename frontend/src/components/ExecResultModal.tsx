import React from 'react';

interface Props {
  taskId: string;
  loading: boolean;
  data: any;
  onClose: () => void;
}

const StatBadge: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <div style={{
    flex: 1, minWidth: 80, padding: '8px 12px', borderRadius: 6,
    background: 'var(--surface-secondary)', textAlign: 'center',
    border: '1px solid var(--border-subtle)',
  }}>
    <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginBottom: 2 }}>{label}</div>
    <div style={{ fontSize: 16, fontWeight: 600, color: color || 'var(--text-primary)' }}>{value}</div>
  </div>
);

const ExecResultModal: React.FC<Props> = ({ taskId, loading, data, onClose }) => (
  <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2100 }}
    onClick={onClose}>
    <div onClick={e => e.stopPropagation()} style={{
      background: 'var(--bg-elevated)', borderRadius: 12, width: 520, maxWidth: '94vw',
      maxHeight: '70vh', display: 'flex', flexDirection: 'column',
      boxShadow: '0 30px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)',
    }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>执行结果 — {taskId}</span>
        <button onClick={onClose} style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', fontSize: 12 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 30, color: 'var(--text-tertiary)' }}>加载中...</div>
        ) : data?.error ? (
          <div style={{ textAlign: 'center', padding: 30, color: 'var(--text-tertiary)' }}>该任务尚未执行或执行记录已清除</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <StatBadge label="状态" value={data?.overall_status || '-'} />
              <StatBadge label="进度" value={`${data?.progress_percent || 0}%`} />
              <StatBadge label="通过" value={String(data?.passed_case_count || 0)} color="#3fb950" />
              <StatBadge label="失败" value={String(data?.failed_case_count || 0)} color="#f85149" />
            </div>
            {data?.cases?.map((c: any, i: number) => (
              <div key={c.case_id || i} style={{
                padding: '8px 10px', borderRadius: 6,
                border: '1px solid var(--border-subtle)', background: 'var(--surface-secondary)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 10, color: 'var(--text-tertiary)' }}>{c.auto_case_id || c.case_id}</span>
                  <span style={{ flex: 1, fontWeight: 500 }}>{c.title || '-'}</span>
                  <span style={{
                    fontSize: 10, padding: '1px 6px', borderRadius: 3, fontWeight: 600,
                    color: c.status === 'PASSED' ? '#3fb950' : c.status === 'FAILED' ? '#f85149' : '#8b949e',
                    background: c.status === 'PASSED' ? 'rgba(63,185,80,0.12)' : c.status === 'FAILED' ? 'rgba(248,81,73,0.12)' : 'rgba(139,148,158,0.12)',
                  }}>
                    {c.status || '-'}
                  </span>
                </div>
                {c.failure_message && (
                  <div style={{ fontSize: 10, color: '#f85149', padding: '4px 8px', background: 'rgba(248,81,73,0.06)', borderRadius: 4, marginTop: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                    {c.failure_message}
                  </div>
                )}
                {c.result_data?.assertions?.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>断言: {c.result_data.assertions.length} 条</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  </div>
);

export default ExecResultModal;
