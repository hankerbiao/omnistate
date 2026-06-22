import React from 'react';
import type { PlanTask } from './myTasksTypes';
import { Dialog, DialogContent } from './ui/dialog';

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
  <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
    <DialogContent className="sm:max-w-[400px]" style={{ padding: 0 }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>改派 — {task.caseId}</span>
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
    </DialogContent>
  </Dialog>
);

export default ReassignModal;
