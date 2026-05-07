import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { UserResponse, RoleResponse } from '../types';

type EditableUserField = 'username' | 'email';

const emptyNewUser = {
  user_id: '',
  username: '',
  password: '',
  email: '',
  role_ids: [] as string[],
};

const getErrorMessage = (err: unknown, fallback: string) => {
  if (err instanceof Error) {
    return `${fallback}: ${err.message}`;
  }
  return fallback;
};

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [roles, setRoles] = useState<RoleResponse[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<EditableUserField | null>(null);
  const [editValue, setEditValue] = useState('');
  const [selectedRoleIds, setSelectedRoleIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newUser, setNewUser] = useState(emptyNewUser);
  const [creating, setCreating] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('');

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: { status?: string; limit?: number } = { limit: 200 };
      if (filterStatus) {
        params.status = filterStatus;
      }
      const response = await api.listUsers(params);
      const nextUsers = response.data || [];
      setUsers(nextUsers);
      setSelectedUser(current => {
        if (!current) return null;
        return nextUsers.find(user => user.user_id === current.user_id) || null;
      });
    } catch (err) {
      setError(getErrorMessage(err, '获取用户列表失败'));
      console.error('Fetch users error:', err);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  const fetchRoles = useCallback(async () => {
    try {
      const response = await api.listRoles();
      setRoles(response.data || []);
    } catch (err) {
      console.error('Fetch roles error:', err);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    fetchRoles();
  }, [fetchUsers, fetchRoles]);

  const handleSelectUser = (user: UserResponse) => {
    setSelectedUser(user);
    setSelectedRoleIds(new Set(user.role_ids));
    setEditingField(null);
  };

  const handleEditField = (field: EditableUserField, currentValue: string) => {
    setEditingField(field);
    setEditValue(currentValue || '');
    setError(null);
  };

  const handleSaveField = async () => {
    if (!selectedUser || !editingField) return;
    const value = editValue.trim();
    if (editingField === 'username' && !value) {
      setError('用户名不能为空');
      return;
    }

    setSaving(true);
    try {
      const data = { [editingField]: value };
      await api.updateUser(selectedUser.user_id, data);
      await fetchUsers();
      setEditingField(null);
      setEditValue('');
    } catch (err) {
      setError(getErrorMessage(err, '保存失败'));
      console.error('Update user error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingField(null);
    setEditValue('');
  };

  const handleToggleRole = (roleId: string) => {
    setError(null);
    setSelectedRoleIds(prev => {
      const next = new Set(prev);
      if (next.has(roleId)) {
        next.delete(roleId);
      } else {
        next.add(roleId);
      }
      return next;
    });
  };

  const handleSaveRoles = async () => {
    if (!selectedUser) return;

    setSaving(true);
    try {
      await api.updateUserRoles(selectedUser.user_id, {
        role_ids: Array.from(selectedRoleIds),
      });
      await fetchUsers();
    } catch (err) {
      setError(getErrorMessage(err, '保存角色失败'));
      console.error('Update user roles error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateUser = async () => {
    if (!newUser.user_id.trim() || !newUser.username.trim() || !newUser.password.trim()) {
      setError('请填写必填字段');
      return;
    }

    setCreating(true);
    try {
      await api.createUser({
        user_id: newUser.user_id.trim(),
        username: newUser.username.trim(),
        password: newUser.password,
        email: newUser.email.trim() || undefined,
        role_ids: newUser.role_ids,
      });
      await fetchUsers();
      setCreateModalOpen(false);
      setNewUser(emptyNewUser);
    } catch (err) {
      setError(getErrorMessage(err, '创建用户失败'));
      console.error('Create user error:', err);
    } finally {
      setCreating(false);
    }
  };

  const getStatusStyle = (status: string) => {
    if (status === 'ACTIVE') {
      return {
        bg: 'var(--status-success-bg)',
        color: 'var(--accent-green)',
        text: '启用',
      };
    }
    return {
      bg: 'var(--status-error-bg)',
      color: 'var(--accent-red)',
      text: '禁用',
    };
  };

  const getRoleName = (roleId: string) => {
    const role = roles.find(r => r.role_id === roleId);
    return role?.name || roleId;
  };

  return (
    <div className="workspace">
      {/* Left Panel - User List */}
      <div style={styles.leftPanel}>
        <div style={styles.panelHeader}>
          <div>
            <h2 style={styles.panelTitle}>用户列表</h2>
            <span style={styles.panelHint}>{users.length} 个用户</span>
          </div>
          <button className="btn btn--primary btn--sm" onClick={() => setCreateModalOpen(true)}>
            + 新建
          </button>
        </div>

        <div style={styles.filterRow}>
          <select
            style={styles.filterSelect}
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
          >
            <option value="">全部状态</option>
            <option value="ACTIVE">启用</option>
            <option value="INACTIVE">禁用</option>
          </select>
          <button style={styles.refreshBtn} onClick={fetchUsers} disabled={loading}>
            刷新
          </button>
        </div>

        {loading && users.length === 0 ? (
          <div className="loading-overlay">
            <div className="loading-spinner" />
          </div>
        ) : (
          <div style={styles.userList}>
            {users.map(user => {
              const status = getStatusStyle(user.status);
              return (
                <div
                  key={user.user_id}
                  style={{
                    ...styles.userItem,
                    ...(selectedUser?.user_id === user.user_id ? styles.userItemSelected : {}),
                  }}
                  onClick={() => handleSelectUser(user)}
                >
                  <div style={styles.userItemHeader}>
                    <span style={styles.userName}>{user.username}</span>
                    <span
                      style={{
                        ...styles.statusBadge,
                        backgroundColor: status.bg,
                        color: status.color,
                      }}
                    >
                      {status.text}
                    </span>
                  </div>
                  <div style={styles.userId}>{user.user_id}</div>
                  <div style={styles.userRoles}>
                    {user.role_ids.slice(0, 2).map(rid => (
                      <span key={rid} style={styles.roleTag}>{getRoleName(rid)}</span>
                    ))}
                    {user.role_ids.length > 2 && (
                      <span style={styles.roleTagMore}>+{user.role_ids.length - 2}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Right Panel - User Details */}
      <div style={styles.rightPanel}>
        {selectedUser ? (
          <div className="data-panel">
            <div className="data-panel-header">
              <h3 className="data-panel-title">用户详情 - {selectedUser.username}</h3>
            </div>

            {error && (
              <div className="error-banner" style={{ marginBottom: '16px' }}>
                <span>⚠</span> {error}
                <button style={styles.errorClose} onClick={() => setError(null)}>×</button>
              </div>
            )}

            <div style={styles.detailSection}>
              <label style={styles.label}>用户ID</label>
              <div style={styles.readonlyField}>{selectedUser.user_id}</div>
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>用户名</label>
              {editingField === 'username' ? (
                <div style={styles.editRow}>
                  <input
                    style={styles.input}
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    autoFocus
                  />
                  <button style={styles.saveBtn} onClick={handleSaveField} disabled={saving}>
                    {saving ? '保存中...' : '保存'}
                  </button>
                  <button style={styles.cancelBtn} onClick={handleCancelEdit}>取消</button>
                </div>
              ) : (
                <div style={styles.editFieldRow}>
                  <span style={styles.fieldValue}>{selectedUser.username}</span>
                  <button style={styles.editBtn} onClick={() => handleEditField('username', selectedUser.username)}>
                    编辑
                  </button>
                </div>
              )}
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>邮箱</label>
              {editingField === 'email' ? (
                <div style={styles.editRow}>
                  <input
                    style={styles.input}
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    placeholder="请输入邮箱"
                    autoFocus
                  />
                  <button style={styles.saveBtn} onClick={handleSaveField} disabled={saving}>
                    {saving ? '保存中...' : '保存'}
                  </button>
                  <button style={styles.cancelBtn} onClick={handleCancelEdit}>取消</button>
                </div>
              ) : (
                <div style={styles.editFieldRow}>
                  <span style={styles.fieldValue}>{selectedUser.email || '未设置'}</span>
                  <button style={styles.editBtn} onClick={() => handleEditField('email', selectedUser.email || '')}>
                    编辑
                  </button>
                </div>
              )}
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>状态</label>
              <div style={styles.statusRow}>
                {selectedUser.status === 'ACTIVE' ? (
                  <span style={{ ...styles.statusBadge, backgroundColor: 'var(--status-success-bg)', color: 'var(--accent-green)' }}>
                    启用
                  </span>
                ) : (
                  <span style={{ ...styles.statusBadge, backgroundColor: 'var(--status-error-bg)', color: 'var(--accent-red)' }}>
                    禁用
                  </span>
                )}
              </div>
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>所属角色</label>
              <div style={styles.roleList}>
                {roles.map(role => (
                  <div
                    key={role.role_id}
                    style={{
                      ...styles.roleItem,
                      ...(selectedRoleIds.has(role.role_id) ? styles.roleItemSelected : {}),
                    }}
                    onClick={() => handleToggleRole(role.role_id)}
                    className="role-item"
                  >
                    <input
                      type="checkbox"
                      checked={selectedRoleIds.has(role.role_id)}
                      onClick={e => e.stopPropagation()}
                      onChange={() => handleToggleRole(role.role_id)}
                      style={styles.checkbox}
                    />
                    <span style={styles.roleName}>{role.name}</span>
                  </div>
                ))}
              </div>
              <button
                style={{
                  ...styles.saveRolesBtn,
                  ...(saving ? styles.saveRolesBtnDisabled : {}),
                }}
                onClick={handleSaveRoles}
                disabled={saving}
              >
                {saving ? '保存中...' : '保存角色'}
              </button>
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>创建时间</label>
              <div style={styles.readonlyField}>
                {new Date(selectedUser.created_at).toLocaleString('zh-CN')}
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state" style={{ height: '100%' }}>
            <div className="empty-state__icon">👤</div>
            <p className="empty-state__text">选择左侧用户查看详情</p>
          </div>
        )}
      </div>

      {/* Create User Modal */}
      {createModalOpen && (
        <div style={styles.modalOverlay} onClick={() => setCreateModalOpen(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>新建用户</h3>
              <button style={styles.modalClose} onClick={() => setCreateModalOpen(false)}>×</button>
            </div>
            <div style={styles.modalBody}>
              <div style={styles.formGroup}>
                <label style={styles.label}>用户ID *</label>
                <input
                  style={styles.input}
                  value={newUser.user_id}
                  onChange={e => setNewUser({ ...newUser, user_id: e.target.value })}
                  placeholder="登录用ID"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>用户名 *</label>
                <input
                  style={styles.input}
                  value={newUser.username}
                  onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                  placeholder="显示名称"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>密码 *</label>
                <input
                  style={styles.input}
                  type="password"
                  value={newUser.password}
                  onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                  placeholder="至少6位"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>邮箱</label>
                <input
                  style={styles.input}
                  type="email"
                  value={newUser.email}
                  onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                  placeholder="可选"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>初始角色</label>
                <div style={styles.modalRoleList}>
                  {roles.map(role => (
                    <div
                      key={role.role_id}
                      style={{
                        ...styles.modalRoleItem,
                        ...(newUser.role_ids.includes(role.role_id) ? styles.modalRoleItemSelected : {}),
                      }}
                      onClick={() => {
                        const ids = newUser.role_ids.includes(role.role_id)
                          ? newUser.role_ids.filter(id => id !== role.role_id)
                          : [...newUser.role_ids, role.role_id];
                        setNewUser({ ...newUser, role_ids: ids });
                      }}
                    >
                    <input
                      type="checkbox"
                      checked={newUser.role_ids.includes(role.role_id)}
                      onClick={e => e.stopPropagation()}
                      onChange={() => {
                        const ids = newUser.role_ids.includes(role.role_id)
                          ? newUser.role_ids.filter(id => id !== role.role_id)
                          : [...newUser.role_ids, role.role_id];
                        setNewUser({ ...newUser, role_ids: ids });
                      }}
                      style={styles.checkbox}
                    />
                      <span>{role.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div style={styles.modalFooter}>
              <button style={styles.cancelBtn} onClick={() => setCreateModalOpen(false)}>取消</button>
              <button
                style={styles.saveBtn}
                onClick={handleCreateUser}
                disabled={creating || !newUser.user_id.trim() || !newUser.username.trim() || !newUser.password}
              >
                {creating ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .role-item:hover {
          background-color: var(--bg-tertiary);
          border-color: var(--accent-cyan);
        }
      `}</style>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    height: 'calc(100vh - 64px)',
    animation: 'fadeIn 0.3s ease',
  } as const,
  leftPanel: {
    width: '380px',
    minWidth: '380px',
    backgroundColor: 'var(--bg-secondary)',
    borderRight: '1px solid var(--border-default)',
    display: 'flex',
    flexDirection: 'column' as const,
  },
  rightPanel: {
    flex: 1,
    padding: '28px 32px',
    overflowY: 'auto' as const,
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid var(--border-muted)',
  },
  panelTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  },
  createBtn: {
    padding: '8px 14px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--accent-cyan)',
    backgroundColor: 'transparent',
    border: '1px solid var(--accent-cyan)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  filterRow: {
    display: 'flex',
    gap: '10px',
    padding: '12px 16px',
    borderBottom: '1px solid var(--border-muted)',
  },
  filterSelect: {
    flex: 1,
    padding: '8px 12px',
    fontSize: '13px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  refreshBtn: {
    padding: '8px 14px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  loadingState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '60px',
    color: 'var(--text-secondary)',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid var(--border-default)',
    borderTopColor: 'var(--accent-cyan)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  userList: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '12px',
  },
  userItem: {
    padding: '14px 16px',
    marginBottom: '8px',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  userItemSelected: {
    borderColor: 'var(--accent-cyan)',
    backgroundColor: 'var(--bg-tertiary)',
  },
  userItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  userName: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  statusBadge: {
    padding: '3px 10px',
    fontSize: '11px',
    fontWeight: 600,
    borderRadius: '10px',
  },
  userId: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-muted)',
    marginBottom: '6px',
  },
  userRoles: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '4px',
  },
  roleTag: {
    fontSize: '11px',
    padding: '2px 8px',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: '4px',
    color: 'var(--text-secondary)',
  },
  roleTagMore: {
    fontSize: '11px',
    padding: '2px 6px',
    color: 'var(--text-muted)',
  },
  detailSection: {
    marginBottom: '24px',
  },
  label: {
    display: 'block',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: '8px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  readonlyField: {
    fontSize: '14px',
    color: 'var(--text-secondary)',
    fontFamily: "'JetBrains Mono', monospace",
  },
  fieldValue: {
    fontSize: '16px',
    color: 'var(--text-primary)',
    fontWeight: 500,
  },
  editFieldRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  editRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
  },
  saveBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--bg-primary)',
    backgroundColor: 'var(--accent-cyan)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  cancelBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'transparent',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  editBtn: {
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  statusRow: {
    display: 'flex',
    gap: '10px',
  },
  roleList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '10px',
    marginBottom: '16px',
  },
  roleItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 14px',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  roleItemSelected: {
    borderColor: 'var(--accent-green)',
    backgroundColor: 'rgba(72, 199, 142, 0.08)',
  },
  roleName: {
    fontSize: '13px',
    color: 'var(--text-primary)',
  },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
  },
  saveRolesBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--bg-primary)',
    backgroundColor: 'var(--accent-cyan)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  saveRolesBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  emptyDetail: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: 'var(--text-muted)',
  },
  emptyIcon: {
    fontSize: '64px',
    opacity: 0.3,
    marginBottom: '16px',
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 18px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--accent-red)',
    fontSize: '14px',
    marginBottom: '20px',
  },
  errorClose: {
    marginLeft: 'auto',
    padding: '0 8px',
    fontSize: '18px',
    background: 'none',
    border: 'none',
    color: 'var(--accent-red)',
    cursor: 'pointer',
  },
  modalOverlay: {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    width: '520px',
    maxWidth: '90vw',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '18px 24px',
    borderBottom: '1px solid var(--border-muted)',
  },
  modalTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  },
  modalClose: {
    padding: '0 8px',
    fontSize: '20px',
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
  },
  modalBody: {
    padding: '24px',
    maxHeight: '60vh',
    overflowY: 'auto' as const,
  },
  formGroup: {
    marginBottom: '18px',
  },
  modalRoleList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
  },
  modalRoleItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 14px',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontSize: '13px',
    color: 'var(--text-primary)',
  },
  modalRoleItemSelected: {
    borderColor: 'var(--accent-green)',
    backgroundColor: 'rgba(72, 199, 142, 0.08)',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    padding: '18px 24px',
    borderTop: '1px solid var(--border-muted)',
  },
};

export default UserManagement;
