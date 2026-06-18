/**
 * RerunConfirmModal - 重新执行确认弹窗
 */
import { useState } from 'react';
import type { RerunConfirmModalProps } from './types';

export default function RerunConfirmModal({ item, users, onConfirm, onClose }: RerunConfirmModalProps) {
  const isAuto = item.ref_type === 'auto';
  const [selectedAssigneeId, setSelectedAssigneeId] = useState(item.assignee_id || '');

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'var(--overlay-bg)', backdropFilter: 'blur(2px)',
        zIndex: 2100, display: 'flex', justifyContent: 'center', alignItems: 'center',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--surface-primary)', borderRadius: 12, width: 440, maxWidth: '90vw',
          padding: 0, boxShadow: '0 25px 80px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)',
        }}
      >
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>确认重新执行</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            确定要重新执行用例 <strong>{item.case_title}</strong> 吗？
          </div>
        </div>
        <div style={{ padding: '12px 20px', fontSize: 12, color: 'var(--text-tertiary)', lineHeight: 1.5 }}>
          {isAuto ? (
            <span>将重置为"待执行"状态并清除旧执行记录。请在状态变为待执行后，手动点击"执行"按钮下发。</span>
          ) : (
            <span>将重置为"待执行"状态，旧结果将被清除。您可以重新提交执行结果。</span>
          )}
        </div>
        <div style={{ padding: '0 20px 12px' }}>
          <label style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4, display: 'block' }}>
            指派给：
          </label>
          <select
            className="form-input form-select"
            value={selectedAssigneeId}
            onChange={(e) => setSelectedAssigneeId(e.target.value)}
            style={{ width: '100%', fontSize: 12 }}
          >
            <option value="">不指派</option>
            {users.map((u) => (
              <option key={u.user_id} value={u.user_id}>
                {u.username} {u.user_id === item.assignee_id ? '(原执行人)' : ''}
              </option>
            ))}
          </select>
        </div>
        <div style={{ padding: '12px 20px', display: 'flex', justifyContent: 'flex-end', gap: 8, borderTop: '1px solid var(--border-subtle)' }}>
          <button className="btn btn--ghost btn--sm" onClick={onClose} style={{ fontSize: 12 }}>取消</button>
          <button
            className="btn btn--primary btn--sm"
            onClick={() => onConfirm(selectedAssigneeId)}
            style={{ fontSize: 12, background: '#f85149', borderColor: '#f85149' }}
          >
            确认执行
          </button>
        </div>
      </div>
    </div>
  );
}