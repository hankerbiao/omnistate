import React from 'react';
import type { PlanTask } from './myTasksTypes';

interface Props {
  task: PlanTask;
  users: { user_id: string; username: string }[];
  loading: boolean;
  currentUserId: string;
  selectedUserId: string;
  onSelectUser: (id: string) => void;
  onConfirm: () => void;
  onClose: () => void;
}

const ReassignModal: React.FC<Props> = ({ task, users, loading, currentUserId, selectedUserId, onSelectUser, onConfirm, onClose }) => (
  <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2100 }}
    onClick={onClose}>
    <div onClick={e => e.stopPropagation()} style={{
      background: 'var(--bg-elevated)', borderRadius: 12, width: 400, maxWidth: '94vw',
      boxShadow: '0 30px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)',
    }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>改派 — {task.caseId}</span>
        <button onClick={onClose} style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
      </div>
      <div style={{ padding: '16px 20px' }}>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>选择新执行人</label>
        <select
          className="form-input form-select"
          value={selectedUserId}
          onChange={e => onSelectUser(e.target.value)}
          style={{ width: '100%', fontSize: 13 }}
          disabled={loading}
        >
          <option value="">{loading ? '加载中...' : '请选择...'}</option>
          {users.filter(u => u.user_id !== currentUserId).map(u => (
            <option key={u.user_id} value={u.user_id}>{u.username} ({u.user_id})</option>
          ))}
        </select>
      </div>
      <div style={{ padding: '12px 20px', display: 'flex', justifyContent: 'flex-end', gap: 8, borderTop: '1px solid var(--border-subtle)' }}>
        <button className="btn btn--ghost btn--sm" onClick={onClose}>取消</button>
        <button className="btn btn--primary btn--sm" onClick={onConfirm} disabled={!selectedUserId}
          style={{ fontSize: 12, opacity: !selectedUserId ? 0.5 : 1 }}>
          确认改派
        </button>
      </div>
    </div>
  </div>
);

export default ReassignModal;
