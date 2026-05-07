import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { RoleResponse, PermissionResponse } from '../types';

const RoleManagement: React.FC = () => {
  const [roles, setRoles] = useState<RoleResponse[]>([]);
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingName, setEditingName] = useState(false);
  const [editName, setEditName] = useState('');
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchRoles = useCallback(async (roleIdToRefresh?: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listRoles();
      setRoles(response.data || []);
      if (roleIdToRefresh || selectedRole) {
        const targetId = roleIdToRefresh || selectedRole?.role_id;
        const updated = response.data?.find(r => r.role_id === targetId);
        if (updated) {
          setSelectedRole(updated);
          setSelectedPermissionIds(new Set(updated.permission_ids || []));
        }
      }
    } catch (err) {
      setError('获取角色列表失败');
      console.error('Fetch roles error:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedRole?.role_id]);

  const fetchPermissions = useCallback(async () => {
    try {
      const response = await api.listPermissions();
      setPermissions(response.data || []);
    } catch (err) {
      console.error('Fetch permissions error:', err);
    }
  }, []);

  useEffect(() => {
    fetchRoles();
    fetchPermissions();
  }, [fetchRoles, fetchPermissions]);

  const handleSelectRole = (role: RoleResponse) => {
    setSelectedRole(role);
    setSelectedPermissionIds(new Set(role.permission_ids || []));
    setEditingName(false);
  };

  const handleEditName = () => {
    if (selectedRole) {
      setEditName(selectedRole.name);
      setEditingName(true);
    }
  };

  const handleSaveName = async () => {
    if (!selectedRole || !editName.trim()) return;

    setSaving(true);
    try {
      await api.updateRole(selectedRole.role_id, { name: editName.trim() });
      await fetchRoles(selectedRole.role_id);
      setEditingName(false);
    } catch (err) {
      setError('保存角色名称失败');
      console.error('Update role name error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEditName = () => {
    setEditingName(false);
    setEditName('');
  };

  const handleTogglePermission = (permissionId: string) => {
    setSelectedPermissionIds(prev => {
      const next = new Set(prev);
      if (next.has(permissionId)) {
        next.delete(permissionId);
      } else {
        next.add(permissionId);
      }
      return next;
    });
  };

  const handleSavePermissions = async () => {
    if (!selectedRole) return;

    setSaving(true);
    try {
      await api.updateRolePermissions(selectedRole.role_id, {
        permission_ids: Array.from(selectedPermissionIds),
      });
      await fetchRoles();
    } catch (err) {
      setError('保存角色权限失败');
      console.error('Update role permissions error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateRole = async () => {
    if (!newRoleName.trim()) return;

    setCreating(true);
    try {
      await api.createRole({
        name: newRoleName.trim(),
        description: newRoleDesc.trim() || undefined,
      });
      await fetchRoles();
      setCreateModalOpen(false);
      setNewRoleName('');
      setNewRoleDesc('');
    } catch (err) {
      setError('创建角色失败');
      console.error('Create role error:', err);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="workspace">
      {/* Left Panel - Role List */}
      <div style={styles.leftPanel}>
        <div style={styles.panelHeader}>
          <div>
            <h2 style={styles.panelTitle}>角色列表</h2>
            <span style={styles.panelHint}>{roles.length} 个角色</span>
          </div>
          <button className="btn btn--primary btn--sm" onClick={() => setCreateModalOpen(true)}>
            + 新建
          </button>
        </div>

        {loading && roles.length === 0 ? (
          <div className="loading-overlay">
            <div className="loading-spinner" />
          </div>
        ) : (
          <div style={styles.roleList}>
            {roles.map(role => (
              <div
                key={role.role_id}
                style={{
                  ...styles.roleItem,
                  ...(selectedRole?.role_id === role.role_id ? styles.roleItemSelected : {}),
                }}
                onClick={() => handleSelectRole(role)}
              >
                <div style={styles.roleItemHeader}>
                  <span style={styles.roleName}>{role.name}</span>
                  {role.is_system && (
                    <span style={styles.systemBadge}>系统</span>
                  )}
                </div>
                {role.description && (
                  <div style={styles.roleDesc}>{role.description}</div>
                )}
                <div style={styles.roleMeta}>
                  {role.permission_ids?.length || 0} 个权限
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right Panel - Role Details */}
      <div style={styles.rightPanel}>
        {selectedRole ? (
          <div className="data-panel">
            <div className="data-panel-header">
              <h3 className="data-panel-title">角色详情 - {selectedRole.name}</h3>
            </div>

            {error && (
              <div className="error-banner" style={{ marginBottom: '16px' }}>
                <span>⚠</span> {error}
                <button style={styles.errorClose} onClick={() => setError(null)}>×</button>
              </div>
            )}

            <div style={styles.detailSection}>
              <label style={styles.label}>角色名称</label>
              {editingName ? (
                <div style={styles.editNameRow}>
                  <input
                    style={styles.input}
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    placeholder="输入角色名称"
                    autoFocus
                  />
                  <button
                    style={styles.saveBtn}
                    onClick={handleSaveName}
                    disabled={saving || !editName.trim()}
                  >
                    {saving ? '保存中...' : '保存'}
                  </button>
                  <button style={styles.cancelBtn} onClick={handleCancelEditName}>
                    取消
                  </button>
                </div>
              ) : (
                <div style={styles.nameDisplay}>
                  <span style={styles.nameValue}>{selectedRole.name}</span>
                  {!selectedRole.is_system && (
                    <button style={styles.editNameBtn} onClick={handleEditName}>
                      编辑
                    </button>
                  )}
                </div>
              )}
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>角色描述</label>
              <div style={styles.descValue}>
                {selectedRole.description || '暂无描述'}
              </div>
            </div>

            <div style={styles.detailSection}>
              <div style={styles.permissionHeader}>
                <label style={styles.label}>权限配置</label>
                <button
                  style={{
                    ...styles.savePermBtn,
                    ...(saving ? styles.savePermBtnDisabled : {}),
                  }}
                  onClick={handleSavePermissions}
                  disabled={saving}
                >
                  {saving ? '保存中...' : '保存权限'}
                </button>
              </div>
              <div style={styles.permissionGrid}>
                {permissions.map(perm => (
                  <div
                    key={perm.id}
                    style={{
                      ...styles.permissionItem,
                      ...(selectedPermissionIds.has(perm.id) ? styles.permissionItemSelected : {}),
                    }}
                    onClick={() => !selectedRole.is_system && handleTogglePermission(perm.id)}
                    className={!selectedRole.is_system ? 'perm-item' : ''}
                  >
                    <input
                      type="checkbox"
                      checked={selectedPermissionIds.has(perm.id)}
                      onChange={() => handleTogglePermission(perm.id)}
                      disabled={selectedRole.is_system}
                      style={styles.permissionCheckbox}
                    />
                    <div style={styles.permissionContent}>
                      <div style={styles.permissionName}>{perm.name}</div>
                      <div style={styles.permissionCode}>{perm.code}</div>
                      {perm.description && (
                        <div style={styles.permissionDesc}>{perm.description}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state" style={{ height: '100%' }}>
            <div className="empty-state__icon">👥</div>
            <p className="empty-state__text">选择左侧角色查看详情</p>
          </div>
        )}
      </div>

      {/* Create Role Modal */}
      {createModalOpen && (
        <div style={styles.modalOverlay} onClick={() => setCreateModalOpen(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>新建角色</h3>
              <button style={styles.modalClose} onClick={() => setCreateModalOpen(false)}>×</button>
            </div>
            <div style={styles.modalBody}>
              <div style={styles.formGroup}>
                <label style={styles.label}>角色名称 *</label>
                <input
                  style={styles.input}
                  value={newRoleName}
                  onChange={e => setNewRoleName(e.target.value)}
                  placeholder="输入角色名称"
                  autoFocus
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>角色描述</label>
                <textarea
                  style={styles.textarea}
                  value={newRoleDesc}
                  onChange={e => setNewRoleDesc(e.target.value)}
                  placeholder="输入角色描述（可选）"
                  rows={3}
                />
              </div>
            </div>
            <div style={styles.modalFooter}>
              <button
                style={styles.cancelBtn}
                onClick={() => setCreateModalOpen(false)}
              >
                取消
              </button>
              <button
                style={styles.saveBtn}
                onClick={handleCreateRole}
                disabled={creating || !newRoleName.trim()}
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
        .perm-item:hover:not(.perm-item input:disabled) {
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
    width: '340px',
    minWidth: '340px',
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
  panelHint: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    marginTop: '2px',
    display: 'block',
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
    transition: 'all var(--transition-fast)',
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
  roleList: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '12px',
  },
  roleItem: {
    padding: '14px 16px',
    marginBottom: '8px',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  roleItemSelected: {
    borderColor: 'var(--accent-cyan)',
    backgroundColor: 'var(--bg-tertiary)',
  },
  roleItemHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
  },
  roleName: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  systemBadge: {
    fontSize: '10px',
    fontWeight: 600,
    color: 'var(--accent-purple)',
    backgroundColor: 'rgba(163, 113, 247, 0.15)',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  roleDesc: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    marginBottom: '6px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  roleMeta: {
    fontSize: '11px',
    color: 'var(--text-muted)',
  },
  detailSection: {
    marginBottom: '28px',
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: '10px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  nameDisplay: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  nameValue: {
    fontSize: '20px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  editNameBtn: {
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  editNameRow: {
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
  textarea: {
    width: '100%',
    padding: '10px 14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    resize: 'vertical' as const,
    fontFamily: 'inherit',
  },
  descValue: {
    fontSize: '14px',
    color: 'var(--text-secondary)',
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
    transition: 'all var(--transition-fast)',
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
  permissionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  savePermBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--bg-primary)',
    backgroundColor: 'var(--accent-cyan)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  savePermBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  permissionGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '12px',
  },
  permissionItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    padding: '14px 16px',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  permissionItemSelected: {
    borderColor: 'var(--accent-green)',
    backgroundColor: 'rgba(72, 199, 142, 0.08)',
  },
  permissionCheckbox: {
    marginTop: '2px',
    width: '16px',
    height: '16px',
    cursor: 'pointer',
  },
  permissionContent: {
    flex: 1,
  },
  permissionName: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '4px',
  },
  permissionCode: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-cyan)',
    marginBottom: '4px',
  },
  permissionDesc: {
    fontSize: '12px',
    color: 'var(--text-muted)',
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
    width: '480px',
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
  },
  formGroup: {
    marginBottom: '18px',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    padding: '18px 24px',
    borderTop: '1px solid var(--border-muted)',
  },
};

export default RoleManagement;