import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../services/api';
import {
  getStateLabel,
  WORKFLOW_ACTION_LABELS,
  WORKFLOW_FIELD_LABELS,
  type WorkflowTypeCode,
} from '../../constants/workflowLabels';
import type { WorkflowTransition } from '../../types';
import { SWITCHABLE_USERS } from '../../config/users';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';

interface WorkflowTransitionModalProps {
  open: boolean;
  transition: WorkflowTransition | null;
  typeCode?: WorkflowTypeCode;
  defaultPriority?: string;
  onClose: () => void;
  onSubmit: (formData: Record<string, string>) => Promise<boolean>;
  submitting: boolean;
}

const WorkflowTransitionModal: React.FC<WorkflowTransitionModalProps> = ({
  open,
  transition,
  typeCode,
  defaultPriority = '',
  onClose,
  onSubmit,
  submitting,
}) => {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [ownerSearchQuery, setOwnerSearchQuery] = useState('');
  const [ownerSuggestions, setOwnerSuggestions] = useState<{ user_id: string; username: string }[]>([]);
  const [showOwnerDropdown, setShowOwnerDropdown] = useState(false);

  const searchUsers = useCallback(async (query: string) => {
    try {
      const response = await api.listUsers(
        query.trim() ? { search: query, limit: 20 } : { limit: 50 },
      );
      setOwnerSuggestions(response.data || []);
    } catch (err) {
      console.error('Search users error:', err);
    }
  }, []);

  useEffect(() => {
    if (!open || !transition) return;
    const initial: Record<string, string> = {};
    for (const field of transition.required_fields) {
      if (field === 'priority') {
        initial[field] = defaultPriority;
      }
    }
    setFormData(initial);
    setOwnerSearchQuery('');
    if (transition.required_fields.includes('target_owner_id')) {
      searchUsers('');
    }
  }, [open, transition, defaultPriority, searchUsers]);

  if (!open || !transition) return null;

  const handleSubmit = async () => {
    for (const field of transition.required_fields) {
      if (!formData[field]?.trim()) {
        alert(`${WORKFLOW_FIELD_LABELS[field] || field} 不能为空`);
        return;
      }
    }
    const ok = await onSubmit(formData);
    if (ok) onClose();
  };

  const quickPickUser = (userId: string, username: string) => {
    setFormData((prev) => ({ ...prev, target_owner_id: userId }));
    setOwnerSearchQuery(username);
    setShowOwnerDropdown(false);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>
            {WORKFLOW_ACTION_LABELS[transition.action] || transition.action}
          </DialogTitle>
        </DialogHeader>

        <p style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: '13px' }}>
          状态将变为:{' '}
          <strong>{getStateLabel(transition.to_state, typeCode)}</strong>
          <span style={{ color: 'var(--text-tertiary)', marginLeft: '6px' }}>
            ({transition.to_state})
          </span>
        </p>

        {transition.required_fields.includes('target_owner_id') && (
          <div style={styles.quickUsers}>
            <span style={styles.quickLabel}>快捷指派（测试角色）:</span>
            <div style={styles.quickChips}>
              {SWITCHABLE_USERS.filter((u) => u.userId !== 'admin').map((user) => (
                <button
                  key={user.userId}
                  type="button"
                  style={styles.chip}
                  onClick={() => quickPickUser(user.userId, user.label)}
                >
                  {user.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {transition.required_fields.map((field) => (
          <div key={field} style={{ marginBottom: '16px' }}>
            <label style={styles.formLabel}>{WORKFLOW_FIELD_LABELS[field] || field} *</label>
            {field === 'priority' ? (
              <select
                className="form-input form-select"
                value={formData[field] || ''}
                onChange={(e) => setFormData({ ...formData, [field]: e.target.value })}
              >
                <option value="">请选择</option>
                <option value="P0">P0 - 紧急</option>
                <option value="P1">P1 - 高</option>
                <option value="P2">P2 - 中</option>
                <option value="P3">P3 - 低</option>
              </select>
            ) : field === 'target_owner_id' ? (
              <div style={{ position: 'relative' }}>
                <input
                  className="form-input"
                  type="text"
                  value={ownerSearchQuery}
                  onChange={(e) => {
                    setOwnerSearchQuery(e.target.value);
                    searchUsers(e.target.value);
                    setShowOwnerDropdown(true);
                  }}
                  onFocus={() => {
                    searchUsers(ownerSearchQuery);
                    setShowOwnerDropdown(true);
                  }}
                  placeholder="搜索用户 ID 或姓名..."
                  autoComplete="off"
                />
                {formData.target_owner_id && (
                  <div style={styles.selectedId}>已选: {formData.target_owner_id}</div>
                )}
                {showOwnerDropdown && ownerSuggestions.length > 0 && (
                  <div style={styles.dropdown}>
                    {ownerSuggestions.map((user) => (
                      <div
                        key={user.user_id}
                        style={styles.dropdownItem}
                        onClick={() => quickPickUser(user.user_id, user.username)}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = 'var(--surface-hover)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = '';
                        }}
                      >
                        <span style={{ fontWeight: 500 }}>{user.username}</span>
                        <span style={styles.userId}>{user.user_id}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : field === 'comment' ? (
              <textarea
                className="form-input"
                rows={3}
                value={formData[field] || ''}
                onChange={(e) => setFormData({ ...formData, [field]: e.target.value })}
                placeholder="请输入备注"
                style={{ resize: 'vertical' }}
              />
            ) : (
              <input
                className="form-input"
                type="text"
                value={formData[field] || ''}
                onChange={(e) => setFormData({ ...formData, [field]: e.target.value })}
                placeholder={`请输入${WORKFLOW_FIELD_LABELS[field] || field}`}
              />
            )}
          </div>
        ))}

        <DialogFooter>
          <Button variant="ghost" size="sm" onClick={onClose}>取消</Button>
          <Button size="sm" onClick={handleSubmit} disabled={submitting}>
            {submitting ? '处理中...' : '确认流转'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const styles: Record<string, React.CSSProperties> = {
  formLabel: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    marginBottom: '6px',
  },
  quickUsers: {
    marginBottom: '16px',
    padding: '10px 12px',
    backgroundColor: 'var(--surface-tertiary)',
    borderRadius: 'var(--radius-md)',
  },
  quickLabel: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    display: 'block',
    marginBottom: '8px',
  },
  quickChips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  chip: {
    padding: '4px 10px',
    fontSize: '12px',
    borderRadius: '999px',
    border: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-primary)',
    cursor: 'pointer',
    color: 'var(--text-secondary)',
  },
  selectedId: {
    fontSize: '11px',
    color: 'var(--status-success)',
    marginTop: '4px',
    fontFamily: 'monospace',
  },
  dropdown: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)',
    marginTop: '2px',
    maxHeight: '200px',
    overflow: 'auto',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    zIndex: 10,
  },
  dropdownItem: {
    padding: '8px 12px',
    cursor: 'pointer',
    fontSize: '13px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  userId: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    fontFamily: 'monospace',
  },
};

export default WorkflowTransitionModal;
