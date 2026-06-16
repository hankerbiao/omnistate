import React from 'react';
import type { ExecutionTask } from '../types';

const EXEC_STATUS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  QUEUED: { bg: 'rgba(210,153,34,0.12)', color: '#d29922', label: '排队中' },
  RUNNING: { bg: 'rgba(63,185,80,0.12)', color: '#3fb950', label: '执行中' },
  PASSED: { bg: 'rgba(63,185,80,0.12)', color: '#3fb950', label: '通过' },
  FAILED: { bg: 'rgba(248,81,73,0.12)', color: '#f85149', label: '失败' },
  SKIPPED: { bg: 'rgba(139,148,158,0.12)', color: '#8b949e', label: '跳过' },
  CANCELLED: { bg: 'rgba(139,148,158,0.12)', color: '#8b949e', label: '已取消' },
};

interface Props {
  tasks: ExecutionTask[];
  onViewResult: (taskId: string) => void;
  onClose: () => void;
}

const ExecRecordsModal: React.FC<Props> = ({ tasks, onViewResult, onClose }) => {
  const getStyle = (status: string) => EXEC_STATUS_STYLE[status] || { bg: 'rgba(139,148,158,0.12)', color: '#8b949e', label: status };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}
      onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-elevated)', borderRadius: 12, width: 680, maxWidth: '94vw',
        maxHeight: '80vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 30px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)',
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>自动化执行记录</div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{tasks.length} 条记录</div>
          </div>
          <button onClick={onClose} style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {tasks.length === 0 ? (
            <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>暂无自动化执行记录</div>
          ) : (
            tasks.map(task => {
              const meta = getStyle(task.overall_status);
              return (
                <div key={task.task_id} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                  borderRadius: 6, border: '1px solid var(--border-subtle)', background: 'var(--bg-primary)', fontSize: 12,
                }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 10, color: 'var(--text-tertiary)', flexShrink: 0 }}>
                    {task.task_id}
                  </span>
                  <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                    {task.cases?.map(c => c.title).filter(Boolean).join(', ') || task.task_id}
                  </span>
                  <span style={{
                    fontSize: 10, padding: '2px 8px', borderRadius: 4,
                    background: meta.bg, color: meta.color, fontWeight: 600, flexShrink: 0,
                  }}>
                    {meta.label}
                  </span>
                  <span style={{ fontSize: 10, color: 'var(--text-tertiary)', flexShrink: 0 }}>
                    {task.created_at ? new Date(task.created_at).toLocaleString('zh-CN', {
                      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
                    }) : '-'}
                  </span>
                  <button onClick={() => onViewResult(task.task_id)} style={{
                    fontSize: 10, padding: '2px 8px', borderRadius: 4,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--surface-secondary)', color: 'var(--accent-primary)',
                    cursor: 'pointer', flexShrink: 0,
                  }}>
                    结果
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default ExecRecordsModal;
