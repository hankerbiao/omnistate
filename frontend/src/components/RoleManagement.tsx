import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import type { RoleResponse, PermissionResponse } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';

const getErrorMessage = (err: unknown, fallback: string) => {
  if (err instanceof Error) return `${fallback}: ${err.message}`;
  return fallback;
};

const getPermissionKey = (perm: PermissionResponse) =>
  perm.perm_id || perm.permission_id || perm.id;

const groupPermissions = (perms: PermissionResponse[]) => {
  const groups = new Map<string, PermissionResponse[]>();
  for (const perm of perms) {
    const group = perm.code.includes(':') ? perm.code.split(':')[0] : '其他';
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(perm);
  }
  return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
};

type RoleFilter = 'all' | 'system' | 'custom';

const RoleManagement: React.FC = () => {
  const [roles, setRoles] = useState<RoleResponse[]>([]);
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all');
  const [permissionSearch, setPermissionSearch] = useState('');

  const fetchRoles = useCallback(async (roleIdToRefresh?: string, syncDrawer = false) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listRoles();
      setRoles(response.data || []);
      const targetId = roleIdToRefresh ?? (syncDrawer ? selectedRole?.role_id : undefined);
      if (targetId) {
        const updated = response.data?.find(r => r.role_id === targetId);
        if (updated) {
          setSelectedRole(updated);
          setSelectedPermissionIds(new Set(updated.permission_ids || []));
          setEditName(updated.name);
          setEditDesc(updated.description || '');
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

  const filteredRoles = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return roles.filter(role => {
      if (roleFilter === 'system' && !role.is_system) return false;
      if (roleFilter === 'custom' && role.is_system) return false;
      if (!q) return true;
      return (
        role.name.toLowerCase().includes(q)
        || role.role_id.toLowerCase().includes(q)
        || (role.description?.toLowerCase().includes(q) ?? false)
      );
    });
  }, [roles, searchQuery, roleFilter]);

  const filteredPermissions = useMemo(() => {
    const q = permissionSearch.trim().toLowerCase();
    if (!q) return permissions;
    return permissions.filter(perm =>
      perm.name.toLowerCase().includes(q)
      || perm.code.toLowerCase().includes(q)
      || (perm.description?.toLowerCase().includes(q) ?? false),
    );
  }, [permissions, permissionSearch]);

  const permissionGroups = useMemo(
    () => groupPermissions(filteredPermissions),
    [filteredPermissions],
  );

  const selectableRoles = useMemo(
    () => filteredRoles.filter(r => !r.is_system),
    [filteredRoles],
  );

  const openRoleDrawer = (role: RoleResponse) => {
    setSelectedRole(role);
    setSelectedPermissionIds(new Set(role.permission_ids || []));
    setEditName(role.name);
    setEditDesc(role.description || '');
    setPermissionSearch('');
    setError(null);
  };

  const closeRoleDrawer = () => {
    setSelectedRole(null);
    setPermissionSearch('');
  };

  const handleSaveBasicInfo = async () => {
    if (!selectedRole || !editName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateRole(selectedRole.role_id, {
        name: editName.trim(),
        description: editDesc.trim() || undefined,
      });
      await fetchRoles(selectedRole.role_id);
    } catch (err) {
      setError('保存角色信息失败');
      console.error('Update role error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleTogglePermission = (permissionId: string) => {
    setSelectedPermissionIds(prev => {
      const next = new Set(prev);
      if (next.has(permissionId)) next.delete(permissionId);
      else next.add(permissionId);
      return next;
    });
  };

  const handleToggleGroup = (groupPerms: PermissionResponse[], selectAll: boolean) => {
    setSelectedPermissionIds(prev => {
      const next = new Set(prev);
      for (const perm of groupPerms) {
        const key = getPermissionKey(perm);
        if (selectAll) next.add(key);
        else next.delete(key);
      }
      return next;
    });
  };

  const handleSavePermissions = async () => {
    if (!selectedRole) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateRolePermissions(selectedRole.role_id, {
        permission_ids: Array.from(selectedPermissionIds),
      });
      await fetchRoles(selectedRole.role_id);
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
    setError(null);
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
      setError(getErrorMessage(err, '创建角色失败'));
      console.error('Create role error:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteRole = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteRole(deleteConfirm);
      setDeleteConfirm(null);
      if (selectedRole?.role_id === deleteConfirm) closeRoleDrawer();
      await fetchRoles();
    } catch (err) {
      setError(getErrorMessage(err, '删除角色失败'));
      console.error('Delete role error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const toggleSelect = (roleId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(roleId)) next.delete(roleId);
      else next.add(roleId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === selectableRoles.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(selectableRoles.map(r => r.role_id)));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    setBatchDeleting(true);
    setError(null);
    try {
      await Promise.all(Array.from(selectedIds).map(id => api.deleteRole(id)));
      setBatchDeleteConfirm(false);
      if (selectedRole && selectedIds.has(selectedRole.role_id)) closeRoleDrawer();
      setSelectedIds(new Set());
      await fetchRoles();
    } catch (err) {
      setError(getErrorMessage(err, '批量删除失败'));
      console.error('Batch delete error:', err);
    } finally {
      setBatchDeleting(false);
    }
  };

  const deleteTargetRole = deleteConfirm
    ? roles.find(r => r.role_id === deleteConfirm)
    : null;

  const hasBasicInfoChanges = selectedRole && (
    editName.trim() !== selectedRole.name
    || editDesc.trim() !== (selectedRole.description || '')
  );

  const hasPermissionChanges = selectedRole && (() => {
    const current = new Set(selectedRole.permission_ids || []);
    if (current.size !== selectedPermissionIds.size) return true;
    for (const id of selectedPermissionIds) {
      if (!current.has(id)) return true;
    }
    return false;
  })();

  const systemRoleCount = roles.filter(r => r.is_system).length;

  return (
    <div className="page-content">
      <PageToolbar
        meta={(
          <>
            <StatPill label="角色" value={roles.length} />
            <StatPill label="系统" value={systemRoleCount} tone="info" />
            <StatPill label="显示" value={filteredRoles.length} />
            {selectedIds.size > 0 && (
              <StatPill label="已选" value={selectedIds.size} tone="warning" />
            )}
          </>
        )}
        actions={(
          <>
            <input
              className="form-input"
              style={{ width: 220, fontSize: 13 }}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="搜索名称、ID、描述…"
              aria-label="搜索角色"
            />
            <select
              className="form-input form-select"
              style={{ width: 130 }}
              value={roleFilter}
              onChange={e => setRoleFilter(e.target.value as RoleFilter)}
              aria-label="角色类型"
            >
              <option value="all">全部</option>
              <option value="system">系统角色</option>
              <option value="custom">自定义</option>
            </select>
            {selectedIds.size > 0 && (
              <button
                type="button"
                className="btn btn--danger btn--sm"
                onClick={() => setBatchDeleteConfirm(true)}
              >
                删除 ({selectedIds.size})
              </button>
            )}
            <button type="button" className="btn btn--primary btn--sm" onClick={() => setCreateModalOpen(true)}>
              + 新建角色
            </button>
          </>
        )}
      />

      {error && !selectedRole && (
        <div className="error-banner" style={styles.errorBanner}>
          <span>⚠</span> {error}
          <button style={styles.errorClose} onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Role Table */}
      {loading && roles.length === 0 ? (
        <div className="loading-overlay">
          <div className="loading-spinner" />
        </div>
      ) : filteredRoles.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">👥</div>
          <p className="empty-state__text">
            {searchQuery || roleFilter !== 'all' ? '没有匹配的角色' : '暂无角色数据'}
          </p>
        </div>
      ) : (
        <div className="surface-card" style={{ overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={styles.colCheck}>
                  <input
                    type="checkbox"
                    checked={selectableRoles.length > 0 && selectedIds.size === selectableRoles.length}
                    onChange={toggleSelectAll}
                    disabled={selectableRoles.length === 0}
                    style={styles.checkbox}
                  />
                </th>
                <th>角色名称</th>
                <th>角色 ID</th>
                <th>描述</th>
                <th style={styles.colCount}>权限数</th>
                <th style={styles.colType}>类型</th>
                <th style={styles.colActions}>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredRoles.map(role => (
                <tr
                  key={role.role_id}
                  className={selectedRole?.role_id === role.role_id ? 'selected' : ''}
                  onClick={() => openRoleDrawer(role)}
                  style={{ cursor: 'pointer' }}
                >
                  <td onClick={e => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(role.role_id)}
                      onChange={() => !role.is_system && toggleSelect(role.role_id)}
                      disabled={role.is_system}
                      style={styles.checkbox}
                    />
                  </td>
                  <td>
                    <span style={styles.roleNameCell}>{role.name}</span>
                  </td>
                  <td>
                    <span className="mono" style={styles.roleIdCell}>{role.role_id}</span>
                  </td>
                  <td>
                    <span style={styles.descCell}>
                      {role.description || '—'}
                    </span>
                  </td>
                  <td>
                    <span style={styles.permCountBadge}>
                      {role.permission_ids?.length || 0}
                    </span>
                  </td>
                  <td>
                    {role.is_system ? (
                      <span className="status-badge status-badge--info">系统</span>
                    ) : (
                      <span className="status-badge status-badge--neutral">自定义</span>
                    )}
                  </td>
                  <td onClick={e => e.stopPropagation()}>
                    <div style={styles.rowActions}>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => openRoleDrawer(role)}
                      >
                        配置
                      </button>
                      {!role.is_system && (
                        <button
                          className="btn btn--ghost btn--sm"
                          style={{ color: 'var(--status-error)' }}
                          onClick={() => setDeleteConfirm(role.role_id)}
                        >
                          删除
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Slide-over Drawer */}
      {selectedRole && (
        <>
          <div style={styles.drawerOverlay} onClick={closeRoleDrawer} />
          <aside style={styles.drawer}>
            <div style={styles.drawerHeader}>
              <div>
                <h3 style={styles.drawerTitle}>{selectedRole.name}</h3>
                <span className="mono" style={styles.drawerSubtitle}>{selectedRole.role_id}</span>
              </div>
              <button style={styles.drawerClose} onClick={closeRoleDrawer} aria-label="关闭">
                ×
              </button>
            </div>

            <div style={styles.drawerBody}>
              {error && (
                <div className="error-banner" style={{ ...styles.errorBanner, marginBottom: 16 }}>
                  <span>⚠</span> {error}
                  <button style={styles.errorClose} onClick={() => setError(null)}>×</button>
                </div>
              )}

              {/* Basic Info */}
              <section style={styles.section}>
                <h4 style={styles.sectionTitle}>基本信息</h4>
                <div style={styles.formGroup}>
                  <label style={styles.label}>角色名称</label>
                  <input
                    className="form-input"
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    placeholder="输入角色名称"
                    disabled={selectedRole.is_system}
                  />
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.label}>角色描述</label>
                  <textarea
                    className="form-input"
                    style={styles.textarea}
                    value={editDesc}
                    onChange={e => setEditDesc(e.target.value)}
                    placeholder="输入角色描述（可选）"
                    rows={3}
                    disabled={selectedRole.is_system}
                  />
                </div>
                {!selectedRole.is_system && (
                  <button
                    className="btn btn--primary btn--sm"
                    onClick={handleSaveBasicInfo}
                    disabled={saving || !editName.trim() || !hasBasicInfoChanges}
                  >
                    {saving ? '保存中...' : '保存基本信息'}
                  </button>
                )}
                {selectedRole.is_system && (
                  <p style={styles.systemHint}>
                    系统角色不可修改名称与描述，权限配置可调整
                  </p>
                )}
              </section>

              {/* Permissions */}
              <section style={styles.section}>
                <div style={styles.sectionHeader}>
                  <h4 style={styles.sectionTitle}>
                    权限配置
                    <span style={styles.permSelectedCount}>
                      已选 {selectedPermissionIds.size} / {permissions.length}
                    </span>
                  </h4>
                  <button
                    className="btn btn--primary btn--sm"
                    onClick={handleSavePermissions}
                    disabled={saving || !hasPermissionChanges}
                  >
                    {saving ? '保存中...' : '保存权限'}
                  </button>
                </div>

                <input
                  className="form-input"
                  value={permissionSearch}
                  onChange={e => setPermissionSearch(e.target.value)}
                  placeholder="搜索权限名称或代码..."
                  style={{ marginBottom: 12 }}
                />

                {permissionGroups.length === 0 ? (
                  <p style={styles.noResults}>没有匹配的权限</p>
                ) : (
                  <div style={styles.permGroupList}>
                    {permissionGroups.map(([groupName, groupPerms]) => {
                      const selectedInGroup = groupPerms.filter(p =>
                        selectedPermissionIds.has(getPermissionKey(p)),
                      ).length;
                      const allSelected = selectedInGroup === groupPerms.length;
                      const someSelected = selectedInGroup > 0 && !allSelected;

                      return (
                        <div key={groupName} style={styles.permGroup}>
                          <div style={styles.permGroupHeader}>
                            <label style={styles.permGroupLabel}>
                              <input
                                type="checkbox"
                                checked={allSelected}
                                ref={el => {
                                  if (el) el.indeterminate = someSelected;
                                }}
                                onChange={() => handleToggleGroup(groupPerms, !allSelected)}
                                style={styles.checkbox}
                              />
                              <span style={styles.permGroupName}>{groupName}</span>
                              <span style={styles.permGroupCount}>
                                {selectedInGroup}/{groupPerms.length}
                              </span>
                            </label>
                          </div>
                          <div style={styles.permList}>
                            {groupPerms.map(perm => {
                              const permKey = getPermissionKey(perm);
                              const checked = selectedPermissionIds.has(permKey);
                              return (
                                <label
                                  key={permKey}
                                  style={{
                                    ...styles.permItem,
                                    ...(checked ? styles.permItemSelected : {}),
                                  }}
                                  className="perm-item"
                                >
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={() => handleTogglePermission(permKey)}
                                    style={styles.checkbox}
                                  />
                                  <div style={styles.permContent}>
                                    <div style={styles.permName}>{perm.name}</div>
                                    <div className="mono" style={styles.permCode}>{perm.code}</div>
                                    <div style={styles.permDesc}>
                                      {perm.description || '暂无说明'}
                                    </div>
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            </div>

            {!selectedRole.is_system && (
              <div style={styles.drawerFooter}>
                <button
                  className="btn btn--danger btn--sm"
                  onClick={() => setDeleteConfirm(selectedRole.role_id)}
                >
                  删除角色
                </button>
              </div>
            )}
          </aside>
        </>
      )}

      {/* Create Role Modal */}
      {createModalOpen && (
        <div className="modal-overlay" onClick={() => setCreateModalOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">新建角色</h3>
              <button className="modal__close" onClick={() => setCreateModalOpen(false)}>×</button>
            </div>
            <div className="modal__body">
              {error && (
                <div className="error-banner" style={{ marginBottom: 16 }}>
                  <span>⚠</span> {error}
                </div>
              )}
              <div style={styles.formGroup}>
                <label style={styles.label}>角色名称 *</label>
                <input
                  className="form-input"
                  value={newRoleName}
                  onChange={e => setNewRoleName(e.target.value)}
                  placeholder="输入角色名称"
                  autoFocus
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>角色描述</label>
                <textarea
                  className="form-input"
                  style={styles.textarea}
                  value={newRoleDesc}
                  onChange={e => setNewRoleDesc(e.target.value)}
                  placeholder="输入角色描述（可选）"
                  rows={3}
                />
              </div>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setCreateModalOpen(false)}>
                取消
              </button>
              <button
                className="btn btn--primary"
                onClick={handleCreateRole}
                disabled={creating || !newRoleName.trim()}
              >
                {creating ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">确认删除</h3>
              <button className="modal__close" onClick={() => setDeleteConfirm(null)}>×</button>
            </div>
            <div className="modal__body">
              <p style={styles.confirmText}>
                确定要删除角色 <strong>{deleteTargetRole?.name || deleteConfirm}</strong> 吗？此操作不可恢复。
              </p>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setDeleteConfirm(null)}>
                取消
              </button>
              <button
                className="btn btn--danger"
                onClick={handleDeleteRole}
                disabled={deleting}
              >
                {deleting ? '删除中...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Delete Confirmation */}
      {batchDeleteConfirm && (
        <div className="modal-overlay" onClick={() => setBatchDeleteConfirm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">确认批量删除</h3>
              <button className="modal__close" onClick={() => setBatchDeleteConfirm(false)}>×</button>
            </div>
            <div className="modal__body">
              <p style={styles.confirmText}>
                确定要删除选中的 <strong>{selectedIds.size}</strong> 个角色吗？此操作不可恢复。
              </p>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setBatchDeleteConfirm(false)}>
                取消
              </button>
              <button
                className="btn btn--danger"
                onClick={handleBatchDelete}
                disabled={batchDeleting}
              >
                {batchDeleting ? '删除中...' : `删除 ${selectedIds.size} 项`}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .perm-item:hover:not(:has(input:disabled)) {
          background-color: var(--surface-hover);
          border-color: var(--accent-primary);
        }
      `}</style>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    padding: 'var(--space-6)',
    height: '100%',
    overflow: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 'var(--space-4)',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  subtitle: {
    fontSize: '13px',
    color: 'var(--text-tertiary)',
    marginTop: '4px',
    display: 'block',
  },
  toolbar: {
    marginBottom: 'var(--space-4)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-subtle)',
  },
  searchInput: {
    maxWidth: '360px',
  },
  filterSelect: {
    width: '140px',
  },
  errorBanner: {
    marginBottom: 'var(--space-4)',
  },
  errorClose: {
    marginLeft: 'auto',
    padding: '0 8px',
    fontSize: '18px',
    background: 'none',
    border: 'none',
    color: 'var(--status-error)',
    cursor: 'pointer',
  },
  tableCard: {
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
  },
  colCheck: { width: '44px' },
  colCount: { width: '80px', textAlign: 'center' as const },
  colType: { width: '90px' },
  colActions: { width: '140px' },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
    accentColor: 'var(--accent-primary)',
  },
  roleNameCell: {
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  roleIdCell: {
    fontSize: '12px',
    color: 'var(--accent-primary)',
  },
  descCell: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    maxWidth: '280px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
    display: 'block',
  },
  permCountBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '28px',
    padding: '2px 8px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--surface-tertiary)',
    borderRadius: 'var(--radius-full)',
  },
  rowActions: {
    display: 'flex',
    gap: '4px',
  },
  drawerOverlay: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    zIndex: 1000,
    animation: 'fadeIn 0.15s ease',
  },
  drawer: {
    position: 'fixed',
    top: 0,
    right: 0,
    bottom: 0,
    width: '520px',
    maxWidth: '95vw',
    backgroundColor: 'var(--surface-primary)',
    boxShadow: 'var(--shadow-lg)',
    zIndex: 1001,
    display: 'flex',
    flexDirection: 'column',
    animation: 'slideInRight 0.25s ease',
  },
  drawerHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: 'var(--space-5) var(--space-6)',
    borderBottom: '1px solid var(--border-subtle)',
  },
  drawerTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  drawerSubtitle: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    marginTop: '4px',
    display: 'block',
  },
  drawerClose: {
    padding: '4px 8px',
    fontSize: '22px',
    color: 'var(--text-tertiary)',
    lineHeight: 1,
  },
  drawerBody: {
    flex: 1,
    overflowY: 'auto',
    padding: 'var(--space-6)',
  },
  drawerFooter: {
    padding: 'var(--space-4) var(--space-6)',
    borderTop: '1px solid var(--border-subtle)',
  },
  section: {
    marginBottom: 'var(--space-8)',
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 'var(--space-3)',
  },
  sectionTitle: {
    margin: 0,
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  permSelectedCount: {
    marginLeft: '8px',
    fontSize: '11px',
    fontWeight: 500,
    color: 'var(--text-tertiary)',
    textTransform: 'none',
    letterSpacing: 0,
  },
  formGroup: {
    marginBottom: 'var(--space-4)',
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    marginBottom: '6px',
  },
  textarea: {
    resize: 'vertical' as const,
    minHeight: '72px',
  },
  systemHint: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    margin: 0,
  },
  permGroupList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-4)',
  },
  permGroup: {
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
  },
  permGroupHeader: {
    padding: 'var(--space-3) var(--space-4)',
    backgroundColor: 'var(--surface-secondary)',
    borderBottom: '1px solid var(--border-subtle)',
  },
  permGroupLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    cursor: 'pointer',
  },
  permGroupName: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    textTransform: 'capitalize',
  },
  permGroupCount: {
    marginLeft: 'auto',
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  },
  permList: {
    display: 'flex',
    flexDirection: 'column',
  },
  permItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 'var(--space-3)',
    padding: 'var(--space-3) var(--space-4)',
    borderBottom: '1px solid var(--border-subtle)',
    cursor: 'pointer',
    transition: 'background-color var(--transition-fast)',
  },
  permItemSelected: {
    backgroundColor: 'rgba(22, 163, 74, 0.06)',
  },
  permContent: {
    flex: 1,
    minWidth: 0,
  },
  permName: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '2px',
  },
  permCode: {
    fontSize: '11px',
    color: 'var(--accent-primary)',
    marginBottom: '2px',
  },
  permDesc: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  },
  noResults: {
    fontSize: '13px',
    color: 'var(--text-tertiary)',
    textAlign: 'center' as const,
    padding: 'var(--space-6)',
  },
  confirmText: {
    fontSize: '14px',
    color: 'var(--text-primary)',
    margin: 0,
    lineHeight: 1.6,
  },
};

export default RoleManagement;
